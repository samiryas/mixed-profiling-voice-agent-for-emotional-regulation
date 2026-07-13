"""CLI entry point.

    python -m analysis --wide data/all_apps_wide_20260713.csv \
                       --hrv-dir data/hrv \
                       [--voice-export data/Voice.csv] \
                       --out results

Outputs, under --out:
    participants_master.csv     one row per participant: condition, scale scores,
                                engagement, per-segment HRV + deltas vs baseline
    hrv_segments_long.csv       participant x segment HRV metrics (tidy long)
    hrv_rolling_<code>.csv      rolling RMSSD series per participant
    figures/                    all PNGs
    report_<code>.html          per-participant report (self-contained)
    cohort_report.html          condition comparison + descriptives
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from .ingest import discover_hrv_files, load_voice_export, load_wide_csv
from .pipeline import analyze_participant, participant_row
from .plots import plot_condition_comparison, plot_segment_rmssd, plot_session_timeline
from .report import COHORT_MEASURES, cohort_report, participant_report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m analysis", description=__doc__)
    ap.add_argument("--wide", required=True, help="oTree all_apps_wide CSV")
    ap.add_argument("--hrv-dir", default=None, help="directory of participant_<code>_hrv_raw.csv files")
    ap.add_argument("--voice-export", default=None, help="Voice app custom_export CSV (optional)")
    ap.add_argument("--out", default="results", help="output directory (default: results/)")
    ap.add_argument("--rolling-window", type=float, default=60.0, help="rolling RMSSD window seconds")
    ap.add_argument("--rolling-step", type=float, default=15.0, help="rolling RMSSD step seconds")
    args = ap.parse_args(argv)

    out = Path(args.out)
    fig_dir = out / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    records = load_wide_csv(args.wide)
    if not records:
        print("No visited participants found in the wide CSV.", file=sys.stderr)
        return 1
    hrv_files = discover_hrv_files(args.hrv_dir) if args.hrv_dir else {}
    print(f"{len(records)} participant(s) in wide CSV; HRV recordings for "
          f"{sum(1 for r in records if r.participant_code in hrv_files)} of them.")

    voice_export = load_voice_export(args.voice_export) if args.voice_export else None

    master_rows, seg_frames = [], []
    for rec in records:
        code = rec.participant_code
        res = analyze_participant(
            rec, hrv_files.get(code),
            rolling_window_s=args.rolling_window, rolling_step_s=args.rolling_step,
        )

        made_timeline = plot_session_timeline(res, str(fig_dir / f"{code}_timeline.png"))
        made_segments = plot_segment_rmssd(res, str(fig_dir / f"{code}_segments.png"))
        participant_report(res, fig_dir, out / f"report_{code}.html")

        row = participant_row(res)
        if voice_export is not None and "participantId" in voice_export.columns:
            mine = voice_export[voice_export["participantId"] == code]
            if len(mine):
                lat = pd.to_numeric(mine.get("meanResponseLatencyMs"), errors="coerce").dropna()
                if len(lat):
                    row["mean_response_latency_ms"] = float(lat.iloc[0])
        master_rows.append(row)

        if len(res.segment_metrics):
            seg_frames.append(res.segment_metrics)
        if len(res.rolling):
            res.rolling.to_csv(out / f"hrv_rolling_{code}.csv", index=False)

        print(f"  {code}: condition={rec.condition or '—'} hrv={'yes' if code in hrv_files else 'no'} "
              f"timeline_fig={'yes' if made_timeline else 'no'} segment_fig={'yes' if made_segments else 'no'}")

    master = pd.DataFrame(master_rows)
    master.to_csv(out / "participants_master.csv", index=False)
    if seg_frames:
        pd.concat(seg_frames, ignore_index=True).to_csv(out / "hrv_segments_long.csv", index=False)

    plot_condition_comparison(master, COHORT_MEASURES, str(fig_dir / "cohort_conditions.png"))
    cohort_report(master, fig_dir, out / "cohort_report.html")

    print(f"Done. Outputs in {out}/ (cohort_report.html, report_<code>.html, participants_master.csv)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
