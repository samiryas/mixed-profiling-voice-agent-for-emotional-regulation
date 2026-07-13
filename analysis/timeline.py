"""Reconstruct each participant's session timeline from the app's own timestamps.

This replaces the manual step of reading wall-clock times off the oTree export and
typing them into the HRV tools: every segment boundary below comes from a timestamp
the app itself recorded (all Unix epochs, UTC).

Segments (intervals) produced, when their timestamps exist:

- hrv_baseline           Introduction.timestamp_hrv_baseline_start/_end (5-min rest)
- profiling_interview    approx.: last Introduction activity -> Voice session start
                         (the Chat app records no page-level timestamps; flagged inferred)
- voice_session          first Voice turn -> recovery start (or last turn as fallback)
- voice:<phase>          one per Voice phase from phase_log (checkin/technique/...),
                         plus the in-progress phase the log never closed (inferred end)
- hrv_recovery           Voice.timestamp_hrv_recovery_start/_end

Point events: questionnaire submits, calibration, VAS stress rating (with value),
evaluation questionnaire submit, per-turn Voice messages.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .ingest import VOICE_PHASES, ParticipantRecord


@dataclass
class Segment:
    name: str
    start: datetime
    end: datetime
    inferred: bool = False  # True when a boundary had to be derived, not read directly
    meta: dict | None = None

    @property
    def duration_s(self) -> float:
        return (self.end - self.start).total_seconds()


@dataclass
class Event:
    name: str
    at: datetime
    meta: dict | None = None


def _utc(epoch: float | None) -> datetime | None:
    return datetime.fromtimestamp(epoch, tz=timezone.utc) if epoch else None


def build_timeline(rec: ParticipantRecord) -> tuple[list[Segment], list[Event]]:
    segments: list[Segment] = []
    events: list[Event] = []

    # ---- Introduction ------------------------------------------------------
    base_start = _utc(rec.float_field("Introduction", "timestamp_hrv_baseline_start"))
    base_end = _utc(rec.float_field("Introduction", "timestamp_hrv_baseline_end"))
    if base_start and base_end:
        segments.append(Segment("hrv_baseline", base_start, base_end))

    intro_events = {
        "privacy_accepted": "timestamp_privacy",
        "bigfive_submitted": "timestamp_bigfive",
        "erq_submitted": "timestamp_erq",
        "calibration_recorded": "timestamp_calibration",
    }
    intro_epochs = []
    for name, fieldname in intro_events.items():
        at = _utc(rec.float_field("Introduction", fieldname))
        if at:
            events.append(Event(name, at))
            intro_epochs.append(at)

    # ---- Voice session -----------------------------------------------------
    plog = rec.phase_log
    turns = [m for m in rec.voice_messages if m.get("epoch")]
    first_turn = _utc(min(m["epoch"] for m in turns)) if turns else None
    last_turn = _utc(max(m["epoch"] for m in turns)) if turns else None

    rec_start = _utc(rec.float_field("Voice", "timestamp_hrv_recovery_start"))
    rec_end = _utc(rec.float_field("Voice", "timestamp_hrv_recovery_end"))

    voice_start = _utc(plog[0]["started_at"]) if plog else first_turn
    # the Voice page ends where recovery begins; without recovery, last activity
    voice_end = rec_start or (_utc(plog[-1]["advanced_at"]) if plog else None)
    if last_turn and (voice_end is None or last_turn > voice_end):
        voice_end = last_turn

    if voice_start and voice_end and voice_end > voice_start:
        segments.append(
            Segment("voice_session", voice_start, voice_end, inferred=rec_start is None)
        )

    # completed phases straight from the log
    for entry in plog:
        s, e = _utc(entry.get("started_at")), _utc(entry.get("advanced_at"))
        if s and e and e > s:
            segments.append(
                Segment(
                    f"voice:{entry.get('phase', '?')}",
                    s,
                    e,
                    meta={"turns": entry.get("turns"), "reason": entry.get("reason")},
                )
            )

    # the phase that was running when the session ended never gets a log entry:
    # phase_log records transitions only. Reconstruct it from current_phase.
    cur_idx = rec.int_field("Voice", "current_phase")
    cur_started = _utc(rec.float_field("Voice", "current_phase_started"))
    if (
        cur_idx is not None
        and cur_idx == len(plog)
        and cur_idx < len(VOICE_PHASES)
        and cur_started
        and voice_end
        and voice_end > cur_started
    ):
        segments.append(
            Segment(
                f"voice:{VOICE_PHASES[cur_idx]}",
                cur_started,
                voice_end,
                inferred=True,
                meta={"turns": rec.int_field("Voice", "current_phase_turns"), "reason": "session_end"},
            )
        )

    # interview span: between the last Introduction activity and the Voice session.
    # The Chat app records no page timestamps, so both bounds are borrowed; only
    # useful as a coarse marker and clearly labelled inferred.
    if intro_epochs and voice_start:
        intro_last = max(intro_epochs)
        if voice_start > intro_last:
            segments.append(Segment("profiling_interview", intro_last, voice_start, inferred=True))

    if rec_start and rec_end:
        segments.append(Segment("hrv_recovery", rec_start, rec_end))

    # ---- point events ------------------------------------------------------
    vas_at = _utc(rec.float_field("Voice", "vas_stress_timestamp"))
    if vas_at:
        events.append(Event("vas_stress", vas_at, {"value": rec.int_field("Voice", "vas_stress")}))

    eval_at = _utc(rec.float_field("Evaluation", "timestamp_evaluate_questionnaire"))
    if eval_at:
        events.append(Event("evaluation_submitted", eval_at))

    for m in turns:
        sender = m.get("sender", "")
        events.append(
            Event(
                "agent_turn" if sender == "assistant" else "user_turn",
                _utc(m["epoch"]),
                {"label": m.get("label", ""), "words": len((m.get("text") or "").split())},
            )
        )

    segments.sort(key=lambda s: s.start)
    events.sort(key=lambda e: e.at)
    return segments, events


def engagement_from_record(rec: ParticipantRecord) -> dict:
    """Session-level engagement derivable from the wide CSV alone (no Voice export
    needed): turn counts, word totals, per-phase pacing from phase_log."""
    turns = rec.voice_messages
    user = [m for m in turns if m.get("sender") != "assistant"]
    agent = [m for m in turns if m.get("sender") == "assistant"]
    user_words = sum(len((m.get("text") or "").split()) for m in user)
    agent_words = sum(len((m.get("text") or "").split()) for m in agent)
    plog = rec.phase_log
    return {
        "voice_user_turns": len(user),
        "voice_agent_turns": len(agent),
        "voice_user_words": user_words,
        "voice_agent_words": agent_words,
        "voice_word_ratio": round(user_words / agent_words, 3) if agent_words else None,
        "phases_completed": len(plog),
        "phases_early": sum(1 for e in plog if e.get("reason") in ("judge", "flag")),
        "phases_forced": sum(1 for e in plog if e.get("reason") == "forced"),
    }
