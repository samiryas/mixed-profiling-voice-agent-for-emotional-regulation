#!/usr/bin/env python3
"""Validate the ERQ -> DEEPEN/INTRODUCE framing rule (issue #8 acceptance criteria).

Compares the two approaches from the issue over a sample of generated ERQ profiles:

  Approach 2 (deterministic, the runtime rule): utils.erq.framing_category -- a within-person,
      norm-referenced relative comparison of the reappraisal vs suppression subscales.
  Approach 1 (empirical): query the LLM 10x per profile and take the majority DEEPEN/INTRODUCE
      recommendation, reflecting model consistency (not a validated clinical threshold).

Prints the agreement rate between the two and lists disagreements, for the methods section.
Approach 1 is optional (needs an OpenAI-compatible endpoint); Approach 2 always runs.

Usage (from repo root):
    python Voice/tools/erq_framing_analysis.py --n 200            # deterministic only
    python Voice/tools/erq_framing_analysis.py --n 60 --llm       # + LLM majority (needs OPENAI_*)
"""
from __future__ import annotations

import argparse
import os
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root -> import utils.erq

from utils.erq import framing_category, subscale_means, DEEPEN, INTRODUCE  # noqa: E402


def sample_profiles(n: int, seed: int = 0):
    """Yield n random ERQ-10 response vectors (each item 1..7, uniform)."""
    rng = random.Random(seed)
    for _ in range(n):
        yield [rng.randint(1, 7) for _ in range(10)]


# ----- Approach 1: LLM majority ------------------------------------------------

def _llm_category(reapp_mean: float, supp_mean: float, reps: int, model, url, key) -> str | None:
    """Majority DEEPEN/INTRODUCE over `reps` LLM calls for one profile. None on failure."""
    try:
        from openai import OpenAI
    except ImportError:
        print("openai not installed; cannot run Approach 1 (--llm).", file=sys.stderr)
        return None
    client = OpenAI(api_key=key or "unused", base_url=url)
    system = (
        "You design a cognitive-reappraisal coaching session. Based on the participant's emotion-"
        "regulation questionnaire, decide whether the session should DEEPEN their existing "
        "reappraisal habit or INTRODUCE reappraisal as a new skill. Answer with exactly one word: "
        "DEEPEN or INTRODUCE."
    )
    user = (
        f"On the Emotion Regulation Questionnaire (1-7 scale), this participant's cognitive "
        f"reappraisal subscale mean is {reapp_mean:.2f} and their expressive suppression subscale "
        f"mean is {supp_mean:.2f}. Which framing fits better?"
    )
    votes = Counter()
    for _ in range(reps):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=1.0,
            )
            text = (resp.choices[0].message.content or "").lower()
        except Exception as e:  # noqa: BLE001
            print(f"LLM call failed: {e}", file=sys.stderr)
            return None
        if "deepen" in text and "introduce" not in text:
            votes[DEEPEN] += 1
        elif "introduce" in text and "deepen" not in text:
            votes[INTRODUCE] += 1
    if not votes:
        return None
    return votes.most_common(1)[0][0]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=200, help="number of sampled profiles")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--llm", action="store_true", help="also run Approach 1 (LLM majority)")
    ap.add_argument("--reps", type=int, default=10, help="LLM calls per profile (Approach 1)")
    args = ap.parse_args()

    model = os.environ.get("OPENAI_MODEL", "gpt-oss:120b")
    url = os.environ.get("OPENAI_URL")
    key = os.environ.get("OPENAI_KEY")

    det_counts = Counter()
    agree = disagree = compared = 0
    disagreements = []

    for vals in sample_profiles(args.n, args.seed):
        reapp, supp = subscale_means(vals)
        det_cat, z_r, z_s = framing_category(vals)
        det_counts[det_cat] += 1

        if args.llm:
            llm_cat = _llm_category(reapp, supp, args.reps, model, url, key)
            if llm_cat is None:
                print("Aborting Approach 1 (endpoint unavailable).", file=sys.stderr)
                args.llm = False
            else:
                compared += 1
                if llm_cat == det_cat:
                    agree += 1
                else:
                    disagree += 1
                    disagreements.append((reapp, supp, z_r, z_s, det_cat, llm_cat))

    print(f"\nDeterministic rule (Approach 2) over {args.n} profiles:")
    print(f"  DEEPEN   : {det_counts[DEEPEN]}")
    print(f"  INTRODUCE: {det_counts[INTRODUCE]}")

    if compared:
        rate = 100.0 * agree / compared
        print(f"\nAgreement with LLM majority (Approach 1) over {compared} profiles: {rate:.1f}%")
        print(f"  agree={agree}  disagree={disagree}")
        if disagreements:
            print("\n  Disagreements (reapp, supp, z_reapp, z_supp, deterministic -> llm):")
            for reapp, supp, z_r, z_s, det_cat, llm_cat in disagreements[:20]:
                print(f"    {reapp:.2f}  {supp:.2f}  {z_r:+.2f}  {z_s:+.2f}   {det_cat} -> {llm_cat}")
    else:
        print("\n(Approach 1 not run; pass --llm with OPENAI_URL/MODEL/KEY set to compare.)")


if __name__ == "__main__":
    main()
