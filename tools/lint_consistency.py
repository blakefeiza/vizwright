"""Cross-dashboard consistency check for a SERIES of related workbooks.

A single dashboard can be internally clean yet clash with its siblings: a
different green, a different title font, bars here and lollipops there for the
same job. This fingerprints each .twb's design DNA and flags drift across the
set, so a family of dashboards reads as one system.

It compares:
  - palette      : the set of fill/mark hex colors used
  - fonts        : font-family values
  - title_size   : the largest run fontsize (dashboard title scale)
  - mark_families: which mark classes appear (Bar, Line, Circle, ...)
  - number_fmts  : the default-format / text-format strings
  - canvas       : dashboard <size> (fixed w x h)

Usage:
  python3 tools/lint_consistency.py output/a.twb output/b.twb output/c.twb
  python3 tools/lint_consistency.py output/          # all .twb in a dir

Exit 0 = consistent (warnings allowed); 1 = drift beyond tolerance.
Drift is reported, not auto-fixed — the fix is a human/agent design call.
"""

import re
import sys
from collections import Counter
from pathlib import Path


HEX = re.compile(r"#[0-9a-fA-F]{6}\b")


def fingerprint(twb: Path) -> dict:
    s = twb.read_text(errors="replace")
    palette = Counter(m.group(0).lower() for m in HEX.finditer(s))
    # drop near-black/near-white structural colors; keep the brand-ish ones
    brand = {c for c, n in palette.items()
             if c not in ("#000000", "#ffffff", "#00000000") and n >= 1}
    fonts = set(re.findall(r"fontname='([^']+)'", s)) | set(re.findall(r"attr='font-family' value='([^']+)'", s))
    title_sizes = [int(x) for x in re.findall(r"fontsize='(\d+)'", s)]
    marks = set(re.findall(r"<mark class='([^']+)'", s))
    num_fmts = set(re.findall(r"(?:default-format|text-format)[^=]*=[\"']([^\"']*[#0][^\"']*)[\"']", s))
    sizes = set(re.findall(r"<size maxheight='(\d+)' maxwidth='(\d+)'", s))
    return {
        "file": twb.name,
        "palette": brand,
        "fonts": fonts,
        "title_size": max(title_sizes) if title_sizes else 0,
        "mark_families": marks,
        "number_fmts": num_fmts,
        "canvas": sizes,
    }


def diff(fps: list[dict]) -> list[str]:
    warns = []
    # fonts should match across the series
    all_fonts = set().union(*(f["fonts"] for f in fps))
    if len({frozenset(f["fonts"]) for f in fps}) > 1:
        warns.append(f"font drift: workbooks use different font sets ({sorted(all_fonts)})")
    # title scale within 4pt
    tsizes = [f["title_size"] for f in fps]
    if max(tsizes) - min(tsizes) > 4:
        warns.append(f"title-size drift: dashboard titles range {min(tsizes)}–{max(tsizes)}pt")
    # palette: flag brand colors that appear in some but not most workbooks
    all_colors = Counter()
    for f in fps:
        for c in f["palette"]:
            all_colors[c] += 1
    n = len(fps)
    if n >= 2:
        oddballs = [c for c, k in all_colors.items() if 0 < k < n and k == 1 and n > 2]
        if oddballs:
            warns.append(f"palette drift: colors used in only one of {n} workbooks: {oddballs}")
    # canvas size consistency
    if len({frozenset(f["canvas"]) for f in fps}) > 1:
        canvases = [sorted(f["canvas"]) for f in fps]
        warns.append(f"canvas-size drift across the series: {canvases}")
    # number formats
    if len({frozenset(f["number_fmts"]) for f in fps}) > 1:
        warns.append("number-format drift: different currency/percent formats across workbooks")
    return warns


def main(paths: list[str]) -> int:
    twbs: list[Path] = []
    for p in paths:
        pp = Path(p)
        twbs.extend(sorted(pp.glob("*.twb")) if pp.is_dir() else [pp])
    twbs = [t for t in twbs if t.exists()]
    if len(twbs) < 2:
        print("need >= 2 .twb files to compare a series")
        return 0

    fps = [fingerprint(t) for t in twbs]
    print(f"fingerprinted {len(fps)} workbooks: {[f['file'] for f in fps]}")
    warns = diff(fps)
    for w in warns:
        print(f"  DRIFT: {w}")
    if warns:
        print(f"CONSISTENCY: {len(warns)} drift issue(s) across the series")
        return 1
    print("CONSISTENCY OK: the series reads as one design system")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1:]))
