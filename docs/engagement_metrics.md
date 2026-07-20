# Voice session engagement metrics (issue #12)

General interaction/engagement metrics logged for **all conditions (T1/T2/T3)** and exported via
`Voice` `custom_export` (oTree admin → Data → Voice, or `otree custom_export Voice`). These are
useful outcome/covariate data regardless of condition.

Most metrics are **derived at export time** from data already stored (transcripts, timestamps,
`phase_log`), so they add no per-turn runtime cost. The one exception is response latency, which is
measured client-side during the session.

## Per-session columns (repeated on each of a participant's rows)

| Column | Definition |
|---|---|
| `sessionDurationSec` | Last − first `MessageData` timestamp for the participant |
| `totalUserTurns` / `totalAgentTurns` | Count of participant / agent turns |
| `userWordTotal` / `agentWordTotal` | Total words spoken (whitespace tokens of the transcript) |
| `wordRatioUserAgent` | `userWordTotal / agentWordTotal` (turn-taking balance) |
| `meanResponseLatencyMs` | Mean participant response latency across the session |
| `phasesEarly` | Phases advanced by readiness (`phase_log.reason` ∈ {judge, flag}) |
| `phasesForced` | Phases advanced by hitting a turn/time ceiling (`reason` = forced) |

Per-phase durations and turn counts are available in the `phaseLog` JSON column (from #14).

## Per-turn columns

| Column | Definition |
|---|---|
| `wordCount` | Words in this turn's transcript |
| `responseLatencyMs` | Participant turns only: ms between the agent's audio finishing and the participant starting to record (client-measured). Blank on agent turns / if not measurable |
| `pauseRate`, `speechRate`, `pitchMean` | Participant turns only: computed at export from the saved audio via `acoustics.extract_features` (same code the T3 pipeline uses live), so they are available for **all** conditions. Blank if the audio or librosa/ffmpeg is unavailable |

## Notes

- **Scope decision:** general engagement metrics run for all conditions (per the issue's
  recommendation); the acoustic metrics reuse the T3 extraction code but are computed at export, so
  they are not condition-gated.
- **Acoustics at export** require the saved participant audio (`SAVE_USER_AUDIO=True`, default) plus
  librosa/ffmpeg on the export host; they fail open to blank otherwise.
- **Supervisor sign-off:** confirm which of these metrics the analysis actually needs; unused
  columns can be dropped from `custom_export` without touching the runtime path.
