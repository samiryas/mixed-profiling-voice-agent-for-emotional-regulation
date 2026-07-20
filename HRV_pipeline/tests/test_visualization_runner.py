"""Regression test for HRV_pipeline/visualization_runner.py's method-name mismatch bug.

`main()` called `runner.run_baseline_calculation(...)`, a method that did not exist on
`HRVVisualizationRunner` (only `run_baseline_visualization` was defined, and it called
`self.visualizer.plot_baseline_rmssd(...)`, a method that does not exist on `HRVVisualizer`
either -- baseline is a single 5-min scalar, not a time series, so there is nothing to plot).
Both crashed on first use. Requires pandas/numpy/matplotlib (HRV_pipeline's requirements.txt
pins) and `HRV_pipeline/` importable as a flat module directory (its own scripts import each
other by bare name, e.g. `from hrv_analyzer import HRVAnalyzer`).

Run from the repo root:
    python3 HRV_pipeline/tests/test_visualization_runner.py
    pytest HRV_pipeline/tests/test_visualization_runner.py
"""
import csv
import os
import sys
import tempfile
import pathlib
from datetime import datetime, timedelta, timezone

os.environ.setdefault("MPLBACKEND", "Agg")  # headless -- no display needed for these tests

_HRV_PIPELINE_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(_HRV_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(_HRV_PIPELINE_DIR))

from visualization_runner import HRVVisualizationRunner  # noqa: E402


def _write_csv(csv_path, start_utc: datetime, n: int, rr_ms: float = 800.0):
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "rr_ms", "hr_bpm", "gap_ms"])
        t = start_utc
        for i in range(n):
            w.writerow([t.isoformat(timespec="milliseconds"), rr_ms, 70, 0.0 if i == 0 else rr_ms])
            t += timedelta(milliseconds=rr_ms)


def test_run_baseline_calculation_does_not_crash(tmp_path):
    """The bug this guards against: calling this method used to raise AttributeError."""
    csv_path = tmp_path / "hrv.csv"
    start_utc = datetime(2026, 7, 11, 17, 40, 39, tzinfo=timezone.utc)  # 19:40:39 local (CEST)
    _write_csv(csv_path, start_utc, n=400)

    runner = HRVVisualizationRunner(csv_file=str(csv_path))
    runner.run_baseline_calculation(start_time="19:40:39")  # local time, as main() collects it


def test_run_rolling_visualization_still_works(tmp_path):
    """Was already correct before the fix -- guard against a regression here too."""
    csv_path = tmp_path / "hrv.csv"
    start_utc = datetime(2026, 7, 11, 17, 40, 39, tzinfo=timezone.utc)
    _write_csv(csv_path, start_utc, n=400)

    runner = HRVVisualizationRunner(csv_file=str(csv_path))
    runner.run_rolling_visualization(
        start_time="19:40:39", end_time="19:45:00", window_minutes=1, step_seconds=30,
    )


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
