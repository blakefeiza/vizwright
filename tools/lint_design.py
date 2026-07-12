#!/usr/bin/env python3
"""Static design lint for generated .twb XML — catches design/formatting
defects BEFORE any render exists, so render iterations are about insight,
not polish. Run after validate_twb.py; packaging is gated on both.

Checks per chart worksheet (non-empty rows/cols):
  D1  field labels hidden: style-rule worksheet has display-field-labels
      false for rows AND cols
  D2  every continuous (:qk) instance on rows/cols has an axis title
      format (usually cleared: value='')
  D3  gridlines killed via stroke-size 0 (rows + cols)
  D4  custom tooltip present (customized-tooltip in the pane)
  D5  bar sheets: explicit <text> encoding + a text-format for that field
      under style-rule element='cell' (labels bind via cell, not label)
Per BAN worksheet (Text mark, empty shelves):
  D6  text-format present (abbreviated number) + font-size style
Dashboard:
  D7  title/footer text zones carry a padding format (ERROR)
  D8  dashboard title subtitle must not duplicate BAN values (heuristic:
      warn if a $ amount appears in a text zone AND a BAN sheet exists)

Exit 0 = pass (warnings allowed), 1 = defects found.
Usage: python3 tools/lint_design.py output/<name>.twb
"""

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

FIELD_REF = re.compile(r"\[([^\]]+)\]\.\[([^\]]+)\]")


def shelf_text(ws, tag):
    el = ws.find(f".//table/{tag}")
    return (el.text or "") if el is not None else ""


def main(path_str: str) -> int:
    root = ET.parse(path_str).getroot()
    errors: list[str] = []
    warns: list[str] = []
    ban_sheets = []

    for ws in root.findall(".//worksheets/worksheet"):
        name = ws.get("name", "?")
        rows, cols = shelf_text(ws, "rows"), shelf_text(ws, "cols")
        style = ws.find(".//table/style")
        # normalize to single quotes: ET serializes attrs with double quotes
        style_xml = (ET.tostring(style, encoding="unicode") if style is not None else "").replace('"', "'")
        pane_xml = "".join(
            ET.tostring(p, encoding="unicode") for p in ws.findall(".//panes/pane")
        ).replace('"', "'")
        mark = ws.find(".//panes/pane/mark")
        mark_class = mark.get("class") if mark is not None else ""

        if not rows and not cols:  # BAN / KPI card
            if mark_class == "Text":
                ban_sheets.append(name)
                if "text-format" not in style_xml:
                    errors.append(f"D6 '{name}': BAN without text-format (raw number will render)")
                if "font-size" not in style_xml:
                    errors.append(f"D6 '{name}': BAN without font-size style (number won't be big)")
                if "text-align" not in style_xml:
                    errors.append(f"D6 '{name}': BAN without text-align (defaults to odd right-align)")
                if "customized-tooltip" not in pane_xml:
                    errors.append(
                        f"D9 '{name}': BAN default tooltip repeats the number — replace with "
                        "one line of additional context (or leave a static context run)"
                    )
            continue

        # chart worksheets
        if style_xml.count("display-field-labels") < 2:
            errors.append(f"D1 '{name}': field labels not hidden (need scope rows AND cols)")
        for shelf, text in (("rows", rows), ("cols", cols)):
            for dsn, inst in FIELD_REF.findall(text):
                if inst.endswith(":qk"):
                    pat = f"attr='title' class='0' field='[{dsn}].[{inst}]' scope='{shelf}'"
                    if pat not in style_xml:
                        errors.append(
                            f"D2 '{name}': no axis-title format for [{inst}] on {shelf} "
                            "(default axis title will show)"
                        )
        if style_xml.count("stroke-size") < 2:
            errors.append(f"D3 '{name}': gridlines not killed (stroke-size 0, rows+cols)")
        # D11: line elements must be explicit decisions, not defaults
        if "element='table-div'" not in style_xml:
            errors.append(f"D11 '{name}': row/col dividers not declared (default lines = clutter)")
        if "band-color" not in style_xml:
            errors.append(f"D11 '{name}': banding not declared (set #00000000 unless intentional)")
        if "element='zeroline'" not in style_xml:
            errors.append(f"D11 '{name}': zero line not declared (off unless negatives exist; subtle if kept)")
        if (rows or cols) and (
            "element='axis'" not in style_xml
            or "stroke-" not in style_xml.split("element='axis'")[1].split("</style-rule>")[0]
        ):
            errors.append(f"D11 '{name}': axis ruler not declared (0 for bars; subtle time ruler for lines)")
        if "customized-tooltip" not in pane_xml:
            errors.append(f"D4 '{name}': default tooltip (add customized-tooltip)")
        if mark_class == "Bar":
            text_encs = ws.findall(".//panes/pane/encodings/text")
            has_cat_color = any(
                ":nk]" in (c.get("column", "")) or ":ok]" in (c.get("column", ""))
                for c in ws.findall(".//panes/pane/encodings/color"))
            if not text_encs and not has_cat_color:
                # stacked/grouped bars (categorical color) may omit end labels
                errors.append(f"D5 '{name}': bar labels need explicit <text> encoding")
            else:
                for te in text_encs:
                    refs = FIELD_REF.findall(te.get("column", ""))
                    for dsn, inst in refs:
                        cell_rules = re.findall(
                            r"<style-rule element='cell'>(?:(?!</style-rule>).)*?"
                            + re.escape(f"[{inst}]") + r"(?:(?!</style-rule>).)*?</style-rule>",
                            style_xml, re.S)
                        if not any("text-format" in c for c in cell_rules):
                            errors.append(
                                f"D5 '{name}': no cell text-format for label field [{inst}] "
                                "(label will use default format; element='label' does NOT bind)"
                            )

    # dashboards
    has_dollar_text = False
    for db in root.findall(".//dashboards/dashboard"):
        # D12: vertical gutters must sit on one column grid across rows —
        # near-but-unequal boundaries break the gutter line (visual alignment)
        row_bounds = []
        for row in db.iter("zone"):
            if row.get("param") != "horz":
                continue
            bounds = set()
            for child in row.findall("zone"):
                if child.get("name") and not child.get("type-v2"):
                    x = int(child.get("x", 0))
                    if x > 0:
                        bounds.add(x)
            if bounds:
                row_bounds.append(bounds)
        for i in range(len(row_bounds)):
            for j in range(i + 1, len(row_bounds)):
                a, b = sorted(row_bounds[i]), sorted(row_bounds[j])
                # rows with the same column count must share the exact grid;
                # different counts (e.g. 4-BAN band over 2-col rows) are a
                # deliberate rhythm change and exempt
                if len(a) == len(b) and a != b:
                    errors.append(
                        f"D12 dashboard '{db.get('name')}': rows with equal column counts "
                        f"use different gutters ({a} vs {b}) — snap to one column grid "
                        "(prefer golden ratio 61800/38200 for 2-col rows)"
                    )
        for zone in db.iter("zone"):
            zname = zone.get("name")
            if zname and not zone.get("type-v2"):  # worksheet zone
                zxml = ET.tostring(zone, encoding="unicode").replace('"', "'")
                if "attr='padding'" not in zxml:
                    errors.append(
                        f"D10 dashboard '{db.get('name')}': worksheet zone '{zname}' "
                        "has no padding (charts need room to breathe — use 16)"
                    )
            if zone.get("type-v2") != "text":
                continue
            zs = ET.tostring(zone, encoding="unicode").replace('"', "'")
            if "attr='padding'" not in zs:
                # promoted to error: padding is a hard rule for worksheet zones
                # (D10) and the design-standards rubric scores it — text zones
                # were the inconsistent exception. Now enforced everywhere.
                errors.append(f"D7 dashboard '{db.get('name')}': text zone id {zone.get('id')} has no padding (use 8-16)")
            body = "".join(r.text or "" for r in zone.iter("run"))
            if re.search(r"\$[\d,.]+[KMB]?", body):
                has_dollar_text = True
    # D8 stays a WARNING by design: a $ in title/footer text is USUALLY a BAN
    # duplication, but narrative subtitles legitimately quote prices that are
    # not BANs ("a $1,000 gaming card returns 31x more than a $30,000 H100").
    # A hard error here would block correct storytelling, so it advises only.
    if has_dollar_text and ban_sheets:
        warns.append("D8 (advisory) title/footer text contains $ values while BANs exist — "
                     "confirm these are narrative prices, not duplicated BAN numbers")

    for w in warns:
        print(f"  {w}")
    for e in errors:
        print(f"  {e}")
    if errors:
        print(f"DESIGN FAIL: {len(errors)} defect(s), {len(warns)} warning(s)")
        return 1
    print(f"DESIGN OK ({len(warns)} warning(s))")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
