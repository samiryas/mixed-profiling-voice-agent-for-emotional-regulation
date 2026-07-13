"""Synthetic single-participant fixtures shaped exactly like the real exports.

No real study data lives in the repo: these fixtures mimic the structure of an
oTree all_apps_wide row and an HRV recorder CSV for a participant whose session ran
baseline (5 min) -> interview -> voice session (4 phases) -> recovery (5 min).
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

T0 = 1_783_930_000.0  # arbitrary session anchor (UTC epoch)

# session script (offsets in seconds from T0)
PRIVACY_AT = T0 + 60
BASELINE_START = T0 + 100
BASELINE_END = BASELINE_START + 300
CALIBRATION_AT = BASELINE_END + 5
BIGFIVE_AT = CALIBRATION_AT + 70
ERQ_AT = BIGFIVE_AT + 45
VOICE_START = ERQ_AT + 500  # interview happens in between
PHASE_DUR = 120.0
VAS_AT = VOICE_START + 50
RECOVERY_START = VOICE_START + 4 * PHASE_DUR + 10
RECOVERY_END = RECOVERY_START + 300
EVAL_AT = RECOVERY_END + 30


def phase_log() -> list[dict]:
    entries = []
    for i, name in enumerate(["checkin", "technique", "practice"]):
        start = VOICE_START + i * PHASE_DUR
        entries.append(
            {"phase": name, "started_at": start, "advanced_at": start + PHASE_DUR,
             "turns": 2 + i, "reason": "judge" if i < 2 else "forced"}
        )
    return entries  # reflection left in progress: current_phase=3


def voice_messages() -> list[dict]:
    msgs = []
    for i in range(6):
        epoch = VOICE_START + 30 * i
        sender = "assistant" if i % 2 == 0 else "user"
        label = ("B" if sender == "assistant" else "P") + "1"
        msgs.append(
            {"sender": sender, "label": label, "msgId": f"{label}-{epoch}",
             "text": "one two three four" if sender == "user" else "hello there participant"}
        )
    return msgs


def wide_row(code: str = "abc123", condition: str = "T2") -> dict:
    row = {
        "participant.code": code,
        "participant.label": "",
        "participant.visited": "1",
        "session.code": "sess01",
        "Voice.1.player.condition": condition,
        # Introduction
        "Introduction.1.player.timestamp_privacy": str(PRIVACY_AT),
        "Introduction.1.player.timestamp_hrv_baseline_start": str(BASELINE_START),
        "Introduction.1.player.timestamp_hrv_baseline_end": str(BASELINE_END),
        "Introduction.1.player.timestamp_calibration": str(CALIBRATION_AT),
        "Introduction.1.player.timestamp_bigfive": str(BIGFIVE_AT),
        "Introduction.1.player.timestamp_erq": str(ERQ_AT),
        # BFI-10: all items 4 -> reversed items become 2 -> every trait mean 3.0
        **{f"Introduction.1.player.b5_{i}": "4" for i in range(10)},
        # ERQ: reappraisal items 6, suppression items 2
        **{f"Introduction.1.player.erq_{i}": "6" for i in (0, 2, 4, 6, 7, 9)},
        **{f"Introduction.1.player.erq_{i}": "2" for i in (1, 3, 5, 8)},
        # Voice
        "Voice.1.player.cachedMessages": json.dumps(voice_messages()),
        "Voice.1.player.phase_log": json.dumps(phase_log()),
        "Voice.1.player.current_phase": "3",
        "Voice.1.player.current_phase_started": str(VOICE_START + 3 * PHASE_DUR),
        "Voice.1.player.current_phase_turns": "1",
        "Voice.1.player.vas_stress": "4",
        "Voice.1.player.vas_stress_timestamp": str(VAS_AT),
        "Voice.1.player.timestamp_hrv_recovery_start": str(RECOVERY_START),
        "Voice.1.player.timestamp_hrv_recovery_end": str(RECOVERY_END),
        "Voice.1.player.sentiment_log": "[]",
        # Evaluation
        "Evaluation.1.player.timestamp_evaluate_questionnaire": str(EVAL_AT),
        **{f"Evaluation.1.player.wai_{sub}_{i}": "5" for sub in ("goal", "task", "bond") for i in (1, 2, 3)},
        **{f"Evaluation.1.player.ueq_{sub}_{i}": "6" for sub in ("behavior", "quality", "useful") for i in (1, 2, 3, 4)},
        "Evaluation.1.player.pers_1": "6",
        "Evaluation.1.player.pers_2": "6",
        "Evaluation.1.player.pers_3": "2",  # reversed -> 6
        **{f"Evaluation.1.player.hall_{i}": "2" for i in (1, 2, 3, 4)},
        "Evaluation.1.player.open_feedback_1": "great session",
    }
    return row


def wide_csv(tmp_path, rows: list[dict]) -> str:
    """Write rows as an all_apps_wide-style CSV; returns the path."""
    df = pd.DataFrame(rows).fillna("")
    p = tmp_path / "all_apps_wide_test.csv"
    df.to_csv(p, index=False)
    return str(p)


def hrv_csv(tmp_path, code: str = "abc123",
            rmssd_scale_by_epoch=None) -> str:
    """Synthesize an HRV recording covering the whole scripted session.

    RR alternates +/- delta/2 around 800 ms, so successive diffs are exactly delta
    and RMSSD == delta. A callable rmssd_scale_by_epoch(epoch)->delta lets tests
    vary HRV per segment.
    """
    start = T0
    end = RECOVERY_END + 60
    rows = []
    t = start
    flip = 1
    while t < end:
        delta = rmssd_scale_by_epoch(t) if rmssd_scale_by_epoch else 20.0
        rr = 800.0 + flip * delta / 2
        flip = -flip
        ts = pd.Timestamp(t, unit="s", tz="UTC")
        rows.append({"timestamp": ts.isoformat(), "rr_ms": rr, "hr_bpm": round(60000 / rr),
                     "gap_ms": 800.0})
        t += rr / 1000.0
    p = tmp_path / f"participant_{code}_hrv_raw.csv"
    pd.DataFrame(rows).to_csv(p, index=False)
    return str(p)
