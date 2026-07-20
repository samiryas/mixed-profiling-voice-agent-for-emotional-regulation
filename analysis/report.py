"""HTML report generation: one self-contained report per participant + one cohort
report, with the figures embedded as base64 PNGs so files can be shared alone."""
from __future__ import annotations

import base64
import html
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from .pipeline import ParticipantResult

LOCAL_TZ = ZoneInfo("Europe/Berlin")

_CSS = """
body { font-family: system-ui, -apple-system, "Segoe UI", sans-serif; color: #0b0b0b;
       background: #f9f9f7; margin: 2rem auto; max-width: 1100px; padding: 0 1rem; }
h1 { font-size: 1.5rem; } h2 { font-size: 1.15rem; margin-top: 2rem; color: #0b0b0b; }
table { border-collapse: collapse; background: #fcfcfb; font-size: 0.9rem; }
th, td { border: 1px solid #e1e0d9; padding: 0.35rem 0.7rem; text-align: left; }
th { background: #f0efec; font-weight: 600; }
td.num { text-align: right; font-variant-numeric: tabular-nums; }
img { max-width: 100%; background: #fcfcfb; border: 1px solid #e1e0d9; border-radius: 6px; }
.note { color: #52514e; font-size: 0.85rem; }
.flag { color: #d03b3b; font-weight: 600; }
"""


def _img(path: Path) -> str:
    if not path.exists():
        return ""
    b64 = base64.b64encode(path.read_bytes()).decode()
    return f'<img src="data:image/png;base64,{b64}" alt="{html.escape(path.stem)}">'


def _fmt(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    if isinstance(v, float):
        return f"{v:.2f}".rstrip("0").rstrip(".")
    return html.escape(str(v))


def _kv_table(d: dict, keys: list[tuple[str, str]]) -> str:
    rows = "".join(
        f"<tr><th>{html.escape(label)}</th><td class='num'>{_fmt(d.get(key))}</td></tr>"
        for key, label in keys
    )
    return f"<table>{rows}</table>"


def _page(title: str, body: str) -> str:
    stamp = datetime.now(timezone.utc).astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:%M %Z")
    return (
        f"<!doctype html><html><head><meta charset='utf-8'><title>{html.escape(title)}</title>"
        f"<style>{_CSS}</style></head><body><h1>{html.escape(title)}</h1>"
        f"<p class='note'>Generated {stamp} by the analysis pipeline.</p>{body}</body></html>"
    )


SCALE_KEYS = [
    ("bfi_extraversion", "BFI-10 Extraversion (1–5)"),
    ("bfi_agreeableness", "BFI-10 Agreeableness"),
    ("bfi_conscientiousness", "BFI-10 Conscientiousness"),
    ("bfi_neuroticism", "BFI-10 Neuroticism"),
    ("bfi_openness", "BFI-10 Openness"),
    ("erq_reappraisal", "ERQ Reappraisal (1–7)"),
    ("erq_suppression", "ERQ Suppression (1–7)"),
    ("vas_stress", "VAS stress after check-in (0–10)"),
    ("wai_goal", "WAI-SR Goal (1–7)"),
    ("wai_task", "WAI-SR Task"),
    ("wai_bond", "WAI-SR Bond"),
    ("wai_total", "WAI-SR Total"),
    ("ueq_behavior", "UEQ+ Response behaviour (1–7)"),
    ("ueq_quality", "UEQ+ Response quality"),
    ("ueq_useful", "UEQ+ Usefulness"),
    ("personalization", "Perceived personalization (1–7)"),
    ("hallucination", "Perceived hallucination (1–7)"),
]

ENGAGEMENT_KEYS = [
    ("voice_user_turns", "Participant turns (voice)"),
    ("voice_agent_turns", "Agent turns (voice)"),
    ("voice_user_words", "Participant words"),
    ("voice_agent_words", "Agent words"),
    ("voice_word_ratio", "Word ratio user/agent"),
    ("phases_completed", "Phases completed"),
    ("phases_early", "Phases advanced by readiness"),
    ("phases_forced", "Phases advanced by ceiling"),
]


def participant_report(res: ParticipantResult, fig_dir: Path, out_path: Path) -> None:
    seg_rows = ""
    for _, r in res.segment_metrics.iterrows():
        quality = ""
        if r["artifact_pct"] is not None and r["artifact_pct"] > 20:
            quality = " <span class='flag'>check quality</span>"
        seg_rows += (
            f"<tr><td>{html.escape(str(r['segment']))}{' *' if r['inferred'] else ''}</td>"
            f"<td>{r['start_utc'].astimezone(LOCAL_TZ).strftime('%H:%M:%S')}</td>"
            f"<td>{r['end_utc'].astimezone(LOCAL_TZ).strftime('%H:%M:%S')}</td>"
            f"<td class='num'>{_fmt(r['duration_s'])}</td>"
            f"<td class='num'>{_fmt(r['rmssd_ms'])}</td>"
            f"<td class='num'>{_fmt(r['sdnn_ms'])}</td>"
            f"<td class='num'>{_fmt(r['mean_hr_bpm'])}</td>"
            f"<td class='num'>{_fmt(r['artifact_pct'])}{quality}</td>"
            f"<td class='num'>{_fmt(r['n_gaps'])}</td></tr>"
        )
    seg_table = (
        "<table><tr><th>Segment</th><th>Start (local)</th><th>End</th><th>Dur (s)</th>"
        "<th>RMSSD</th><th>SDNN</th><th>Mean HR</th><th>Artifact %</th><th>BLE gaps</th></tr>"
        f"{seg_rows}</table><p class='note'>* boundary inferred (not directly logged).</p>"
        if seg_rows
        else "<p class='note'>No HRV recording matched to this participant.</p>"
    )

    feedback = res.scores.get("open_feedback") or ""
    feedback_html = (
        f"<h2>Open feedback</h2><p>{html.escape(feedback)}</p>" if feedback.strip() else ""
    )

    body = (
        f"<p>Session <b>{html.escape(res.record.session_code)}</b> · condition "
        f"<b>{html.escape(res.record.condition or '—')}</b></p>"
        f"{_img(fig_dir / f'{res.code}_timeline.png')}"
        f"<h2>HRV by session segment</h2>{seg_table}"
        f"{_img(fig_dir / f'{res.code}_segments.png')}"
        f"<h2>Questionnaire scores</h2>{_kv_table(res.scores, SCALE_KEYS)}"
        f"<h2>Engagement</h2>{_kv_table(res.engagement, ENGAGEMENT_KEYS)}"
        f"{feedback_html}"
    )
    out_path.write_text(_page(f"Participant {res.code}", body), encoding="utf-8")


COHORT_MEASURES = [
    ("rmssd_delta_voice", "ΔRMSSD voice vs baseline (ms)"),
    ("rmssd_delta_recovery", "ΔRMSSD recovery vs baseline (ms)"),
    ("vas_stress", "VAS stress (0–10)"),
    ("wai_total", "WAI-SR total (1–7)"),
    ("personalization", "Perceived personalization (1–7)"),
    ("ueq_useful", "UEQ+ usefulness (1–7)"),
    ("ueq_quality", "UEQ+ response quality (1–7)"),
    ("hallucination", "Perceived hallucination (1–7)"),
    ("voice_user_words", "Participant words (voice)"),
]


def _descriptives(master: pd.DataFrame) -> str:
    conds = [c for c in ("T1", "T2", "T3") if c in set(master["condition"])]
    header = "".join(f"<th>{c} mean (sd)</th>" for c in conds)
    rows = ""
    for col, label in COHORT_MEASURES:
        if col not in master.columns or not master[col].notna().any():
            continue
        cells = ""
        for c in conds:
            v = master.loc[master["condition"] == c, col].dropna().astype(float)
            cells += (
                f"<td class='num'>{v.mean():.2f} ({v.std(ddof=1):.2f})</td>"
                if len(v) > 1 else (f"<td class='num'>{v.iloc[0]:.2f} (—)</td>" if len(v) else "<td class='num'>—</td>")
            )
        rows += f"<tr><th>{html.escape(label)}</th>{cells}</tr>"
    return f"<table><tr><th>Measure</th>{header}</tr>{rows}</table>"


def cohort_report(master: pd.DataFrame, fig_dir: Path, out_path: Path) -> None:
    n_by_cond = master.groupby("condition")["participant"].count().to_dict()
    counts = " · ".join(f"{c}: n={n}" for c, n in sorted(n_by_cond.items()))
    body = (
        f"<p>{len(master)} participants ({counts or 'no condition data'})</p>"
        f"{_img(fig_dir / 'cohort_conditions.png')}"
        f"<h2>Descriptives by condition</h2>{_descriptives(master)}"
        "<p class='note'>Full per-participant values: participants_master.csv; "
        "per-segment HRV: hrv_segments_long.csv. Inferential statistics are left to "
        "the stats software of record — these tables are descriptive only.</p>"
    )
    out_path.write_text(_page("Cohort overview", body), encoding="utf-8")
