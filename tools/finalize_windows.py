#!/usr/bin/env python3
"""Rewrite a .twb's <windows> block in the canonical form Tableau requires.

Tableau Desktop's dashboard loader asserts HasVisualDoc() for every
worksheet zone: the dashboard <window> must contain one <viewpoint> per
worksheet used, and every worksheet needs its own <window class='worksheet'>
with a standard <cards> block. Hand-authored workbooks that omit these load
with Internal Error 2805CF18 (verified live, Desktop 2026.1).

Usage:
    python3 tools/finalize_windows.py output/dashboard.twb
"""

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

CARDS = """      <cards>
        <edge name='left'>
          <strip size='160'>
            <card type='pages' />
            <card type='filters' />
            <card type='marks' />
          </strip>
        </edge>
        <edge name='top'>
          <strip size='2147483647'>
            <card type='columns' />
          </strip>
          <strip size='2147483647'>
            <card type='rows' />
          </strip>
          <strip size='31'>
            <card type='title' />
          </strip>
        </edge>
      </cards>"""


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace("'", "&apos;")


def main(path_str: str) -> int:
    path = Path(path_str)
    text = path.read_text()
    root = ET.fromstring(text)

    ws_names = [ws.get("name") for ws in root.findall(".//worksheets/worksheet")]
    # map sheets get locked viewpoints: no pan/zoom, no search, no toolbar,
    # no layer control (grammar mined from VOTD winner 09032025)
    map_sheets = {
        ws.get("name") for ws in root.findall(".//worksheets/worksheet")
        if ws.find(".//mapsources/mapsource") is not None
    }
    dashboards = []
    for db in root.findall(".//dashboards/dashboard"):
        zones = [
            z.get("name")
            for z in db.iter("zone")
            if z.get("name") and not z.get("type-v2")
        ]
        dashboards.append((db.get("name"), zones))

    # NB: no <simple-id> anywhere — it is only declared when the workbook
    # carries <WindowsPersistSimpleIdentifiers /> in the format-change
    # manifest, which we intentionally omit. Worksheet windows take the
    # (cards, viewpoint?) branch; dashboard windows take
    # (viewpoints, active, device-preview).
    lines = ["  <windows source-height='30'>"]
    for ws in ws_names:
        lines.append(f"    <window class='worksheet' name='{esc(ws)}'>")
        lines.append(CARDS)
        lines.append("    </window>")
    for i, (db, zones) in enumerate(dashboards):
        maximized = " maximized='true'" if i == len(dashboards) - 1 else ""
        lines.append(f"    <window class='dashboard'{maximized} name='{esc(db)}'>")
        lines.append("      <viewpoints>")
        for z in sorted(set(zones)):
            lines.append(f"        <viewpoint name='{esc(z)}'>")
            lines.append("          <zoom type='entire-view' />")
            if z in map_sheets:
                lines.append("          <floating-toolbar-visibility value='2' />")
                lines.append("          <geo-search-visibility value='1' />")
                lines.append("          <map-navigation value='1' />")
                lines.append("          <layer-control toolbar-button-enabled='false' />")
            lines.append("        </viewpoint>")
        lines.append("      </viewpoints>")
        lines.append("      <active id='-1' />")
        lines.append("      <device-preview selected='Desktop' />")
        lines.append("    </window>")
    lines.append("  </windows>")
    block = "\n".join(lines)

    new_text, n = re.subn(r"  <windows.*</windows>", block, text, flags=re.S)
    if n == 0:  # no existing block: insert before </workbook>
        new_text = text.replace("</workbook>", block + "\n</workbook>")
    path.write_text(new_text)
    print(f"windows block rebuilt: {len(ws_names)} worksheet windows, "
          f"{len(dashboards)} dashboard window(s) -> {path.name}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
