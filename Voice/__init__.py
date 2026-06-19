from otree.api import *
from os import environ
import json
import os
import base64
import logging
from datetime import datetime, timezone

from .services import transcribe, generate_reply, synthesize

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
    VOICE_ID = environ.get('VOICE_ID', 'EXAVITQu4vr4xnSDxMaL')

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


def _system_prompt(profile: str, condition: str) -> str:
    """Scaffold system prompt. The real layered persona + four phase blocks are a
    later task ("Author & version-control system prompts")."""
    base = (
        "You are a warm, attuned emotion-regulation coach. Help the participant "
        "reflect on and reappraise what they share. Keep replies short and "
        "spoken-friendly."
    )
    # T1 withholds the profile from the agent; T2/T3 inject it.
    if condition != 'T1' and profile:
        return base + "\n\nUser profile (personalize to this person):\n" + profile
    return base


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


class MessageData(ExtraModel):
    player = models.Link(Player)
    msgId = models.StringField()
    timestamp = models.StringField()
    sender = models.StringField()
    msgText = models.StringField()
    audioPath = models.StringField(initial='')


def custom_export(players):
    yield [
        'sessionId', 'participantId', 'condition',
        'msgId', 'timestamp', 'sender', 'msgText', 'audioPath',
    ]
    for m in MessageData.filter():
        p = m.player
        yield [
            p.session.code,
            p.participant.code,
            p.field_maybe_none('condition') or '',
            m.msgId,
            m.timestamp,
            m.sender,
            m.msgText,
            m.audioPath,
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
            debug_condition=condition,
            debug_profile_source=profile_source,
            debug_profile=profile,
            debug_system_prompt=_system_prompt(profile, condition),
        )

    @staticmethod
    async def live_method(player: Player, data):
        # no payload -> just replay the cache (page load / refresh)
        if not data:
            yield {player.id_in_group: dict(messages=json.loads(player.cachedMessages or '[]'))}
            return

        messages = json.loads(player.cachedMessages or '[]')
        currentPlayer = 'P' + str(player.id_in_group)
        botLabel = 'B' + str(player.id_in_group)
        event = data.get('event')

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
                yield {player.id_in_group: {'error': f'Transcription failed: {e}'}}
                return

            MessageData.create(
                player=player, msgId=msgId, timestamp=dateNow,
                sender='Subject', msgText=text, audioPath=audioPath,
            )
            messages.append({'sender': 'user', 'label': currentPlayer, 'msgId': msgId, 'text': text})
            player.cachedMessages = json.dumps(messages)

            yield {player.id_in_group: dict(
                event='text', selfText=text, sender=currentPlayer, msgId=msgId,
            )}
            return

        # ---- bot turn: LLM reply (KIT) -> TTS -> playback ---------------------
        if event == 'botMsg':
            dateNow = str(datetime.now(tz=timezone.utc).timestamp())
            botMsgId = botLabel + '-' + dateNow

            profile = _load_profile(player)
            condition = player.field_maybe_none('condition') or C.DEFAULT_CONDITION
            system_prompt = _system_prompt(profile, condition)

            try:
                reply = await generate_reply(messages, system_prompt=system_prompt)
            except Exception as e:
                logger.exception('LLM failed')
                yield {player.id_in_group: {'error': f'LLM failed: {e}'}}
                return

            # TTS -> save mp3. The stub backend returns no bytes, so the client
            # falls back to showing the transcript only.
            audioURL = None
            audioPath = ''
            try:
                audio = await synthesize(reply, voice_id=C.VOICE_ID)
                if audio:
                    audioPath = _save_audio(f'{player.session.code}_{botMsgId}.mp3', audio)
                    audioURL = audioPath
            except Exception:
                logger.exception('TTS failed (continuing text-only)')

            MessageData.create(
                player=player, msgId=botMsgId, timestamp=dateNow,
                sender=botLabel, msgText=reply, audioPath=audioPath,
            )
            messages.append({'sender': 'assistant', 'label': botLabel, 'msgId': botMsgId, 'text': reply})
            player.cachedMessages = json.dumps(messages)

            yield {player.id_in_group: dict(
                event='botText', sender=botLabel, botMsgId=botMsgId,
                text=reply, audioFilePath=audioURL,
            )}
            return


page_sequence = [Session]
