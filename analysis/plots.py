"""Matplotlib figures for the per-participant and cohort reports.

Static light-mode figures for embedding in the HTML reports / the paper. Styling
follows the project's data-viz conventions: a validated categorical palette in a
FIXED slot order (T1/T2/T3 always get the same hue in every figure), one value
axis per panel (RMSSD and HR are stacked panels, never a dual axis), thin marks,
hairline grid, text in ink colors rather than series colors. The T2/T3 hues fall
below 3:1 contrast on the light surface, so every categorical figure also carries
direct labels (relief rule) and the pipeline always writes the CSV alongside.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from zoneinfo import ZoneInfo

from .pipeline import ParticipantResult

LOCAL_TZ = ZoneInfo("Europe/Berlin")  # lab wall-clock (see HRV_pipeline docs)

# reference palette (light mode) — validated with the dataviz six-checks script
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
SURFACE = "#fcfcfb"

SERIES = ["#2a78d6", "#1baf7a", "#eda100", "#008300", "#4a3aa7", "#e34948"]
CONDITION_COLORS = {"T1": SERIES[0], "T2": SERIES[1], "T3": SERIES[2]}

# background washes for timeline segment bands (very light, labels carry identity)
SEGMENT_WASH = {
    "hrv_baseline": "#cde2fb",  # blue 100
    "profiling_interview": "#f0efec",  # neutral
    "voice:checkin": "#d8f3e8",
    "voice:technique": "#c4ecdc",
    "voice:practice": "#a8e4cc",
    "voice:reflection": "#8fdcbd",
    "hrv_recovery": "#fdeecb",  # warm wash
}
SEGMENT_LABEL = {
    "hrv_baseline": "baseline",
    "profiling_interview": "interview*",
    "voice:checkin": "check-in",
    "voice:technique": "technique",
    "voice:practice": "practice",
    "voice:reflection": "reflection",
    "hrv_recovery": "recovery",
}


def _style_axis(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(BASELINE)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def plot_session_timeline(res: ParticipantResult, out_path: str) -> bool:
    """Rolling RMSSD (1-min and 5-min windows) + heart rate over the whole recording,
    with the reconstructed session segments as labelled background bands and the VAS
    rating marked. Two stacked panels share the time axis (one value axis each); the
    two RMSSD windows share the RMSSD panel's single axis (same measure, same unit)."""
    if res.hrv_df is None or res.rolling_1min.empty:
        return False

    roll_1 = res.rolling_1min.dropna(subset=["rmssd_ms"])
    roll_5 = res.rolling_5min.dropna(subset=["rmssd_ms"])
    hrv = res.hrv_df[~res.hrv_df["artifact"]]

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(13, 6.5), sharex=True, height_ratios=[3, 2],
        facecolor=SURFACE, constrained_layout=True,
    )

    ax1.plot(roll_1["window_end"].dt.tz_convert(LOCAL_TZ), roll_1["rmssd_ms"],
             color=SERIES[0], linewidth=1.3, alpha=0.65, zorder=2, label="1-min window")
    if len(roll_5):
        ax1.plot(roll_5["window_end"].dt.tz_convert(LOCAL_TZ), roll_5["rmssd_ms"],
                 color=SERIES[3], linewidth=2.2, zorder=3, label="5-min window")
    ax1.set_ylabel("RMSSD (ms)", color=INK_2, fontsize=10)
    ax1.legend(loc="upper right", frameon=False, fontsize=9, labelcolor=INK_2)

    t_hr = hrv["timestamp"].dt.tz_convert(LOCAL_TZ)
    ax2.plot(t_hr, hrv["hr_bpm"], color=SERIES[4], linewidth=1.2, zorder=3)
    ax2.set_ylabel("Heart rate (bpm)", color=INK_2, fontsize=10)
    ax2.set_xlabel("Local time (Europe/Berlin)", color=INK_2, fontsize=10)

    for ax in (ax1, ax2):
        _style_axis(ax)
        for seg in res.segments:
            wash = SEGMENT_WASH.get(seg.name)
            if not wash:
                continue
            ax.axvspan(
                seg.start.astimezone(LOCAL_TZ), seg.end.astimezone(LOCAL_TZ),
                color=wash, alpha=0.55, zorder=1, linewidth=0,
            )

    # band labels once, on the top panel
    ymax = ax1.get_ylim()[1]
    for seg in res.segments:
        label = SEGMENT_LABEL.get(seg.name)
        if not label:
            continue
        mid = seg.start + (seg.end - seg.start) / 2
        ax1.annotate(
            label + ("*" if seg.inferred and not label.endswith("*") else ""),
            (mid.astimezone(LOCAL_TZ), ymax), ha="center", va="bottom",
            fontsize=8.5, color=INK_2, annotation_clip=False,
        )

    for ev in res.events:
        if ev.name == "vas_stress":
            for ax in (ax1, ax2):
                ax.axvline(ev.at.astimezone(LOCAL_TZ), color=SERIES[5], linewidth=1.2,
                           linestyle=(0, (4, 3)), zorder=2)
            ax1.annotate(
                f"VAS {ev.meta.get('value', '?')}/10",
                (ev.at.astimezone(LOCAL_TZ), ax1.get_ylim()[0]),
                ha="left", va="bottom", fontsize=8.5, color=SERIES[5],
                xytext=(4, 4), textcoords="offset points",
            )

    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=LOCAL_TZ))
    fig.suptitle(
        f"Session physiology — participant {res.code} ({res.record.condition or 'no condition'})"
        "   ·   *segment boundary inferred",
        color=INK, fontsize=12, x=0.02, ha="left",
    )
    fig.savefig(out_path, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    return True


def plot_segment_rmssd(res: ParticipantResult, out_path: str) -> bool:
    """Per-segment RMSSD bars (single hue — magnitude, not identity), with the
    baseline value as a reference line and direct value labels."""
    seg = res.segment_metrics
    if seg is None or seg.empty:
        return False
    seg = seg[seg["rmssd_ms"].notna()]
    if seg.empty:
        return False

    order = ["hrv_baseline", "voice:checkin", "voice:technique", "voice:practice",
             "voice:reflection", "voice_session", "hrv_recovery"]
    seg = seg.set_index("segment").reindex([s for s in order if s in set(seg["segment"])]).reset_index()

    labels = [SEGMENT_LABEL.get(s, s).rstrip("*") if s != "voice_session" else "voice (all)"
              for s in seg["segment"]]
    fig, ax = plt.subplots(figsize=(9, 4.2), facecolor=SURFACE, constrained_layout=True)
    _style_axis(ax)

    bars = ax.bar(labels, seg["rmssd_ms"], width=0.62, color=SERIES[0], zorder=3)
    for rect, v, art in zip(bars, seg["rmssd_ms"], seg["artifact_pct"]):
        note = f"{v:.0f}"
        if art is not None and art > 5:
            note += f"\n({art:.0f}% artif.)"
        ax.annotate(note, (rect.get_x() + rect.get_width() / 2, rect.get_height()),
                    ha="center", va="bottom", fontsize=9, color=INK_2)

    base = seg[seg["segment"] == "hrv_baseline"]["rmssd_ms"]
    if len(base):
        ax.axhline(float(base.iloc[0]), color=BASELINE, linewidth=1.2, linestyle=(0, (4, 3)), zorder=2)
        ax.annotate("baseline", (len(labels) - 0.5, float(base.iloc[0])), ha="right",
                    va="bottom", fontsize=8.5, color=MUTED)

    ax.set_ylabel("RMSSD (ms)", color=INK_2, fontsize=10)
    ax.set_title(f"RMSSD by session segment — participant {res.code}",
                 color=INK, fontsize=12, loc="left")
    fig.savefig(out_path, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    return True


def plot_condition_comparison(master: pd.DataFrame, measures: list[tuple[str, str]],
                              out_path: str) -> bool:
    """Small-multiple strip plots of key outcomes by condition (T1/T2/T3).

    Conditions keep their fixed palette slots in every figure. Individual points
    (the study is small-N) with a median bar; direct n= labels under each group.
    """
    df = master[master["condition"].isin(CONDITION_COLORS)]
    measures = [(col, label) for col, label in measures if col in df.columns and df[col].notna().any()]
    if df.empty or not measures:
        return False

    ncols = min(3, len(measures))
    nrows = int(np.ceil(len(measures) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.2 * ncols, 3.4 * nrows),
                             facecolor=SURFACE, constrained_layout=True, squeeze=False)

    conditions = [c for c in ("T1", "T2", "T3") if c in set(df["condition"])]
    rng = np.random.default_rng(7)  # deterministic jitter

    for k, (col, label) in enumerate(measures):
        ax = axes[k // ncols][k % ncols]
        _style_axis(ax)
        for i, cond in enumerate(conditions):
            vals = df.loc[df["condition"] == cond, col].dropna().astype(float)
            if len(vals):
                x = i + rng.uniform(-0.12, 0.12, len(vals))
                ax.scatter(x, vals, s=42, color=CONDITION_COLORS[cond], zorder=3,
                           edgecolors=SURFACE, linewidths=1.5)
                ax.hlines(vals.median(), i - 0.22, i + 0.22, color=INK_2, linewidth=2, zorder=4)
            ax.annotate(f"n={len(vals)}", (i, 0), xycoords=("data", "axes fraction"),
                        xytext=(0, -26), textcoords="offset points",
                        ha="center", fontsize=8.5, color=MUTED)
        ax.set_xticks(range(len(conditions)), conditions)
        ax.set_title(label, color=INK, fontsize=10.5, loc="left")

    for k in range(len(measures), nrows * ncols):
        axes[k // ncols][k % ncols].set_visible(False)

    fig.suptitle("Outcomes by condition — median bar, individual participants",
                 color=INK, fontsize=12, x=0.02, ha="left")
    fig.savefig(out_path, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    return True
