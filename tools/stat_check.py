#!/usr/bin/env python3
"""Coded statistical-significance testing for the insights-analyst stage.

The analyst should CITE these results in insights.md instead of eyeballing a
difference and calling it "significant." Every group comparison it makes in
prose should have a corresponding entry here.

Two modes:

  # Compare a numeric measure across the levels of a categorical dimension.
  # Runs every pairwise Welch's t-test, Bonferroni-corrects across the family,
  # and reports Cohen's d effect sizes.
  python3 tools/stat_check.py data.csv --value Profit --group Region

  # Test one proportion/rate difference (two-proportion z-test), e.g.
  # "is 45/333 Cat-5 rate different from 288/1962 lower rate?"
  python3 tools/stat_check.py --prop 45 333 288 1962

Output: JSON to stdout (or --out path). Verdicts use alpha=0.05 AFTER
Bonferroni correction, so the analyst can quote "significant (Bonferroni-
corrected p=…)" honestly.

Guidance the analyst must follow:
- A claim like "West is more profitable than Central" needs sig == true here.
- If sig == false, downgrade the prose: "West's profit is higher but the
  per-order difference is not statistically distinguishable (p=…)."
- Report the effect size too: a tiny-but-significant gap (huge n) is not a
  headline; cohens_d < 0.2 is negligible even when p < 0.05.
"""

import argparse
import json
import sys
from itertools import combinations

import numpy as np
import pandas as pd
from scipy import stats


def cohens_d(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return float("nan")
    va, vb = a.var(ddof=1), b.var(ddof=1)
    pooled = np.sqrt(((na - 1) * va + (nb - 1) * vb) / (na + nb - 2))
    if pooled == 0:
        return 0.0
    return float((a.mean() - b.mean()) / pooled)


def effect_label(d: float) -> str:
    ad = abs(d)
    if np.isnan(ad):
        return "undetermined"
    if ad < 0.2:
        return "negligible"
    if ad < 0.5:
        return "small"
    if ad < 0.8:
        return "medium"
    return "large"


def compare_groups(df: pd.DataFrame, value: str, group: str, alpha: float) -> dict:
    groups = {}
    for name, sub in df.groupby(group)[value]:
        vals = pd.to_numeric(sub, errors="coerce").dropna().to_numpy()
        if len(vals) >= 2:
            groups[str(name)] = vals
    names = sorted(groups, key=lambda n: -groups[n].mean())
    pairs = list(combinations(names, 2))
    m = len(pairs)  # family size for Bonferroni

    comparisons = []
    for a, b in pairs:
        va, vb = groups[a], groups[b]
        t, p = stats.ttest_ind(va, vb, equal_var=False)  # Welch's
        p_adj = min(p * m, 1.0)
        d = cohens_d(va, vb)
        comparisons.append({
            "a": a, "b": b,
            "mean_a": round(float(va.mean()), 4), "mean_b": round(float(vb.mean()), 4),
            "n_a": len(va), "n_b": len(vb),
            "t": round(float(t), 4),
            "p_raw": round(float(p), 6),
            "p_bonferroni": round(float(p_adj), 6),
            "cohens_d": round(d, 3) if not np.isnan(d) else None,
            "effect": effect_label(d),
            "significant": bool(p_adj < alpha),
        })
    return {
        "test": "Welch t-test, pairwise, Bonferroni-corrected",
        "value": value, "group": group, "alpha": alpha,
        "family_size": m,
        "group_means": {n: round(float(groups[n].mean()), 4) for n in names},
        "group_ns": {n: len(groups[n]) for n in names},
        "comparisons": comparisons,
        "any_significant": any(c["significant"] for c in comparisons),
    }


def two_proportion(x1: int, n1: int, x2: int, n2: int, alpha: float) -> dict:
    p1, p2 = x1 / n1, x2 / n2
    p_pool = (x1 + x2) / (n1 + n2)
    se = np.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    z = (p1 - p2) / se if se > 0 else 0.0
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    return {
        "test": "two-proportion z-test",
        "alpha": alpha,
        "rate_a": round(p1, 4), "rate_b": round(p2, 4),
        "count_a": [x1, n1], "count_b": [x2, n2],
        "z": round(float(z), 4),
        "p": round(float(p), 6),
        "significant": bool(p < alpha),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?", help="CSV for group comparison")
    ap.add_argument("--value", help="numeric measure column")
    ap.add_argument("--group", help="categorical grouping column")
    ap.add_argument("--prop", nargs=4, type=int, metavar=("X1", "N1", "X2", "N2"),
                    help="two-proportion z-test: successes/total for A and B")
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--out", help="write JSON here instead of stdout")
    args = ap.parse_args()

    if args.prop:
        result = two_proportion(*args.prop, args.alpha)
    elif args.file and args.value and args.group:
        df = pd.read_csv(args.file)
        for col in (args.value, args.group):
            if col not in df.columns:
                sys.exit(f"column '{col}' not in {args.file}; have: {list(df.columns)}")
        result = compare_groups(df, args.value, args.group, args.alpha)
    else:
        ap.print_help()
        return 2

    text = json.dumps(result, indent=2)
    if args.out:
        from pathlib import Path
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text)
        print(f"stat check -> {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
