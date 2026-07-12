from otree.api import *
from os import environ
import asyncio
import json
import os
import base64
import logging
import threading
from datetime import datetime, timezone

from .services import transcribe, generate_reply, synthesize, judge_phase_goal
from .prompts import (
    build_system_prompt,
    build_judge_prompt,
    prime_text,
    extract_advance_flag,
    phase_name,
    is_last_phase,
    advance_decision,
)
from settings import LANG, HRV_REST_SECONDS, hrv_rest_duration_label

doc = """
Module 2 — Voice Session (scaffold).

Personalized emotion-regulation voice agent built on the
clintmckenna/oTree_gpt `chat_voice` foundation. The full turn loop
(record -> STT -> LLM -> TTS -> playback) is wired here; the actual
STT / LLM / TTS calls go through swappable adapters in services.py.
The scaffold ships local stubs so the loop runs end-to-end without any
API keys or models installed.
"""

logger = logging.getLogger(__name__)


class C(BaseConstants):
    NAME_IN_URL = 'Voice'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1

    # show the text transcript panel next to the voice UI (handy in dev)
    SHOW_TEXT_TRANSCRIPT = True
    # persist each participant utterance to disk (path recorded in the DB)
    SAVE_USER_AUDIO = True
    # re-render the conversation on page refresh
    SHOW_HISTORY = True

    # audio is written here and served at /static/Voice/recordings/<file>
    RECORDINGS_DIR = '_static/Voice/recordings'

    # ElevenLabs voice id (only used when VOICE_TTS_BACKEND=elevenlabs)
    VOICE_ID = (
        environ.get('VOICE_ID_DE', 'FOfJ2PMgU6HOGbNYnzto') if LANG == 'de'
        else environ.get('VOICE_ID_EN', 'WuBPEavIaQB56EnsGvFh')
    )

    # Experimental condition for this run. Real per-participant assignment is a
    # later task ("Config externalization + condition assignment"); for the
    # scaffold we read a single default from the environment.
    #   T1 = profile withheld from agent · T2 = profile injected · T3 = T2 + live adaptation
    DEFAULT_CONDITION = environ.get('VOICE_CONDITION', 'T2')


# ----- profile + prompt helpers ------------------------------------------------

def _load_profile(player) -> str:
    """Read the single end profile produced by Module 1.

    Profiling is one lineage: Introduction builds the initial profile from the
    questionnaire, and Chat refines it with the voice interview into the end
    profile. Both are written to participant.vars, so the voice module reads the
    end profile by participant id, falling back to the initial profile if the
    refinement step has not run, then to empty.
    """
    pv = player.participant.vars
    return pv.get('profile_interview') or pv.get('profile_questionnaire') or ''


# The layered system prompt (persona + AI disclosure -> condition-based profile block ->
# current phase block -> pacing instruction) is assembled in prompts.build_system_prompt().


# ----- models ------------------------------------------------------------------

class Subsession(BaseSubsession):
    pass


def creating_session(subsession: Subsession):
    for p in subsession.get_players():
        # real condition assignment is a later task; seed from the env default
        p.condition = C.DEFAULT_CONDITION


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    # assigned experimental condition (T1 / T2 / T3)
    condition = models.StringField(initial='')
    # running JSON cache of the conversation
    cachedMessages = models.LongStringField(initial='[]')
    # emotional prime: scripted, condition-agnostic first Check-In turn (#5, FR24/D6/D19)
    prime_shown = models.BooleanField(initial=False)
    # VAS stress manipulation check, captured right after the participant's first response,
    # before any personalized LLM reply. None until answered.
    vas_stress = models.IntegerField(min=0, max=10, blank=True)
    vas_stress_timestamp = models.FloatField(initial=0)
    # four-phase session state (D18)
    current_phase = models.IntegerField(initial=0)
    current_phase_started = models.FloatField(initial=0)
    # bot turns taken within the current phase (drives turn-based advancement)
    current_phase_turns = models.IntegerField(initial=0)
    # set when a phase transition just happened, so the next turn acknowledges the shift
    phase_just_advanced = models.BooleanField(initial=False)
    # list of {phase, started_at, advanced_at, turns, reason} transition records
    # (post-hoc HRV3 segmentation + engagement metrics)
    phase_log = models.LongStringField(initial='[]')
    # T3 emotional state tracking (FR13/FR14)
    emotional_state = models.StringField(initial='calm')    # calm | moderate_distress | high_distress
    # [{turn_ts, label, score, pitch_delta, speech_rate_delta, pause_rate_delta,
    #   acoustics_used, state, state_changed, tts_state, tts_voice_settings}]
    sentiment_log   = models.LongStringField(initial='[]')
    # HRV④ post-session recovery rest window (D7/D20)
    timestamp_hrv_recovery_start = models.FloatField(initial=0)
    timestamp_hrv_recovery_end = models.FloatField(initial=0)


class MessageData(ExtraModel):
    player = models.Link(Player)
    msgId = models.StringField()
    timestamp = models.StringField()
    sender = models.StringField()
    msgText = models.StringField()
    audioPath = models.StringField(initial='')
    # engagement (#12): participant response latency = ms between the agent's audio finishing
    # and the participant starting to record. Client-measured; None on agent turns / if unknown.
    responseLatencyMs = models.FloatField(blank=True)


# ----- engagement metrics (#12) ------------------------------------------------

def _word_count(text: str) -> int:
    return len((text or '').split())


def _turn_acoustics(audio_filename: str):
    """Pause/speech rate for one saved participant turn, computed at export time so it runs for
    ALL conditions without any per-turn runtime cost (#12). Fail-open: returns None if the file
    is missing or librosa/ffmpeg is unavailable."""
    if not audio_filename:
        return None
    try:
        from .acoustics import extract_features
        path = os.path.join(C.RECORDINGS_DIR, audio_filename)
        if not os.path.exists(path):
            return None
        return extract_features(path)
    except Exception:
        logger.exception('export acoustics failed for %s (skipping)', audio_filename)
        return None


def _engagement_summary(player) -> dict:
    """Per-session engagement aggregates derived from stored data (#12). Zero runtime cost."""
    msgs = list(MessageData.filter(player=player))
    ts = [float(m.timestamp) for m in msgs if m.timestamp]
    user = [m for m in msgs if m.sender == 'Subject']
    agent = [m for m in msgs if m.sender != 'Subject']
    user_words = sum(_word_count(m.msgText) for m in user)
    agent_words = sum(_word_count(m.msgText) for m in agent)
    lat = [m.field_maybe_none('responseLatencyMs') for m in user]
    lat = [x for x in lat if x is not None]
    plog = json.loads(player.field_maybe_none('phase_log') or '[]')
    return dict(
        sessionDurationSec=round(max(ts) - min(ts), 2) if len(ts) >= 2 else 0,
        totalUserTurns=len(user),
        totalAgentTurns=len(agent),
        userWordTotal=user_words,
        agentWordTotal=agent_words,
        wordRatioUserAgent=round(user_words / agent_words, 3) if agent_words else '',
        meanResponseLatencyMs=round(sum(lat) / len(lat), 1) if lat else '',
        phasesEarly=sum(1 for e in plog if e.get('reason') in ('judge', 'flag')),
        phasesForced=sum(1 for e in plog if e.get('reason') == 'forced'),
    )


def custom_export(players):
    yield [
        'sessionId', 'participantId', 'condition',
        # per-session engagement aggregates (#12), repeated on each of the player's rows
        'sessionDurationSec', 'totalUserTurns', 'totalAgentTurns',
        'userWordTotal', 'agentWordTotal', 'wordRatioUserAgent', 'meanResponseLatencyMs',
        'phasesEarly', 'phasesForced',
        'vasStress', 'vasStressTimestamp', 'phaseLog', 'sentimentLog',
        # per-turn record + per-turn engagement metrics (#12)
        'msgId', 'timestamp', 'sender', 'msgText', 'audioPath',
        'wordCount', 'responseLatencyMs', 'pauseRate', 'speechRate', 'pitchMean',
    ]
    for p in players:
        vas = p.field_maybe_none('vas_stress')
        s = _engagement_summary(p)
        session_cols = [
            p.session.code,
            p.participant.code,
            p.field_maybe_none('condition') or '',
            s['sessionDurationSec'], s['totalUserTurns'], s['totalAgentTurns'],
            s['userWordTotal'], s['agentWordTotal'], s['wordRatioUserAgent'],
            s['meanResponseLatencyMs'], s['phasesEarly'], s['phasesForced'],
            '' if vas is None else vas,
            p.field_maybe_none('vas_stress_timestamp') or '',
            p.field_maybe_none('phase_log') or '[]',
            p.field_maybe_none('sentiment_log') or '[]',
        ]
        for m in MessageData.filter(player=p):
            is_user = m.sender == 'Subject'
            latency = m.field_maybe_none('responseLatencyMs') if is_user else None
            # acoustic engagement metrics for participant turns, all conditions (export-time)
            pause = speech = pitch = ''
            if is_user:
                feats = _turn_acoustics(m.audioPath)
                if feats:
                    pause = round(feats['pause_rate'], 4)
                    speech = round(feats['speech_rate'], 4)
                    pitch = round(feats['pitch_mean'], 1)
            yield session_cols + [
                m.msgId, m.timestamp, m.sender, m.msgText, m.audioPath,
                _word_count(m.msgText),
                '' if latency is None else round(latency, 1),
                pause, speech, pitch,
            ]


# ----- audio helper ------------------------------------------------------------

def _save_audio(filename: str, audio: bytes) -> str:
    """Write audio bytes to the local recordings dir; return the bare filename
    (served at /static/Voice/recordings/<filename>)."""
    os.makedirs(C.RECORDINGS_DIR, exist_ok=True)
    with open(os.path.join(C.RECORDINGS_DIR, filename), 'wb') as f:
        f.write(audio)
    return filename


# ----- pages -------------------------------------------------------------------

class Session(Page):
    form_model = 'player'
    template_name = f'Voice/{LANG}/Session.html'

    @staticmethod
    def js_vars(player):
        return dict(
            id_in_group=player.id_in_group,
            playerId='P' + str(player.id_in_group),
            showTextTranscript=C.SHOW_TEXT_TRANSCRIPT,
        )

    @staticmethod
    def vars_for_template(player):
        profile = _load_profile(player)
        condition = player.field_maybe_none('condition') or C.DEFAULT_CONDITION
        pv = player.participant.vars
        profile_source = (
            'interview' if pv.get('profile_interview')
            else 'questionnaire' if pv.get('profile_questionnaire')
            else 'none'
        )
        return dict(
            cached_messages=json.loads(player.cachedMessages or '[]'),
            show_history=C.SHOW_HISTORY,
            currentPlayer='P' + str(player.id_in_group),
            current_phase_name=phase_name(player.current_phase),
            debug_condition=condition,
            debug_profile_source=profile_source,
            debug_profile=profile,
            debug_system_prompt=build_system_prompt(
                profile, condition, player.current_phase,
                erq_category=pv.get('erq_framing_category'),
            ),
        )

    @staticmethod
    async def live_method(player: Player, data):
        messages = json.loads(player.cachedMessages or '[]')
        currentPlayer = 'P' + str(player.id_in_group)
        botLabel = 'B' + str(player.id_in_group)

        # no payload -> page load / refresh
        if not data:
            # first load: open Check-In with the scripted, condition-agnostic emotional prime
            # (fixed text, TTS, no LLM) before any personalized behaviour (#5, FR24/D6/D19).
            if not player.prime_shown:
                now_ts = datetime.now(tz=timezone.utc).timestamp()
                dateNow = str(now_ts)
                botMsgId = botLabel + '-' + dateNow
                text = prime_text()

                audioURL = None
                audioPath = ''
                try:
                    audio = await synthesize(text, voice_id=C.VOICE_ID)
                    if audio:
                        audioPath = _save_audio(f'{player.session.code}_{botMsgId}.mp3', audio)
                        audioURL = audioPath
                except Exception:
                    logger.exception('Prime TTS failed (continuing text-only)')

                MessageData.create(
                    player=player, msgId=botMsgId, timestamp=dateNow,
                    sender=botLabel, msgText=text, audioPath=audioPath,
                )
                messages.append({'sender': 'assistant', 'label': botLabel, 'msgId': botMsgId, 'text': text})
                player.cachedMessages = json.dumps(messages)
                player.prime_shown = True
                # anchor the Check-In clock at the prime (start of the phase)
                player.current_phase_started = now_ts

                yield {player.id_in_group: dict(
                    event='botText', sender=botLabel, botMsgId=botMsgId,
                    text=text, audioFilePath=audioURL,
                    phase=phase_name(player.current_phase), sessionDone=False,
                )}
                return
            # already primed. If a refresh interrupted the VAS before it was submitted, re-show
            # it so the manipulation check is never silently skipped (data integrity for #5).
            user_turns = sum(1 for mm in messages if mm.get('sender') == 'user')
            if player.field_maybe_none('vas_stress') is None and user_turns >= 1:
                yield {player.id_in_group: dict(event='resumeVas', messages=messages)}
                return
            yield {player.id_in_group: dict(messages=messages)}
            return

        event = data.get('event')

        # ---- VAS stress manipulation check: stored after the participant's first response,
        # before any further (personalized) LLM reply (#5). Ack so the client then proceeds.
        if event == 'vas':
            try:
                val = int(data.get('value'))
            except (TypeError, ValueError):
                val = None
            if val is not None and 0 <= val <= 10:
                player.vas_stress = val
                player.vas_stress_timestamp = float(
                    data.get('ts') or datetime.now(tz=timezone.utc).timestamp()
                )
            yield {player.id_in_group: dict(event='vasStored')}
            return

        # ---- participant turn: decode audio -> save -> transcribe (STT) -------
        if event == 'text':
            b64 = base64.b64decode(data['text'])
            dateNow = str(datetime.now(tz=timezone.utc).timestamp())
            msgId = currentPlayer + '-' + dateNow

            audioPath = ''
            if C.SAVE_USER_AUDIO:
                audioPath = _save_audio(f'{player.session.code}_{msgId}.webm', b64)

            try:
                text = await transcribe(b64)
            except Exception as e:
                logger.exception('STT failed')
                yield {player.id_in_group: {'error': (
                    f'Transkription fehlgeschlagen: {e}' if LANG == 'de'
                    else f'Transcription failed: {e}'
                )}}
                return

            # response latency (#12): ms between the agent's audio finishing and this recording
            # starting, measured client-side. Ignore missing/negative values.
            try:
                latency = float(data.get('latencyMs'))
                if latency < 0:
                    latency = None
            except (TypeError, ValueError):
                latency = None

            MessageData.create(
                player=player, msgId=msgId, timestamp=dateNow,
                sender='Subject', msgText=text, audioPath=audioPath,
                responseLatencyMs=latency,
            )
            messages.append({'sender': 'user', 'label': currentPlayer, 'msgId': msgId, 'text': text})
            player.cachedMessages = json.dumps(messages)

            # the participant's first response is the answer to the prime -> collect the VAS
            # stress check before any personalized LLM reply (#5). Client shows the slider and
            # withholds the bot turn until it is submitted.
            user_turns = sum(1 for mm in messages if mm.get('sender') == 'user')
            show_vas = user_turns == 1 and player.field_maybe_none('vas_stress') is None

            yield {player.id_in_group: dict(
                event='text', selfText=text, sender=currentPlayer, msgId=msgId,
                showVas=show_vas,
            )}
            return

        # ---- bot turn: LLM reply (KIT) -> TTS -> playback ---------------------
        if event == 'botMsg':
            now_ts = datetime.now(tz=timezone.utc).timestamp()
            dateNow = str(now_ts)
            botMsgId = botLabel + '-' + dateNow

            # anchor the first phase's clock on the first bot turn
            if not player.current_phase_started:
                player.current_phase_started = now_ts

            profile = _load_profile(player)
            condition = player.field_maybe_none('condition') or C.DEFAULT_CONDITION

            # ---- T3 live adaptation: per-turn sentiment + 3-state classifier (FR12/FR13/FR14)
            # Runs server-side, T3 only. Sentiment always runs; acoustics are fail-open
            # (skipped when the participant has no calibration baseline recording).
            state_changed = False
            new_state = None
            tts_voice_settings = None  # T3 only — NFR3: T1/T2 must stay None (fixed stimulus)
            if condition == 'T3':
                from .sentiment import analyse_sentiment, classify_state
                from .acoustics import get_baseline, extract_features, compute_deltas

                # most recent participant turn: transcript (from cache) + saved audio (from DB)
                transcript_text = ''
                audio_path = ''
                for m in reversed(messages):
                    if m.get('sender') == 'user':
                        transcript_text = m.get('text', '')
                        rows = MessageData.filter(player=player, msgId=m.get('msgId'))
                        if rows and rows[0].audioPath:
                            audio_path = os.path.join(C.RECORDINGS_DIR, rows[0].audioPath)
                        break

                # acoustic features for this turn (relative to calibration baseline)
                cal_path = player.participant.vars.get('calibration_audio_path')
                if not cal_path:
                    cal_name = player.participant.vars.get('calibration_audio')
                    if cal_name:
                        cal_path = os.path.join(C.RECORDINGS_DIR, cal_name)
                baseline = get_baseline(
                    player.participant.code,
                    calibration_path=cal_path,
                )
                acoustics_used = bool(baseline and audio_path)
                if acoustics_used:  # fail-open if calibration recording is missing
                    try:
                        turn_features = extract_features(audio_path)
                        deltas = compute_deltas(turn_features, baseline)
                    except Exception:
                        logger.exception(
                            "Turn acoustic extraction failed for %s (fail-open)",
                            player.participant.code,
                        )
                        deltas = {"pitch_delta": 0.0, "speech_rate_delta": 0.0, "pause_rate_delta": 0.0}
                        acoustics_used = False
                else:
                    deltas = {"pitch_delta": 0.0, "speech_rate_delta": 0.0, "pause_rate_delta": 0.0}

                # sentiment on the transcript
                sentiment = analyse_sentiment(transcript_text)

                # classify and detect transition
                new_state = classify_state(sentiment, **deltas)
                state_changed = (new_state != player.emotional_state)
                prev_state = player.emotional_state
                if state_changed:
                    player.emotional_state = new_state

                # TTS pacing follows persisted state every turn (not trigger-only like the prompt).
                from .tts_settings import voice_settings_for_emotional_state
                tts_voice_settings = voice_settings_for_emotional_state(player.emotional_state)

                # surface the per-turn decision in the server log (pilot monitoring)
                logger.info(
                    "[T3 %s] sentiment=%s (%.2f) | deltas pitch=%+.2f rate=%+.2f pause=%+.2f%s "
                    "| state=%s%s",
                    player.participant.code,
                    sentiment['label'], sentiment['score'],
                    deltas['pitch_delta'], deltas['speech_rate_delta'], deltas['pause_rate_delta'],
                    '' if acoustics_used else ' (no baseline: acoustics skipped)',
                    new_state,
                    f' (changed from {prev_state})' if state_changed else ' (unchanged)',
                )

                # log every turn for pilot hand-validation (NFR5 / study design requirement).
                # Includes the acoustic deltas the classifier actually decided on (and whether
                # acoustics were available at all) -- previously only visible in the server log,
                # not queryable from the DB/CSV export where hand-validation actually happens.
                log = json.loads(player.sentiment_log or '[]')
                log.append({
                    'turn_ts': now_ts,
                    'label': sentiment['label'],
                    'score': sentiment['score'],
                    'pitch_delta': deltas['pitch_delta'],
                    'speech_rate_delta': deltas['speech_rate_delta'],
                    'pause_rate_delta': deltas['pause_rate_delta'],
                    'acoustics_used': acoustics_used,
                    'state': new_state,
                    'state_changed': state_changed,
                    'tts_state': player.emotional_state,
                    'tts_voice_settings': tts_voice_settings,
                })
                player.sentiment_log = json.dumps(log)

            # first turn of a new phase: name the phase we just left so the model acknowledges
            # the shift instead of being handed a fresh instruction with no context (D18).
            transition_from = (
                phase_name(player.current_phase - 1) if player.phase_just_advanced else None
            )
            player.phase_just_advanced = False

            # trigger-only: inject the state instruction on transition, not every turn.
            # erq_category (frozen at questionnaire time) selects DEEPEN/INTRODUCE framing (#8).
            system_prompt = build_system_prompt(
                profile, condition, player.current_phase,
                emotional_state=new_state if state_changed else None,
                transition_from=transition_from,
                erq_category=player.participant.vars.get('erq_framing_category'),
            )

            try:
                reply = await generate_reply(messages, system_prompt=system_prompt)
            except Exception as e:
                logger.exception('LLM failed')
                yield {player.id_in_group: {'error': (
                    f'KI-Antwort fehlgeschlagen: {e}' if LANG == 'de'
                    else f'LLM failed: {e}'
                )}}
                return

            # sanitize the reply (strip any leaked flag/harmony tokens) before it reaches TTS or
            # the transcript (D18/FR22). wants_advance is the inline-flag *fallback* signal.
            reply, wants_advance = extract_advance_flag(reply)

            # this reply is the current phase's turn; count it before deciding (D18)
            player.current_phase_turns += 1

            # Option B: decide phase readiness out-of-band. A separate structured judge call reads
            # the conversation (including this reply) and the phase's goal, so the coaching reply
            # above never has to carry a control signal. Runs concurrently with TTS to hide its
            # latency; falls back to the inline flag if the judge is unavailable, and the ceiling
            # always applies regardless.
            judge_msgs = messages + [{'sender': 'assistant', 'text': reply}]
            judge_task = asyncio.ensure_future(
                judge_phase_goal(build_judge_prompt(player.current_phase), judge_msgs)
            )

            # TTS -> save mp3. The stub backend returns no bytes, so the client
            # falls back to showing the transcript only.
            # NFR3: only T3 passes state-derived voice_settings; T1/T2 use ElevenLabs defaults.
            audioURL = None
            audioPath = ''
            try:
                if condition == 'T3':
                    audio = await synthesize(
                        reply, voice_id=C.VOICE_ID, voice_settings=tts_voice_settings,
                    )
                else:
                    audio = await synthesize(reply, voice_id=C.VOICE_ID)
                if audio:
                    audioPath = _save_audio(f'{player.session.code}_{botMsgId}.mp3', audio)
                    audioURL = audioPath
            except Exception:
                logger.exception('TTS failed (continuing text-only)')

            # collect the judge verdict (was running during TTS); None -> use the inline flag.
            judge_met = await judge_task
            ready_to_advance = wants_advance if judge_met is None else judge_met

            # turn-gated advancement with a hard ceiling: honour readiness once the turn floor is
            # met, but force-advance if a turn/time ceiling is hit so a phase can never hang.
            # log the transition (turns + reason feed engagement metrics); finish after the last.
            elapsed = now_ts - player.current_phase_started
            turns_this_phase = player.current_phase_turns
            from_phase = phase_name(player.current_phase)
            advance, reason = advance_decision(
                player.current_phase, turns_this_phase, elapsed, ready_to_advance,
            )
            if advance and reason == 'flag':
                # distinguish how readiness was signalled, for pilot hand-validation (#12)
                reason = 'judge' if judge_met is not None else 'flag'
            session_done = False
            if advance:
                log = json.loads(player.phase_log or '[]')
                log.append({
                    'phase': from_phase,
                    'started_at': player.current_phase_started,
                    'advanced_at': now_ts,
                    'turns': turns_this_phase,
                    'reason': reason,
                })
                player.phase_log = json.dumps(log)
                if is_last_phase(player.current_phase):
                    session_done = True
                else:
                    player.current_phase += 1
                    player.current_phase_started = now_ts
                    player.current_phase_turns = 0
                    player.phase_just_advanced = True

            # surface every phase-control decision in the server log (pilot monitoring) --
            # mirrors the T3 sentiment/state logging above so phase advancement is visible
            # live during a session, not only after the fact via phase_log/CSV export.
            logger.info(
                "[Phase %s] phase=%s turn=%d elapsed=%.0fs judge=%s inline_flag=%s -> %s",
                player.participant.code,
                from_phase,
                turns_this_phase,
                elapsed,
                judge_met if judge_met is not None else 'n/a',
                wants_advance,
                (
                    'SESSION END' if session_done
                    else f'ADVANCE to {phase_name(player.current_phase)} ({reason})' if advance
                    else 'stay'
                ),
            )

            MessageData.create(
                player=player, msgId=botMsgId, timestamp=dateNow,
                sender=botLabel, msgText=reply, audioPath=audioPath,
            )
            messages.append({'sender': 'assistant', 'label': botLabel, 'msgId': botMsgId, 'text': reply})
            player.cachedMessages = json.dumps(messages)

            yield {player.id_in_group: dict(
                event='botText', sender=botLabel, botMsgId=botMsgId,
                text=reply, audioFilePath=audioURL,
                phase=phase_name(player.current_phase), sessionDone=session_done,
            )}
            return


class HRVRecovery(Page):
    form_model = 'player'
    template_name = f'Voice/{LANG}/HRVRecovery.html'

    @staticmethod
    def vars_for_template(player):
        return dict(
            hrv_rest_seconds=HRV_REST_SECONDS,
            hrv_rest_duration=hrv_rest_duration_label(),
        )

    @staticmethod
    def live_method(player, data):
        if data.get('timestamp_hrv_recovery_start'):
            player.timestamp_hrv_recovery_start = data['timestamp_hrv_recovery_start']
            return
        if data.get('timestamp_hrv_recovery_end'):
            player.timestamp_hrv_recovery_end = data['timestamp_hrv_recovery_end']
            return


page_sequence = [Session, HRVRecovery]

# Best-effort head start: load STT / sentiment / librosa JIT in the background so
# the first Voice turn is fast. Introduction Processing gates on is_warm() for
# the real guarantee.
from .warmup import warmup  # noqa: E402

threading.Thread(target=warmup, daemon=True, name='voice-warmup').start()
