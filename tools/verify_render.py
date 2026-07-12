#!/usr/bin/env python3
"""Deterministic render gate — runs after publish, before the design-linter.

The design-linter reads a screenshot and scores it with an LLM. That is only
meaningful if a real dashboard actually rendered. This check is the coded
guard in front of it: it fails fast, with no LLM, when a render is missing,
blank, truncated, or a solid wall of one color (the classic "worksheet errored
so Tableau drew nothing" case — which happened on this project's own GPU
scatter before it was fixed).

Checks per PNG:
  R1  file exists and is a decode-able image
  R2  dimensions are sane (>= min_w x min_h; not a 1px sliver)
  R3  not blank: luminance standard deviation over a downsampled grid must
      clear --min-std (a solid fill has std ~0)
  R4  not near-empty: the fraction of pixels differing from the modal
      background must clear --min-ink (catches "title + axes but no marks")

Usage:
  python3 tools/verify_render.py runs/<run>/renders            # all PNGs in dir
  python3 tools/verify_render.py runs/<run>/renders/Dash.png   # one file
  python3 tools/verify_render.py runs/<run>/renders --expect 1 # require >=1 PNG

Exit 0 = every render passed; 1 = a render failed or none were found (so the
orchestrator can refuse to run the design-linter on an empty renders/ dir).
"""

import argparse
import sys
from pathlib import Path

from PIL import Image


def check_image(path: Path, min_w: int, min_h: int, min_std: float, min_ink: float) -> dict:
    fails = []
    try:
        img = Image.open(path).convert("L")  # luminance
    except Exception as e:  # noqa: BLE001
        return {"file": path.name, "ok": False, "fails": [f"R1 not a decodable image: {e}"]}

    w, h = img.size
    if w < min_w or h < min_h:
        fails.append(f"R2 dimensions {w}x{h} below minimum {min_w}x{min_h}")

    # downsample to a 96x96 grid for a cheap, stable statistic
    small = img.resize((96, 96))
    px = list(small.getdata())
    n = len(px)
    mean = sum(px) / n
    std = (sum((p - mean) ** 2 for p in px) / n) ** 0.5
    if std < min_std:
        fails.append(f"R3 blank/solid fill (luminance std {std:.1f} < {min_std})")

    # modal background = most common luminance bucket; ink = share differing from it
    buckets = {}
    for p in px:
        b = p // 8
        buckets[b] = buckets.get(b, 0) + 1
    modal = max(buckets, key=buckets.get)
    ink = sum(c for b, c in buckets.items() if abs(b - modal) > 1) / n
    if ink < min_ink:
        fails.append(f"R4 near-empty (only {ink*100:.1f}% ink vs background < {min_ink*100:.0f}%)")

    return {"file": path.name, "ok": not fails, "w": w, "h": h,
            "lum_std": round(std, 1), "ink_frac": round(ink, 3), "fails": fails}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", type=Path, help="a PNG or a directory of PNGs")
    ap.add_argument("--min-w", type=int, default=600)
    ap.add_argument("--min-h", type=int, default=400)
    ap.add_argument("--min-std", type=float, default=4.0)
    ap.add_argument("--min-ink", type=float, default=0.02)
    ap.add_argument("--expect", type=int, default=1, help="minimum PNG count required")
    args = ap.parse_args()

    if args.path.is_dir():
        pngs = sorted(args.path.glob("*.png"))
    elif args.path.exists():
        pngs = [args.path]
    else:
        print(f"FAIL: path not found: {args.path}")
        return 1

    if len(pngs) < args.expect:
        print(f"FAIL: found {len(pngs)} render(s), expected >= {args.expect} "
              f"(publish/export likely produced nothing)")
        return 1

    results = [check_image(p, args.min_w, args.min_h, args.min_std, args.min_ink) for p in pngs]
    bad = [r for r in results if not r["ok"]]
    for r in results:
        status = "OK  " if r["ok"] else "FAIL"
        detail = "" if r["ok"] else "  ::  " + "; ".join(r["fails"])
        dims = f"{r.get('w','?')}x{r.get('h','?')} std={r.get('lum_std','?')} ink={r.get('ink_frac','?')}"
        print(f"  {status} {r['file']}  ({dims}){detail}")
    if bad:
        print(f"RENDER GATE FAIL: {len(bad)}/{len(results)} render(s) unusable")
        return 1
    print(f"RENDER GATE OK: {len(results)} render(s) verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
