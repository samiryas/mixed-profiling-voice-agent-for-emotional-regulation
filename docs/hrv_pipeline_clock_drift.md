# HRV pipeline: per-packet wall-clock timestamping (clock-drift fix)

`HRV_pipeline/read_polarH10.py` timestamps every RR interval it receives from the Polar
H10 over BLE. The original implementation anchored the whole session to one fixed
`recording_start_time` and derived each beat's timestamp by summing RR intervals from
that anchor (`cumulative_ms`). This has two failure modes over a ~60-70 min session:

- **Sensor/host clock drift** — small (tens of ppm), sub-second over a full session. Not
  the practical risk.
- **Dropped BLE notifications** — a connection hiccup (participant movement, strap
  contact loss, RF interference) silently skips some beats. Since the anchor only
  advances by *received* RR intervals, every timestamp after a gap is permanently offset
  from real wall-clock time by the size of the gap, with no way to detect it after the
  fact. There was also no gap visibility in the recorded data at all.

This matters specifically for this pipeline because its value over the original D8 plan
(Polar Flow + Kubios) is aligning HRV data against the oTree app's own timestamps
(`phase_log`, `vas_stress_timestamp`, HRV baseline/recovery start/end) for automated
segmentation — undetected drift silently defeats that.

## The fix

Each BLE notification is now timestamped from its own **wall-clock arrival time**
(`notification_handler`'s `arrival_time = self._clock()`), not from a session-start
anchor. This re-anchors on every single packet, so drift and gaps never compound past
the next packet that arrives. The RR-interval values within one packet are still used to
order and space beats correctly within that packet (device-measured, accurate to
~1/1024s) — only the packet's anchor point comes from the wall clock.

A new `gap_ms` CSV column records the wall-clock time since the previous packet arrived
(0.0 for the very first packet). Values much larger than the sensor's typical ~1s
notification cadence flag a real BLE dropout, so `hrv_analyzer.py` (or manual review) can
exclude or flag the affected window rather than silently trusting data spanning an
undetected gap.

`self._clock` is an injectable callable (defaults to `datetime.now`) so tests can drive
`notification_handler` deterministically without real sleeps or a BLE connection — see
`HRV_pipeline/tests/test_read_polarH10.py`.

## Deliberately unchanged: still naive local time, not UTC

The fix does **not** switch timestamps to UTC, even though the rest of the study
(oTree's `phase_log`, `vas_stress_timestamp`, etc.) uses `datetime.now(tz=timezone.utc)`.
`hrv_analyzer.py` / `visualization_runner.py` prompt the experimenter to manually type a
window start time off a clock in the room (e.g. `"Startzeit ... eingeben (z. B.
19:40:39)"`), which is local wall-clock time. If the recorder wrote UTC while the
analyzer's manual-entry path stayed in local time, every manually-typed window would be
off by the local UTC offset (e.g. 2 hours during CEST) — a worse, silent bug than the one
this fix addresses. Switching both the recorder and the analyzer's input/UX to UTC
consistently is a reasonable follow-up, but is a separate, coordinated change (touches
the experimenter-facing workflow) and is out of scope here.

## CSV schema change

`timestamp, rr_ms, hr_bpm` → `timestamp, rr_ms, hr_bpm, gap_ms`. `hrv_analyzer.py` reads
columns by name, so this is backward-compatible with existing analysis code; old CSVs
recorded before this fix simply won't have a `gap_ms` column.
