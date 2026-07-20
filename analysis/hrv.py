"""HRV metrics over arbitrary time windows, with artifact and BLE-gap handling.

The recorder (HRV_pipeline/read_polarH10.py) wall-clock-stamps every packet and
records gap_ms = time since the previous packet, so BLE dropouts are visible in the
data instead of silently shifting it. This module builds on that:

Cleaning (per beat):
- absolute physiological bounds: RR outside [RR_MIN_MS, RR_MAX_MS] is an artifact;
- relative jump: RR differing from the local median of its neighbours (a centred
  window of +/-LOCAL_MEDIAN_HALFWIN clean beats) by more than MAX_REL_DIFF
  (default 25%, the common Kubios/Malik-style quotient rule) is an artifact. The
  reference is a *local median*, not the last accepted beat: a fixed last-accepted
  anchor goes stale as HR drifts over a long recording, which cascades into
  rejecting nearly every subsequent beat (observed: a 48-min recording flagged 94%
  where the true artifact rate was ~4%).

Pairing (for RMSSD):
- successive differences are only taken between two consecutive *clean* beats, and
  never across a BLE dropout (gap_ms > GAP_THRESHOLD_MS on the later beat) — a
  difference spanning missing beats is not a beat-to-beat difference.

Every metrics dict carries n/artifact/coverage figures so segment quality is
auditable rather than silently trusted.
"""
from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd

RR_MIN_MS = 300.0
RR_MAX_MS = 2000.0
MAX_REL_DIFF = 0.25
GAP_THRESHOLD_MS = 3000.0
# half-width (in beats) of the centred window used for the local-median reference
LOCAL_MEDIAN_HALFWIN = 5


def clean_rr(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with boolean 'artifact' and 'after_gap' columns added.

    A beat is an artifact if it is outside the absolute physiological bounds, or if it
    deviates from the local median of its in-bounds neighbours by more than MAX_REL_DIFF.
    The local median is drift-tolerant (unlike a last-accepted anchor, which cascades) and
    robust to isolated spikes (the spike itself barely moves the median of its neighbours).
    """
    out = df.copy()
    rr = out["rr_ms"].to_numpy(dtype=float)
    n = len(rr)

    in_bounds = (rr >= RR_MIN_MS) & (rr <= RR_MAX_MS)
    artifact = ~in_bounds.copy()

    half = LOCAL_MEDIAN_HALFWIN
    for i in range(n):
        if not in_bounds[i]:
            continue
        lo, hi = max(0, i - half), min(n, i + half + 1)
        neigh = rr[lo:hi][in_bounds[lo:hi]]
        neigh = neigh[np.arange(lo, hi)[in_bounds[lo:hi]] != i]  # exclude the beat itself
        ref = float(np.median(neigh)) if neigh.size else rr[i]
        if ref > 0 and abs(rr[i] - ref) / ref > MAX_REL_DIFF:
            artifact[i] = True

    out["artifact"] = artifact
    out["after_gap"] = out["gap_ms"].to_numpy(dtype=float) > GAP_THRESHOLD_MS
    return out


def window_metrics(clean: pd.DataFrame, start: datetime, end: datetime) -> dict:
    """HRV metrics for [start, end). `clean` must come from clean_rr().

    Returns a dict with rmssd_ms, sdnn_ms, mean_hr_bpm, mean_rr_ms, n_beats,
    n_artifacts, artifact_pct, n_gaps, coverage_pct, duration_s. Metric values are
    None when there is not enough clean data in the window.
    """
    w = clean[(clean["timestamp"] >= start) & (clean["timestamp"] < end)]
    duration_s = (end - start).total_seconds()
    n_beats = len(w)
    ok = w[~w["artifact"]]
    rr = ok["rr_ms"].to_numpy(dtype=float)

    res = {
        "duration_s": round(duration_s, 1),
        "n_beats": n_beats,
        "n_artifacts": int(w["artifact"].sum()),
        "artifact_pct": round(100 * w["artifact"].mean(), 1) if n_beats else None,
        "n_gaps": int(w["after_gap"].sum()),
        "coverage_pct": round(min(100.0, 100 * rr.sum() / (duration_s * 1000)), 1)
        if duration_s > 0 and len(rr)
        else None,
        "mean_rr_ms": round(float(rr.mean()), 2) if len(rr) else None,
        "mean_hr_bpm": round(60000.0 / rr.mean(), 1) if len(rr) else None,
        "sdnn_ms": round(float(rr.std(ddof=1)), 2) if len(rr) >= 2 else None,
        "rmssd_ms": None,
    }

    # successive differences between consecutive clean beats, not across gaps
    if len(ok) >= 2:
        idx = ok.index.to_numpy()
        consecutive = np.diff(idx) == 1  # no artifact beat dropped in between
        later_after_gap = ok["after_gap"].to_numpy()[1:]
        valid = consecutive & ~later_after_gap
        diffs = np.diff(rr)[valid]
        if len(diffs) >= 1:
            res["rmssd_ms"] = round(float(np.sqrt(np.mean(diffs**2))), 2)
            res["n_diff_pairs"] = int(len(diffs))
        else:
            res["n_diff_pairs"] = 0
    else:
        res["n_diff_pairs"] = 0
    return res


def rolling_rmssd(
    clean: pd.DataFrame,
    start: datetime,
    end: datetime,
    window_s: float = 60.0,
    step_s: float = 15.0,
) -> pd.DataFrame:
    """Rolling-window metrics between start and end.

    Returns a DataFrame with window_start, window_end (UTC), rmssd_ms, mean_hr_bpm,
    n_beats, artifact_pct. Windows with no computable RMSSD keep None.
    """
    rows = []
    current = start
    window = pd.Timedelta(seconds=window_s)
    step = pd.Timedelta(seconds=step_s)
    while current + window <= end:
        m = window_metrics(clean, current, current + window)
        rows.append(
            {
                "window_start": current,
                "window_end": current + window,
                "rmssd_ms": m["rmssd_ms"],
                "mean_hr_bpm": m["mean_hr_bpm"],
                "n_beats": m["n_beats"],
                "artifact_pct": m["artifact_pct"],
            }
        )
        current += step
    return pd.DataFrame(rows)
