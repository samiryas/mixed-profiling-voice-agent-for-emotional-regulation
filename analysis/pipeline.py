"""Per-participant orchestration: raw record + HRV recording -> analysis results."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from . import hrv as hrv_mod
from .ingest import ParticipantRecord, load_hrv_csv
from .scoring import score_participant
from .timeline import Event, Segment, build_timeline, engagement_from_record

# Segments worth an HRV row (turn-level events are handled separately).
HRV_SEGMENTS = ("hrv_baseline", "voice_session", "hrv_recovery")


@dataclass
class ParticipantResult:
    record: ParticipantRecord
    scores: dict
    engagement: dict
    segments: list[Segment]
    events: list[Event]
    hrv_df: pd.DataFrame | None = None  # cleaned RR series (clean_rr output)
    segment_metrics: pd.DataFrame = field(default_factory=pd.DataFrame)
    # two standard rolling-RMSSD views: a 1-min window (responsive to fast changes,
    # e.g. within a short phase) and a 5-min window (the HRV Task Force's conventional
    # segment length, less noisy but slower to reflect a transition).
    rolling_1min: pd.DataFrame = field(default_factory=pd.DataFrame)
    rolling_5min: pd.DataFrame = field(default_factory=pd.DataFrame)

    @property
    def code(self) -> str:
        return self.record.participant_code


def _deltas(seg_df: pd.DataFrame) -> dict:
    """Reactivity/recovery deltas vs baseline RMSSD (negative reactivity = the
    vagally-mediated HRV drop expected under stress)."""

    def rmssd_of(name: str):
        rows = seg_df[seg_df["segment"] == name]
        return rows.iloc[0]["rmssd_ms"] if len(rows) else None

    base = rmssd_of("hrv_baseline")
    out = {}
    for name, col in (
        ("voice_session", "rmssd_delta_voice"),
        ("hrv_recovery", "rmssd_delta_recovery"),
        ("voice:practice", "rmssd_delta_practice"),
    ):
        v = rmssd_of(name)
        out[col] = round(v - base, 2) if (v is not None and base is not None) else None
    return out


def analyze_participant(
    rec: ParticipantRecord,
    hrv_path: Path | None,
    rolling_1min_step_s: float = 15.0,
    rolling_5min_step_s: float = 60.0,
) -> ParticipantResult:
    scores = score_participant(rec)
    engagement = engagement_from_record(rec)
    segments, events = build_timeline(rec)

    result = ParticipantResult(
        record=rec, scores=scores, engagement=engagement, segments=segments, events=events
    )

    if hrv_path is not None:
        clean = hrv_mod.clean_rr(load_hrv_csv(hrv_path))
        result.hrv_df = clean

        rows = []
        for seg in segments:
            if not (seg.name in HRV_SEGMENTS or seg.name.startswith("voice:")):
                continue
            m = hrv_mod.window_metrics(clean, seg.start, seg.end)
            rows.append(
                {
                    "participant": rec.participant_code,
                    "condition": rec.condition,
                    "segment": seg.name,
                    "start_utc": seg.start,
                    "end_utc": seg.end,
                    "inferred": seg.inferred,
                    **m,
                }
            )
        result.segment_metrics = pd.DataFrame(rows)

        if not clean.empty:
            start, end = clean["timestamp"].iloc[0], clean["timestamp"].iloc[-1]
            result.rolling_1min = hrv_mod.rolling_rmssd(
                clean, start, end, window_s=60.0, step_s=rolling_1min_step_s,
            )
            result.rolling_5min = hrv_mod.rolling_rmssd(
                clean, start, end, window_s=300.0, step_s=rolling_5min_step_s,
            )

    return result


def participant_row(res: ParticipantResult) -> dict:
    """One flat master-table row: identity, condition, scores, engagement, HRV."""
    row: dict = {
        "participant": res.code,
        "session": res.record.session_code,
        "condition": res.record.condition,
        "erq_framing_deepen_vs_introduce": "",  # filled from wide csv if present
        **{k: v for k, v in res.scores.items() if k != "open_feedback"},
        **res.engagement,
        "has_hrv": res.hrv_df is not None,
    }
    seg = res.segment_metrics
    if len(seg):
        for _, r in seg.iterrows():
            prefix = r["segment"].replace("voice:", "phase_")
            row[f"{prefix}_rmssd_ms"] = r["rmssd_ms"]
            row[f"{prefix}_mean_hr_bpm"] = r["mean_hr_bpm"]
            row[f"{prefix}_artifact_pct"] = r["artifact_pct"]
        row.update(_deltas(seg))
    row["open_feedback"] = res.scores.get("open_feedback", "")
    return row
