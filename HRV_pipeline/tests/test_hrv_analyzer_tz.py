"""Unit tests for HRV_pipeline/hrv_analyzer.py's local <-> UTC time handling.

The recorder (read_polarH10.py) writes UTC-timestamped CSVs; the experimenter still types
window start/end times as local (Europe/Berlin) wall-clock time, reading a clock in the
room. This module's job is exactly that translation -- getting it wrong either silently
selects the wrong window (a data-integrity bug) or crashes on a nonexistent/ambiguous
local time (DST transitions). Requires pandas/numpy (see HRV_pipeline's requirements.txt
pins).

Run from the repo root:
    python3 HRV_pipeline/tests/test_hrv_analyzer_tz.py
    pytest HRV_pipeline/tests/test_hrv_analyzer_tz.py
"""
import csv
import importlib.util
import pathlib
import tempfile
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

_MODULE_PATH = pathlib.Path(__file__).resolve().parents[1] / "hrv_analyzer.py"
_spec = importlib.util.spec_from_file_location("hrv_analyzer_under_test", _MODULE_PATH)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

HRVAnalyzer = _mod.HRVAnalyzer
LOCAL_TZ = _mod.LOCAL_TZ


def _write_csv(csv_path, start_utc: datetime, n: int, rr_ms: float = 800.0):
    """Synthesize a recorder-format CSV: UTC ISO timestamps, evenly spaced by rr_ms."""
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "rr_ms", "hr_bpm", "gap_ms"])
        t = start_utc
        for i in range(n):
            w.writerow([t.isoformat(timespec="milliseconds"), rr_ms, 70, 0.0 if i == 0 else rr_ms])
            t += timedelta(milliseconds=rr_ms)


def test_local_summer_time_converts_to_utc_plus_two(tmp_path):
    """CEST (July, Europe/Berlin) is UTC+2. A participant window at 19:40:39 local must
    select data recorded from 17:40:39 UTC -- this is exactly the 2-hour bug that a naive
    local-vs-UTC comparison would introduce silently."""
    csv_path = tmp_path / "hrv.csv"
    start_utc = datetime(2026, 7, 11, 17, 40, 39, tzinfo=timezone.utc)
    _write_csv(csv_path, start_utc, n=400)  # ~5.3 min of 800ms beats

    a = HRVAnalyzer(str(csv_path))
    rmssd = a.baseline_rmssd(start_time="19:40:39")  # local (Europe/Berlin) time
    assert rmssd is not None  # only succeeds if the 5-min UTC window was located correctly


def test_local_winter_time_converts_to_utc_plus_one(tmp_path):
    """CET (January, Europe/Berlin) is UTC+1 -- different offset than summer, proving the
    conversion uses the correct offset for the *date in question*, not a fixed constant."""
    csv_path = tmp_path / "hrv.csv"
    start_utc = datetime(2026, 1, 11, 18, 40, 39, tzinfo=timezone.utc)
    _write_csv(csv_path, start_utc, n=400)

    a = HRVAnalyzer(str(csv_path))
    rmssd = a.baseline_rmssd(start_time="19:40:39")  # local (Europe/Berlin) time
    assert rmssd is not None


def test_wrong_offset_would_miss_the_window(tmp_path):
    """Negative control: confirms the test setup is actually sensitive to the offset --
    a window request using the WRONG (UTC, not local) hour should find no/insufficient
    data, proving the previous two tests are not passing by accident."""
    csv_path = tmp_path / "hrv.csv"
    start_utc = datetime(2026, 7, 11, 17, 40, 39, tzinfo=timezone.utc)
    _write_csv(csv_path, start_utc, n=400)

    a = HRVAnalyzer(str(csv_path))
    # naively treating "17:40:39" as local (Europe/Berlin) would target 15:40:39 UTC --
    # two hours before any recorded data exists.
    rmssd = a.baseline_rmssd(start_time="17:40:39")
    assert rmssd is None


def test_full_datetime_string_is_also_treated_as_local(tmp_path):
    csv_path = tmp_path / "hrv.csv"
    start_utc = datetime(2026, 7, 11, 17, 40, 39, tzinfo=timezone.utc)
    _write_csv(csv_path, start_utc, n=400)

    a = HRVAnalyzer(str(csv_path))
    rmssd = a.baseline_rmssd(start_time="2026-07-11T19:40:39")  # local, matches CSV's date
    assert rmssd is not None


def test_rolling_rmssd_windows_align_with_utc_data(tmp_path):
    csv_path = tmp_path / "hrv.csv"
    start_utc = datetime(2026, 7, 11, 17, 40, 39, tzinfo=timezone.utc)
    _write_csv(csv_path, start_utc, n=400)

    a = HRVAnalyzer(str(csv_path))
    results = a.rolling_rmssd(
        start_time="19:40:39", end_time="19:45:00", window_minutes=1, step_seconds=30,
    )
    assert len(results) > 0
    assert any(r["n_rr"] > 0 for r in results)


def test_to_utc_passes_through_already_aware_timestamps():
    import pandas as pd

    aware = pd.Timestamp("2026-07-11T17:40:39", tz=timezone.utc)
    assert HRVAnalyzer._to_utc(aware) == aware


def test_to_utc_localizes_naive_as_europe_berlin():
    import pandas as pd

    naive = pd.Timestamp("2026-07-11T19:40:39")
    result = HRVAnalyzer._to_utc(naive)
    expected = pd.Timestamp("2026-07-11T19:40:39", tz=LOCAL_TZ).tz_convert(timezone.utc)
    assert result == expected


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            if fn.__code__.co_argcount == 1:
                with tempfile.TemporaryDirectory() as d:
                    fn(pathlib.Path(d))
            else:
                fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
        except Exception as e:
            failed += 1
            print(f"ERROR {fn.__name__}: {e!r}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    raise SystemExit(1 if failed else 0)
