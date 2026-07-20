import numpy as np
import pandas as pd

from analysis.hrv import GAP_THRESHOLD_MS, clean_rr, rolling_rmssd, window_metrics


def make_df(rr_values, start="2026-01-01T10:00:00Z", gaps=None):
    ts, t = [], pd.Timestamp(start)
    for rr in rr_values:
        ts.append(t)
        t = t + pd.Timedelta(milliseconds=rr)
    return pd.DataFrame({
        "timestamp": ts,
        "rr_ms": rr_values,
        "hr_bpm": [round(60000 / r) for r in rr_values],
        "gap_ms": gaps if gaps is not None else [0.0] + [float(r) for r in rr_values[1:]],
    })


def test_rmssd_known_value():
    # alternating 810/790 -> every successive diff is 20 -> RMSSD 20
    df = clean_rr(make_df([810, 790] * 30))
    m = window_metrics(df, df["timestamp"].iloc[0], df["timestamp"].iloc[-1] + pd.Timedelta(seconds=1))
    assert m["rmssd_ms"] == 20.0
    assert m["n_artifacts"] == 0
    assert m["mean_hr_bpm"] == 75.0


def test_absolute_artifact_flagged_and_excluded():
    rr = [800.0] * 10 + [250.0] + [800.0] * 10  # a non-physiological beat
    df = clean_rr(make_df(rr))
    assert df["artifact"].sum() == 1
    m = window_metrics(df, df["timestamp"].iloc[0], df["timestamp"].iloc[-1] + pd.Timedelta(seconds=1))
    # diffs across the dropped beat are not taken -> perfectly steady RR -> RMSSD 0
    assert m["rmssd_ms"] == 0.0
    assert m["n_artifacts"] == 1


def test_relative_jump_flagged():
    rr = [800.0] * 5 + [1500.0] + [800.0] * 5  # physiological range but >25% jump
    df = clean_rr(make_df(rr))
    assert bool(df["artifact"].iloc[5])


def test_slow_hr_drift_not_flagged():
    # HR drifting smoothly from ~750ms to ~1050ms over a long recording: no single beat
    # deviates much from its local neighbours, so nothing should be flagged. (A last-accepted
    # anchor would go stale and cascade into rejecting the whole tail — the bug this guards.)
    rr = list(np.linspace(750.0, 1050.0, 400))
    df = clean_rr(make_df(rr))
    assert df["artifact"].sum() == 0


def test_isolated_spike_amid_drift_flagged_but_neighbours_kept():
    rr = list(np.linspace(760.0, 1040.0, 200))
    rr[100] = 1500.0  # one spurious beat in the middle of the drift
    df = clean_rr(make_df(rr))
    assert bool(df["artifact"].iloc[100])
    assert df["artifact"].sum() == 1  # only the spike, not the drifting neighbours


def test_no_diff_across_ble_gap():
    rr = [800.0, 810.0, 790.0, 810.0]
    gaps = [0.0, 800.0, GAP_THRESHOLD_MS + 1000.0, 800.0]  # dropout before beat 2
    df = clean_rr(make_df(rr, gaps=gaps))
    m = window_metrics(df, df["timestamp"].iloc[0], df["timestamp"].iloc[-1] + pd.Timedelta(seconds=1))
    # valid pairs: (800,810) and (790,810) -> diffs 10, 20 ; never 810->790 across the gap
    assert m["n_diff_pairs"] == 2
    assert m["rmssd_ms"] == round(float(np.sqrt((10**2 + 20**2) / 2)), 2)
    assert m["n_gaps"] == 1


def test_rolling_windows_cover_range():
    df = clean_rr(make_df([800.0] * 240))  # ~192 s of data
    start, end = df["timestamp"].iloc[0], df["timestamp"].iloc[-1]
    roll = rolling_rmssd(df, start, end, window_s=60, step_s=30)
    assert len(roll) >= 4
    assert roll["rmssd_ms"].notna().all()
    assert (roll["window_end"] - roll["window_start"] == pd.Timedelta(seconds=60)).all()
