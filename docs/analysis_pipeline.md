# Data analysis & evaluation pipeline (`analysis/`)

Automates what was previously manual: aligning the Polar H10 HRV recording with the
oTree session timestamps, segmenting it by study phase, scoring the questionnaires,
and producing per-participant and cohort-level reports ready for the paper.

## Inputs

| Input | Source | Required |
|---|---|---|
| `all_apps_wide_*.csv` | oTree admin → Data → "All apps, wide" | yes |
| `participant_<code>_hrv_raw.csv` (one per participant, any directory) | `HRV_pipeline/recording_main.py` | optional per participant |
| Voice `custom_export` CSV | oTree admin → Data → Voice | optional |

HRV files are matched to participants by the `<code>` in the filename
(`participant.code` in oTree). Participants without a recording still get their
questionnaire scores, timeline, and engagement metrics.

## Running

```
pip install -r requirements.txt          # pandas / numpy / matplotlib
python -m analysis --wide data/all_apps_wide_20260713.csv \
                   --hrv-dir data/hrv \
                   --out results
```

Optional: `--voice-export Voice.csv` (adds response-latency aggregates),
`--rolling-window` / `--rolling-step` (rolling RMSSD parameters, default 60 s / 15 s).

Keep raw study data out of git: `data/` and `results/` are git-ignored — put exports
there.

## Outputs (under `--out`)

| File | Contents |
|---|---|
| `participants_master.csv` | one row per participant: condition, every scale score, engagement metrics, per-segment RMSSD/HR/artifact-%, deltas vs baseline |
| `hrv_segments_long.csv` | tidy long table: participant × segment × HRV metrics — the stats-software input for physiological analyses |
| `hrv_rolling_<code>.csv` | rolling RMSSD/HR time series per participant |
| `report_<code>.html` | self-contained per-participant report (figures embedded) |
| `cohort_report.html` | condition descriptives + comparison figure |
| `figures/*.png` | all figures separately, for the paper |

## How the session timeline is reconstructed

Every boundary comes from a timestamp the app itself logged (Unix epoch, UTC — the
HRV recorder also stamps UTC, which is what makes automatic alignment sound; see
`docs/hrv_pipeline_clock_drift.md`):

- **hrv_baseline** — `Introduction.timestamp_hrv_baseline_start/_end`
- **voice:<phase>** — Voice `phase_log` entries (`started_at`/`advanced_at`, plus
  turns and advance reason). The phase running when the session ended never gets a
  log entry (the log records transitions), so it is reconstructed from
  `current_phase`/`current_phase_started` and closed at recovery start — flagged
  `inferred` in every output.
- **voice_session** — first phase start → `timestamp_hrv_recovery_start`.
- **hrv_recovery** — `Voice.timestamp_hrv_recovery_start/_end`.
- **profiling_interview** — approximate (the Chat app logs no page timestamps):
  last Introduction activity → Voice start; always flagged inferred.
- Point events: questionnaire submits, calibration, **VAS stress** (with value),
  every voice turn (timestamps parsed out of `msgId`).

## HRV metric definitions

Cleaning per beat: RR outside 300–2000 ms, or >25 % change vs the previous accepted
beat (Kubios-style quotient rule) → artifact. RMSSD uses successive differences
between consecutive clean beats only, and never across a BLE dropout
(`gap_ms` > 3000 ms). Each segment row reports `n_beats`, `artifact_pct`, `n_gaps`,
and `coverage_pct` so window quality is auditable; the per-participant report flags
segments with >20 % artifacts.

- `rmssd_ms`, `sdnn_ms`, `mean_hr_bpm`, `mean_rr_ms` per segment
- `rmssd_delta_voice` = voice-session RMSSD − baseline RMSSD (stress reactivity;
  more negative = stronger vagal withdrawal)
- `rmssd_delta_recovery` = recovery RMSSD − baseline RMSSD
- `rmssd_delta_practice` = practice-phase RMSSD − baseline RMSSD

## Questionnaire scoring provenance

| Scale | Items | Rule |
|---|---|---|
| BFI-10 (Rammstedt & John 2007) | `b5_0..b5_9`, 1–5 | reverse `b5_0, b5_2, b5_3, b5_4, b5_6`; trait = mean of its 2 items |
| ERQ-10 (Gross & John 2003) | `erq_0..erq_9`, 1–7 | reappraisal = mean(0,2,4,6,7,9); suppression = mean(1,3,5,8) — same ids as `docs/erq_framing.md` |
| WAI-SR | `wai_{goal,task,bond}_{1..3}`, 1–7 | subscale means + total (mean of subscales) |
| UEQ+ | `ueq_{behavior,quality,useful}_{1..4}`, 1–7 | subscale means (positive pole = 7, no reversal) |
| Personalization check | `pers_1..3`, 1–7 | reverse `pers_3`; mean |
| Perceived hallucination | `hall_1..4`, 1–7 | mean |
| VAS stress | `vas_stress` | as-is (0–10, taken after check-in) |

A scale with any missing item scores `None` (dropouts can't silently average a
subset).

Engagement metrics derived from the wide CSV alone: user/agent turns and word
totals (from Voice `cachedMessages`; per-turn epochs parsed from `msgId`), phases
completed / advanced-by-readiness / advanced-by-ceiling (from `phase_log`). Richer
per-turn metrics (response latency, acoustics) come from the optional Voice export.

## Tests

```
python -m pytest analysis/tests/ -q
```

Fixtures are fully synthetic (`analysis/tests/fixtures.py`) — no participant data
in the repo. They cover reverse-coded scoring, known-value RMSSD, artifact/gap
exclusion, timeline reconstruction (including the in-progress-phase case and a
missing-recovery dropout), and the master-row assembly.
