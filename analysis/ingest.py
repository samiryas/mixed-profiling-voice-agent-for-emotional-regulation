"""Load the study's raw exports into per-participant records.

Inputs handled here:

- ``all_apps_wide_*.csv`` — oTree's wide export, one row per participant, columns
  named ``<App>.<round>.player.<field>`` plus ``participant.*`` / ``session.*``.
- ``participant_<code>_hrv_raw.csv`` — the HRV recorder's output (UTC ISO
  timestamps; see HRV_pipeline/read_polarH10.py). Matched to participants by the
  ``<code>`` in the filename.
- Voice ``custom_export`` CSV (optional) — per-turn engagement rows.

All oTree timestamps are Unix epochs in UTC; the HRV recorder also writes UTC.
Everything downstream compares tz-aware UTC datetimes.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

HRV_FILENAME_RE = re.compile(r"participant_(?P<code>[A-Za-z0-9]+)_hrv_raw\.csv$")

# Voice session phase order (Voice/prompts.py PHASES); index -> name.
VOICE_PHASES = ["checkin", "technique", "practice", "reflection"]


@dataclass
class ParticipantRecord:
    """Everything the pipeline knows about one participant, pre-scoring."""

    participant_code: str
    session_code: str
    condition: str  # T1 | T2 | T3 | '' if Voice app never reached
    label: str = ""
    raw: dict = field(default_factory=dict)  # flattened wide-CSV fields (app-prefixed)

    # -- convenience accessors -------------------------------------------------
    def app_field(self, app: str, fieldname: str, default=None):
        """Value of <app>.1.player.<fieldname> (single-round apps), parsed CSV string."""
        return self.raw.get(f"{app}.1.player.{fieldname}", default)

    def float_field(self, app: str, fieldname: str) -> float | None:
        v = self.app_field(app, fieldname)
        if v in (None, ""):
            return None
        try:
            f = float(v)
        except (TypeError, ValueError):
            return None
        return f if f > 0 else None  # oTree timestamp fields default to 0 == unset

    def int_field(self, app: str, fieldname: str) -> int | None:
        v = self.app_field(app, fieldname)
        if v in (None, ""):
            return None
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return None

    def json_field(self, app: str, fieldname: str, default):
        v = self.app_field(app, fieldname)
        if v in (None, ""):
            return default
        try:
            return json.loads(v)
        except (TypeError, ValueError, json.JSONDecodeError):
            return default

    @property
    def phase_log(self) -> list[dict]:
        return self.json_field("Voice", "phase_log", [])

    @property
    def voice_messages(self) -> list[dict]:
        """Voice conversation turns from cachedMessages. Each msgId embeds the turn's
        epoch timestamp ('B1-1783931296.707817'), which is parsed into 'epoch'."""
        msgs = self.json_field("Voice", "cachedMessages", [])
        out = []
        for m in msgs:
            if not isinstance(m, dict):
                continue
            epoch = None
            msg_id = m.get("msgId", "")
            if "-" in msg_id:
                try:
                    epoch = float(msg_id.rsplit("-", 1)[1])
                except ValueError:
                    epoch = None
            out.append({**m, "epoch": epoch})
        return out

    @property
    def sentiment_log(self) -> list[dict]:
        return self.json_field("Voice", "sentiment_log", [])


def load_wide_csv(path: str | Path) -> list[ParticipantRecord]:
    """Parse an oTree all_apps_wide CSV into one ParticipantRecord per row.

    Rows for participants who never actually started (oTree exports placeholder rows
    for unvisited slots) are dropped: they have participant.visited != 1.
    """
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    records = []
    for _, row in df.iterrows():
        raw = row.to_dict()
        if raw.get("participant.visited", "0") not in ("1", "True", "true"):
            continue
        records.append(
            ParticipantRecord(
                participant_code=raw.get("participant.code", ""),
                session_code=raw.get("session.code", ""),
                condition=raw.get("Voice.1.player.condition", "") or "",
                label=raw.get("participant.label", "") or "",
                raw=raw,
            )
        )
    return records


def load_hrv_csv(path: str | Path) -> pd.DataFrame:
    """Load one HRV recording: tz-aware UTC 'timestamp', float 'rr_ms', 'hr_bpm', 'gap_ms'.

    Sorted by timestamp (the recorder can emit slightly out-of-order rows around
    multi-beat BLE packets). gap_ms is missing on the recording's final partial row
    sometimes — filled with 0.
    """
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, format="ISO8601")
    for col in ("rr_ms", "hr_bpm", "gap_ms"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "gap_ms" not in df.columns:
        df["gap_ms"] = 0.0
    df["gap_ms"] = df["gap_ms"].fillna(0.0)
    df = df.dropna(subset=["rr_ms"])
    return df.sort_values("timestamp").reset_index(drop=True)


def discover_hrv_files(hrv_dir: str | Path) -> dict[str, Path]:
    """Map participant code -> HRV CSV path for every participant_<code>_hrv_raw.csv."""
    out: dict[str, Path] = {}
    for p in sorted(Path(hrv_dir).glob("*.csv")):
        m = HRV_FILENAME_RE.search(p.name)
        if m:
            out[m.group("code")] = p
    return out


def load_voice_export(path: str | Path) -> pd.DataFrame:
    """Load the Voice app custom_export CSV (per-turn engagement rows)."""
    df = pd.read_csv(path, dtype={"participantId": str, "sessionId": str})
    if "timestamp" in df.columns:
        df["epoch"] = pd.to_numeric(df["timestamp"], errors="coerce")
    return df
