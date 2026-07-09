#!/usr/bin/env python3
"""Profile a dataset (CSV/Excel) into a JSON summary for the insights agent.

Usage:
    python3 tools/profile_data.py data/superstore.csv [--sheet Orders] [--out runs/x/profile.json]
"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd


def load(path: Path, sheet: str | None) -> pd.DataFrame:
    if path.suffix.lower() in (".xls", ".xlsx"):
        return pd.read_excel(path, sheet_name=sheet or 0)
    return pd.read_csv(path)


def profile_column(s: pd.Series) -> dict:
    info: dict = {
        "dtype": str(s.dtype),
        "nonNull": int(s.notna().sum()),
        "nulls": int(s.isna().sum()),
        "unique": int(s.nunique()),
    }
    if pd.api.types.is_numeric_dtype(s):
        info["tableauType"] = "integer" if pd.api.types.is_integer_dtype(s) else "real"
        info.update(
            min=float(s.min()), max=float(s.max()),
            mean=round(float(s.mean()), 4), sum=round(float(s.sum()), 4),
        )
    elif pd.api.types.is_datetime64_any_dtype(s):
        info["tableauType"] = "date"
        info.update(min=str(s.min()), max=str(s.max()))
    else:
        # try dates
        parsed = pd.to_datetime(s, errors="coerce", format="mixed")
        if parsed.notna().mean() > 0.95:
            info["tableauType"] = "date"
            info.update(min=str(parsed.min()), max=str(parsed.max()))
        else:
            info["tableauType"] = "string"
            top = s.value_counts().head(8)
            info["topValues"] = {str(k): int(v) for k, v in top.items()}
    return info


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("file", type=Path)
    ap.add_argument("--sheet", default=None)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    df = load(args.file, args.sheet)
    prof = {
        "file": str(args.file),
        "rows": len(df),
        "columns": {c: profile_column(df[c]) for c in df.columns},
    }
    text = json.dumps(prof, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
        print(f"profile -> {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    sys.exit(main())
