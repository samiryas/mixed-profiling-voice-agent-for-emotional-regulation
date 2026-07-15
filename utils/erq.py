"""Deterministic ERQ (Gross & John, 2003) -> reappraisal framing category.

Maps a participant's ERQ-10 responses to a DEEPEN / INTRODUCE reappraisal framing category
(design ref D4-rev, issue #8). The category is computed once at questionnaire time (Introduction)
and frozen per participant (NFR6 -- auditable, not decided fresh per turn); the Voice session only
reads the stored label.

The rule is a within-person, norm-referenced *relative* comparison of the two subscales rather than
an absolute cutoff: deepen an already-elevated reappraisal habit, otherwise introduce reappraisal as
a new skill. No oTree dependency, so this is unit-testable and importable from offline analysis.
"""
from __future__ import annotations

# ERQ-10 subscale composition, 0-indexed item ids erq_0..erq_9 (Gross & John, 2003).
REAPPRAISAL_ITEMS = (0, 2, 4, 6, 7, 9)   # 6 items
SUPPRESSION_ITEMS = (1, 3, 5, 8)         # 4 items

# Normative subscale means / SDs (Gross & John, 2003). PENDING SUPERVISOR SIGN-OFF -- change here
# if a different normative source is chosen; see docs/erq_framing.md.
NORM_REAPPRAISAL_MEAN = 4.60
NORM_REAPPRAISAL_SD = 0.94
NORM_SUPPRESSION_MEAN = 3.64
NORM_SUPPRESSION_SD = 1.11

DEEPEN = "deepen"
INTRODUCE = "introduce"


def _as_list(items) -> list[float]:
    """Accept either a length-10 sequence or a dict of erq_0..erq_9 -> value."""
    if isinstance(items, dict):
        return [float(items[f"erq_{i}"]) for i in range(10)]
    vals = list(items)
    if len(vals) != 10:
        raise ValueError(f"expected 10 ERQ responses, got {len(vals)}")
    return [float(v) for v in vals]


def subscale_means(items) -> tuple[float, float]:
    """Return (reappraisal_mean, suppression_mean) from the 10 ERQ responses (1..7 each)."""
    vals = _as_list(items)
    reapp = sum(vals[i] for i in REAPPRAISAL_ITEMS) / len(REAPPRAISAL_ITEMS)
    supp = sum(vals[i] for i in SUPPRESSION_ITEMS) / len(SUPPRESSION_ITEMS)
    return reapp, supp


def framing_category(items) -> tuple[str, float, float]:
    """Deterministic DEEPEN/INTRODUCE rule (design ref D4-rev, issue #8).

    Returns (category, z_reappraisal, z_suppression). Ties (z_reappraisal == z_suppression) resolve
    to DEEPEN. The z-scores are returned alongside the label so the decision can be audited.
    """
    reapp, supp = subscale_means(items)
    z_reapp = (reapp - NORM_REAPPRAISAL_MEAN) / NORM_REAPPRAISAL_SD
    z_supp = (supp - NORM_SUPPRESSION_MEAN) / NORM_SUPPRESSION_SD
    category = DEEPEN if z_reapp >= z_supp else INTRODUCE
    return category, z_reapp, z_supp
