# ERQ → reappraisal framing (DEEPEN / INTRODUCE)

Methods note for issue #8 (FR10, design ref D4-rev). Describes how a participant's ERQ responses
select the reappraisal framing used in the Voice session's Technique/Practice phases, and how the
decision boundary is justified without an unjustified numeric threshold.

## What the framing does

The Voice session teaches cognitive reappraisal. The framing personalizes *how*:

- **DEEPEN** — the participant already tends to reappraise; the agent builds on that existing skill.
- **INTRODUCE** — the participant does not habitually reappraise (and may lean on suppression); the
  agent presents reappraisal as a new, learnable skill.

The framing is an instruction injected into the phase prompt (`Voice/prompts/<lang>/framing_*.txt`),
never spoken verbatim. It is personalization, so **condition T1 (profile withheld) always receives
neutral framing** regardless of the computed category, to preserve the condition contrast.

## Where the decision lives (NFR6)

The category is computed **once**, at questionnaire time, in `Introduction`
(`Processing.before_next_page`), and frozen into `participant.vars['erq_framing_category']` along
with the audit z-scores (`participant.vars['erq_framing_z']`). The Voice session only reads that
label — the category is never recomputed per turn or per participant at runtime. This keeps it
deterministic and auditable.

Pure rule: `utils/erq.py` (no oTree dependency; unit-tested in `Voice/tests/test_erq.py`).

## ERQ-10 subscales (Gross & John, 2003)

7-point scale (1 = strongly disagree … 7 = strongly agree). 0-indexed item ids as stored:

- **Reappraisal** (6 items): `erq_0, erq_2, erq_4, erq_6, erq_7, erq_9`
- **Suppression** (4 items): `erq_1, erq_3, erq_5, erq_8`

Subscale score = mean of its items.

## Approach 2 — deterministic rule (runtime)

Norm-reference each subscale, then compare **within-person**:

```
z_reappraisal = (reappraisal_mean − M_reappraisal) / SD_reappraisal
z_suppression = (suppression_mean − M_suppression) / SD_suppression
category = DEEPEN if z_reappraisal ≥ z_suppression else INTRODUCE
```

This is a **relative** comparison (which subscale is more elevated for this person, relative to
population norms), not an absolute cutoff — so there is no arbitrary threshold to justify. Ties
resolve to DEEPEN.

**Normative values (Gross & John, 2003) — PENDING SUPERVISOR SIGN-OFF** (`utils/erq.py`):

| Subscale | M | SD |
|---|---|---|
| Reappraisal | 4.60 | 0.94 |
| Suppression | 3.64 | 1.13 |

Gross & John (2003) report these by sample/gender; swap in the agreed normative source here and in
`utils/erq.py` if a different reference is chosen. Because the rule compares *relative* elevation,
it is less sensitive to the exact norm values than an absolute cutoff would be.

## Approach 1 — empirical LLM majority (offline validation only)

Because a per-participant LLM decision would not be deterministic (violating NFR6), the LLM is used
only to **validate/justify** the boundary, not at runtime. For each sampled profile, the LLM is
queried 10× (`temperature=1.0`) and the majority DEEPEN/INTRODUCE vote is taken — reflecting model
consistency, not a validated clinical threshold.

## Reproducing the comparison

```
# deterministic distribution only
python Voice/tools/erq_framing_analysis.py --n 200

# add the LLM majority and report agreement (needs OPENAI_URL/MODEL/KEY)
python Voice/tools/erq_framing_analysis.py --n 60 --llm
```

The tool prints the DEEPEN/INTRODUCE split and, when `--llm` is set, the **agreement rate** between
the two approaches plus the disagreement cases.

## Results (to fill in before the methods section is finalized)

- [ ] Agreement rate between Approach 1 and Approach 2 over the sampled profiles: ____%
- [ ] Chosen approach: **Approach 2 (deterministic relative comparison)** at runtime, with Approach 1
      as the documented cross-check.
- [ ] Rationale + final normative source: ____

> Note: uniform-random sample profiles are not representative of the real participant distribution
> (they skew toward INTRODUCE under these norms). Use them to check *rule behaviour and agreement*,
> not to estimate the real DEEPEN/INTRODUCE base rate.
