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

`self._clock` is an injectable callable (defaults to `lambda: datetime.now(timezone.utc)`)
so tests can drive `notification_handler` deterministically without real sleeps or a BLE
connection — see `HRV_pipeline/tests/test_read_polarH10.py`.

## Recorder timestamps are UTC; the experimenter still works in local time

`read_polarH10.py` now writes UTC timestamps (`self._clock = lambda: datetime.now(timezone.utc)`),
aligning directly with the rest of the study — oTree's `phase_log`, `vas_stress_timestamp`,
and HRV baseline/recovery start/end all use `datetime.now(tz=timezone.utc)`.

The experimenter-facing workflow (`hrv_analyzer.py`'s `baseline_rmssd()` / `rolling_rmssd()`,
and `visualization_runner.py`'s interactive prompt) is unchanged: window start/end times are
still typed as local wall-clock time, read off a clock in the room, e.g. `"Startzeit ...
eingeben (z. B. 19:40:39)"`. `hrv_analyzer.py` handles the translation:

- `LOCAL_TZ = ZoneInfo("Europe/Berlin")` — hardcoded to the study's physical lab location
  (KIT, Karlsruhe — D16), not the analysis machine's system timezone, so results don't
  depend on where the CSV happens to get analyzed.
- `HRVAnalyzer._parse_time()` interprets every typed string as Europe/Berlin local time and
  converts to UTC (`_to_utc()`) before comparing against the UTC-timestamped `self.df`.
  Handles both HH:MM:SS-only input (date taken from the CSV's own local calendar date, not
  its UTC date) and full datetime strings. `zoneinfo` resolves the correct UTC offset for
  the *specific date* being analyzed (CEST/UTC+2 in summer vs. CET/UTC+1 in winter) — see
  `HRV_pipeline/tests/test_hrv_analyzer_tz.py`, which exercises both.
- All console output (`baseline_rmssd`, `rolling_rmssd`, the "CSV geladen" summary) converts
  back to local time before printing, so what the experimenter sees still matches their own
  clock, even though the underlying comparison runs in UTC.
- `hrv_visualization.py` converts `window_end` back to `LOCAL_TZ` before plotting, and pins
  `mdates.DateFormatter(..., tz=LOCAL_TZ)` explicitly, so the RMSSD chart's x-axis also reads
  local time.

**Old (pre-fix) CSVs are not compatible with the new loader.** They contain naive *local*
timestamps (no UTC offset); `_load_csv()` now parses with `utc=True`, which would silently
treat those naive strings as if they were already UTC — reintroducing exactly the kind of
offset bug this change fixes. No real recordings exist yet (pre-pilot), so this hasn't come
up in practice, but any old CSV would need manual conversion before reanalysis.

## CSV schema change

`timestamp, rr_ms, hr_bpm` → `timestamp, rr_ms, hr_bpm, gap_ms`. `hrv_analyzer.py` reads
columns by name, so this is backward-compatible with existing analysis code; old CSVs
recorded before this fix simply won't have a `gap_ms` column.
