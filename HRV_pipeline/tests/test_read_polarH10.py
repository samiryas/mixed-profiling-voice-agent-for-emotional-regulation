"""Unit tests for HRV_pipeline/read_polarH10.py's per-packet wall-clock timestamping
(clock-drift fix). Pure logic + a lightweight fake CSV sink -- no real BLE hardware needed.

Run from the repo root:
    python3 HRV_pipeline/tests/test_read_polarH10.py
    pytest HRV_pipeline/tests/test_read_polarH10.py
"""
import csv
import importlib.util
import pathlib
import struct
import tempfile
from datetime import datetime, timedelta, timezone

_MODULE_PATH = pathlib.Path(__file__).resolve().parents[1] / "read_polarH10.py"
_spec = importlib.util.spec_from_file_location("read_polarH10_under_test", _MODULE_PATH)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

readPolarH10 = _mod.readPolarH10


def _hr_packet(hr_bpm: int, rr_intervals_ms) -> bytearray:
    """Build a synthetic Bluetooth Heart Rate Measurement packet: 8-bit HR, RR-intervals
    present, no energy-expended field -- matches what a real Polar H10 sends."""
    flags = 0x10  # RR-interval-present bit; HR-format bit (0x01) left unset -> 8-bit HR
    payload = bytearray([flags, hr_bpm])
    for rr_ms in rr_intervals_ms:
        raw = round(rr_ms / 1000 * 1024)
        payload += struct.pack("<H", raw)
    return payload


class _FakeClock:
    """Deterministic, manually-advanced stand-in for datetime.now() in tests."""

    def __init__(self, start: datetime):
        self._now = start

    def advance(self, ms: float):
        self._now += timedelta(milliseconds=ms)

    def __call__(self) -> datetime:
        return self._now


def _make_recorder(csv_path) -> "readPolarH10":
    rec = readPolarH10(output_file=str(csv_path))
    rec.csv_file = open(rec.output_file, mode="w", newline="", encoding="utf-8")
    rec.csv_writer = csv.writer(rec.csv_file)
    rec.csv_writer.writerow(["timestamp", "rr_ms", "hr_bpm", "gap_ms"])
    rec.is_recording = True
    rec._last_arrival = None
    return rec


def _read_rows(csv_path):
    with open(csv_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_parse_heart_rate_measurement_roundtrips_rr_intervals():
    packet = _hr_packet(hr_bpm=72, rr_intervals_ms=[812.5, 798.0])
    hr_bpm, rr_intervals_ms = readPolarH10(output_file="unused").parse_heart_rate_measurement(packet)
    assert hr_bpm == 72
    assert len(rr_intervals_ms) == 2
    # 1/1024s quantization -> exact to ~1ms
    assert abs(rr_intervals_ms[0] - 812.5) < 1.0
    assert abs(rr_intervals_ms[1] - 798.0) < 1.0


def test_single_beat_packet_anchors_to_arrival_time(tmp_path):
    csv_path = tmp_path / "hrv.csv"
    rec = _make_recorder(csv_path)
    clock = _FakeClock(datetime(2026, 7, 11, 14, 0, 0, tzinfo=timezone.utc))
    rec._clock = clock
    expected = clock._now

    rec.notification_handler(sender=None, data=_hr_packet(70, [800.0]))
    rec.csv_file.close()

    rows = _read_rows(csv_path)
    assert len(rows) == 1
    beat_time = datetime.fromisoformat(rows[0]["timestamp"])
    assert beat_time == expected  # only beat in the packet -> right at arrival time
    assert float(rows[0]["gap_ms"]) == 0.0  # first packet: no prior arrival to diff against


def test_multi_beat_packet_preserves_within_packet_rr_spacing(tmp_path):
    csv_path = tmp_path / "hrv.csv"
    rec = _make_recorder(csv_path)
    clock = _FakeClock(datetime(2026, 7, 11, 14, 0, 0, tzinfo=timezone.utc))
    rec._clock = clock
    expected = clock._now

    # three beats in one packet: the last ends at arrival_time, earlier ones offset backward
    # by their own RR spacing (chronological order, oldest first, per the BLE HR spec)
    rec.notification_handler(sender=None, data=_hr_packet(70, [800.0, 810.0, 790.0]))
    rec.csv_file.close()

    rows = _read_rows(csv_path)
    assert len(rows) == 3
    times = [datetime.fromisoformat(r["timestamp"]) for r in rows]
    assert times[2] == expected
    # 1/1024s RR quantization + millisecond isoformat rounding -> exact to ~2ms
    assert abs((times[2] - times[1]).total_seconds() * 1000 - 790.0) < 2.0
    assert abs((times[1] - times[0]).total_seconds() * 1000 - 810.0) < 2.0


def test_gap_does_not_propagate_into_later_timestamps(tmp_path):
    """The core drift fix: a dropped-notification gap must not shift subsequent beats away
    from real wall-clock time, the way the old cumulative-RR-sum anchor did."""
    csv_path = tmp_path / "hrv.csv"
    rec = _make_recorder(csv_path)
    clock = _FakeClock(datetime(2026, 7, 11, 14, 0, 0, tzinfo=timezone.utc))
    rec._clock = clock

    # packet 1: one beat, right at t=0
    rec.notification_handler(sender=None, data=_hr_packet(70, [800.0]))

    # simulate a 6-second BLE dropout (connection hiccup) -- no notifications arrive
    clock.advance(6000.0)

    # packet 2 arrives after the gap: one beat
    rec.notification_handler(sender=None, data=_hr_packet(70, [800.0]))
    rec.csv_file.close()

    rows = _read_rows(csv_path)
    assert len(rows) == 2

    t0 = datetime.fromisoformat(rows[0]["timestamp"])
    t1 = datetime.fromisoformat(rows[1]["timestamp"])
    # new beat is anchored to real elapsed wall-clock time (~6000ms later)...
    assert abs((t1 - t0).total_seconds() * 1000 - 6000.0) < 1.0
    # ...NOT to the old cumulative-RR-sum result, which would have placed it at only
    # 800+800=1600ms after t0 -- 4.4s of silently absorbed drift.
    assert (t1 - t0).total_seconds() * 1000 > 1600.0 + 1000

    # and the gap is visible in the diagnostic column for post-hoc exclusion
    assert float(rows[0]["gap_ms"]) == 0.0
    assert abs(float(rows[1]["gap_ms"]) - 6000.0) < 1.0


def test_packet_with_no_rr_intervals_still_updates_gap_tracking(tmp_path):
    """A heart-rate-only packet (no RR data) must not be silently dropped from gap tracking,
    or the next real packet's gap_ms would be measured from the wrong reference point."""
    csv_path = tmp_path / "hrv.csv"
    rec = _make_recorder(csv_path)
    clock = _FakeClock(datetime(2026, 7, 11, 14, 0, 0, tzinfo=timezone.utc))
    rec._clock = clock

    hr_only_flags = 0x00  # no RR-interval-present bit
    rec.notification_handler(sender=None, data=bytearray([hr_only_flags, 70]))
    clock.advance(1000.0)
    rec.notification_handler(sender=None, data=_hr_packet(70, [800.0]))
    rec.csv_file.close()

    rows = _read_rows(csv_path)
    assert len(rows) == 1  # only the RR-bearing packet writes a row
    assert abs(float(rows[0]["gap_ms"]) - 1000.0) < 1.0  # gap measured from the HR-only packet


def test_timestamps_are_utc(tmp_path):
    """Beat timestamps must carry a UTC offset, so they align directly with oTree's own
    datetime.now(timezone.utc)-based timestamps (phase_log, vas_stress_timestamp, ...)."""
    csv_path = tmp_path / "hrv.csv"
    rec = _make_recorder(csv_path)
    rec._clock = _FakeClock(datetime(2026, 7, 11, 14, 0, 0, tzinfo=timezone.utc))

    rec.notification_handler(sender=None, data=_hr_packet(70, [800.0]))
    rec.csv_file.close()

    rows = _read_rows(csv_path)
    assert rows[0]["timestamp"].endswith("+00:00")
    parsed = datetime.fromisoformat(rows[0]["timestamp"])
    assert parsed.tzinfo is not None
    assert parsed.utcoffset().total_seconds() == 0


def test_csv_header_includes_gap_ms(tmp_path):
    csv_path = tmp_path / "hrv.csv"
    rec = _make_recorder(csv_path)
    rec.csv_file.close()
    with open(csv_path, newline="", encoding="utf-8") as f:
        header = next(csv.reader(f))
    assert header == ["timestamp", "rr_ms", "hr_bpm", "gap_ms"]


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
