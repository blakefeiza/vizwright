#!/usr/bin/env python3
"""Package a .twb and its data files into a .twbx (zip archive).

Layout inside the archive (matches Tableau's own packaging):
    <name>.twb          at the root
    Data/<file>         each data file

Usage:
    python3 tools/package_twbx.py output/dashboard.twb data/superstore.csv [more data files...]
"""

import sys
import zipfile
from pathlib import Path


def main(twb_path: str, data_paths: list[str]) -> int:
    twb = Path(twb_path)
    if not twb.exists():
        print(f"not found: {twb}")
        return 1
    out = twb.with_suffix(".twbx")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(twb, twb.name)
        for dp in data_paths:
            p = Path(dp)
            if not p.exists():
                print(f"data file not found: {p}")
                return 1
            zf.write(p, f"Data/{p.name}")
    print(f"packaged -> {out} ({out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2:]))
