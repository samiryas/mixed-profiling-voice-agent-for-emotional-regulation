"""Questionnaire scale scoring.

Item keys and scoring rules mirror the instruments as implemented in the oTree apps
(Introduction/models.py, Evaluation/models.py) — see docs/analysis_pipeline.md for
the full provenance table.

- BFI-10 (Rammstedt & John, 2007), 5-point. Stored 0-indexed as b5_0..b5_9 in the
  published item order, so the paper's 1-indexed reverse-coded items {1,3,4,5,7}
  are b5_0, b5_2, b5_3, b5_4, b5_6 here.
- ERQ-10 (Gross & John, 2003), 7-point; subscale item ids per docs/erq_framing.md.
  No reverse-coded items.
- WAI-SR (working alliance), 7-point frequency scale; Goal/Task/Bond subscales of
  3 items each. No reverse-coded items in the implemented selection.
- UEQ+ semantic differentials, 7-point; negative pole is 1, so higher = better,
  no reversal needed.
- Personalization manipulation check (researcher-developed), 7-point agreement;
  pers_3 ("felt generic rather than personal") is reverse-coded.
- Perceived hallucination (exploratory), 7-point agreement; no reversed items.
- vas_stress: 0-10 single item, taken as-is.

Missing items make the affected scale mean None rather than silently averaging a
subset (any-missing -> None), so partial sessions can't masquerade as scored ones.
"""
from __future__ import annotations

from .ingest import ParticipantRecord

BFI10_SCALE_MAX = 5  # 1..5
SEVEN_POINT_MAX = 7  # ERQ / WAI / UEQ+ / pers / hall are all 1..7

# trait -> [(item, reversed)] ; 0-indexed storage order == published BFI-10 order
BFI10_KEYS = {
    "extraversion": [("b5_0", True), ("b5_5", False)],
    "agreeableness": [("b5_1", False), ("b5_6", True)],
    "conscientiousness": [("b5_2", True), ("b5_7", False)],
    "neuroticism": [("b5_3", True), ("b5_8", False)],
    "openness": [("b5_4", True), ("b5_9", False)],
}

ERQ_REAPPRAISAL = ["erq_0", "erq_2", "erq_4", "erq_6", "erq_7", "erq_9"]
ERQ_SUPPRESSION = ["erq_1", "erq_3", "erq_5", "erq_8"]

WAI_SUBSCALES = {
    "goal": ["wai_goal_1", "wai_goal_2", "wai_goal_3"],
    "task": ["wai_task_1", "wai_task_2", "wai_task_3"],
    "bond": ["wai_bond_1", "wai_bond_2", "wai_bond_3"],
}

UEQ_SUBSCALES = {
    "behavior": [f"ueq_behavior_{i}" for i in range(1, 5)],
    "quality": [f"ueq_quality_{i}" for i in range(1, 5)],
    "useful": [f"ueq_useful_{i}" for i in range(1, 5)],
}

PERS_ITEMS = [("pers_1", False), ("pers_2", False), ("pers_3", True)]
HALL_ITEMS = [f"hall_{i}" for i in range(1, 5)]


def _items(rec: ParticipantRecord, app: str, keys_reversed, scale_max: int) -> list[float] | None:
    """Fetch items (applying reversal); None if ANY item is missing."""
    vals = []
    for entry in keys_reversed:
        key, rev = entry if isinstance(entry, tuple) else (entry, False)
        v = rec.int_field(app, key)
        if v is None:
            return None
        vals.append(float(scale_max + 1 - v) if rev else float(v))
    return vals


def _mean(vals: list[float] | None) -> float | None:
    return round(sum(vals) / len(vals), 3) if vals else None


def score_participant(rec: ParticipantRecord) -> dict:
    """All scale scores for one participant. Missing scales are None (e.g. dropouts)."""
    s: dict = {}

    for trait, keys in BFI10_KEYS.items():
        s[f"bfi_{trait}"] = _mean(_items(rec, "Introduction", keys, BFI10_SCALE_MAX))

    s["erq_reappraisal"] = _mean(_items(rec, "Introduction", ERQ_REAPPRAISAL, SEVEN_POINT_MAX))
    s["erq_suppression"] = _mean(_items(rec, "Introduction", ERQ_SUPPRESSION, SEVEN_POINT_MAX))

    wai_means = {}
    for sub, keys in WAI_SUBSCALES.items():
        wai_means[sub] = _mean(_items(rec, "Evaluation", keys, SEVEN_POINT_MAX))
        s[f"wai_{sub}"] = wai_means[sub]
    s["wai_total"] = (
        round(sum(wai_means.values()) / 3, 3) if all(v is not None for v in wai_means.values()) else None
    )

    for sub, keys in UEQ_SUBSCALES.items():
        s[f"ueq_{sub}"] = _mean(_items(rec, "Evaluation", keys, SEVEN_POINT_MAX))

    s["personalization"] = _mean(_items(rec, "Evaluation", PERS_ITEMS, SEVEN_POINT_MAX))
    s["hallucination"] = _mean(_items(rec, "Evaluation", HALL_ITEMS, SEVEN_POINT_MAX))

    s["vas_stress"] = rec.int_field("Voice", "vas_stress")
    s["open_feedback"] = rec.app_field("Evaluation", "open_feedback_1", "") or ""
    return s
