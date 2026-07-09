#!/usr/bin/env python3
"""Download business-type VOTD workbooks and extract twb XML chart patterns.

Reads knowledge/votd/votd_catalog.json, downloads .twbx files for business
dashboards (newest first), unpacks the .twb, detects the chart type of each
worksheet, and writes XML fragments into knowledge/xml-patterns/:

    <chart-type>/<workbook>__<sheet>.xml      one file per worksheet
    dashboards/<workbook>__<dashboard>.xml    dashboard zone layouts
    datasources/<workbook>__<name>.xml        connection blocks
    index.json                                inventory with detected types

Usage:
    python3 tools/extract_patterns.py --count 20
"""

import argparse
import io
import json
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

BASE = "https://public.tableau.com"
ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "knowledge" / "votd" / "votd_catalog.json"
PATTERNS = ROOT / "knowledge" / "xml-patterns"
TWBX_DIR = ROOT / "knowledge" / "votd" / "twbx"
MAX_TWBX_BYTES = 60 * 1024 * 1024


def download_twbx(workbook_repo_url: str) -> bytes | None:
    url = f"{BASE}/workbooks/{workbook_repo_url}.twb"
    req = urllib.request.Request(url, headers={"User-Agent": "votd-miner/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read(MAX_TWBX_BYTES + 1)
    except Exception as e:  # noqa: BLE001
        print(f"  download failed: {e}", file=sys.stderr)
        return None
    if len(data) > MAX_TWBX_BYTES:
        print("  skipped: file too large", file=sys.stderr)
        return None
    return data


def read_twb_from_twbx(data: bytes) -> str | None:
    if data[:2] == b"PK":  # packaged workbook (zip)
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                twb_names = [n for n in zf.namelist() if n.endswith(".twb")]
                if not twb_names:
                    return None
                return zf.read(twb_names[0]).decode("utf-8", errors="replace")
        except zipfile.BadZipFile:
            return None
    if data[:5] == b"<?xml" or b"<workbook" in data[:2000]:
        return data.decode("utf-8", errors="replace")
    return None


def shelf_fields(ws: ET.Element, shelf: str) -> str:
    el = ws.find(f".//table/{shelf}")
    return (el.text or "") if el is not None else ""


def is_continuous_measure(field_expr: str) -> bool:
    return bool(re.search(r"\[(sum|avg|min|max|cnt|ctd|usr|median|none)\b", field_expr, re.I))


def detect_chart_type(ws: ET.Element) -> str:
    mark_el = ws.find(".//panes/pane/mark")
    mark = mark_el.get("class", "Automatic") if mark_el is not None else "Automatic"
    rows = shelf_fields(ws, "rows")
    cols = shelf_fields(ws, "cols")

    ws_xml = ET.tostring(ws, encoding="unicode")
    if "Latitude (generated)" in ws_xml or "[Longitude (generated)]" in ws_xml:
        return "map"

    rows_meas = is_continuous_measure(rows)
    cols_meas = is_continuous_measure(cols)

    if mark == "Text":
        if not rows and not cols:
            return "ban-kpi"
        return "text-table"
    if mark == "Bar":
        return "bar"
    if mark == "Line":
        return "line"
    if mark == "Area":
        return "area"
    if mark == "Square":
        if rows and cols and not (rows_meas or cols_meas):
            return "heatmap"
        return "square-other"
    if mark in ("Circle", "Shape"):
        if rows_meas and cols_meas:
            return "scatter"
        return "dot-plot"
    if mark == "Pie":
        return "pie-donut"
    if mark == "GanttBar":
        return "gantt"
    if mark == "Polygon":
        return "polygon-custom"
    if mark == "Automatic":
        if rows_meas and cols_meas:
            return "scatter"
        if rows_meas or cols_meas:
            return "bar-or-line-auto"
        return "auto-other"
    return f"other-{mark.lower()}"


def safe_name(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", s)[:80]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=20, help="target successful downloads")
    ap.add_argument("--types", default="business", help="comma list of vizTypes to mine")
    args = ap.parse_args()

    catalog = json.loads(CATALOG.read_text())
    wanted = {t.strip() for t in args.types.split(",")}
    candidates = [e for e in catalog if e["vizType"] in wanted]

    TWBX_DIR.mkdir(parents=True, exist_ok=True)
    index: list[dict] = []
    ok = 0

    for entry in candidates:
        if ok >= args.count:
            break
        wb = entry["workbookRepoUrl"]
        print(f"[{ok}/{args.count}] {entry['title']} ({wb})")
        data = download_twbx(wb)
        if data is None:
            continue
        twb = read_twb_from_twbx(data)
        if twb is None:
            print("  skipped: no .twb found", file=sys.stderr)
            continue
        try:
            root = ET.fromstring(twb)
        except ET.ParseError as e:
            print(f"  skipped: XML parse error {e}", file=sys.stderr)
            continue

        (TWBX_DIR / f"{safe_name(wb)}.twb").write_text(twb)
        version = root.get("version", "?")
        build = root.get("source-build", "?")

        wb_record = {
            "workbook": wb,
            "title": entry["title"],
            "author": entry["author"],
            "twbVersion": version,
            "sourceBuild": build,
            "worksheets": [],
            "dashboards": [],
        }

        for ws in root.findall(".//worksheets/worksheet"):
            name = ws.get("name", "unnamed")
            ctype = detect_chart_type(ws)
            out_dir = PATTERNS / ctype
            out_dir.mkdir(parents=True, exist_ok=True)
            frag = ET.tostring(ws, encoding="unicode")
            out_path = out_dir / f"{safe_name(wb)}__{safe_name(name)}.xml"
            out_path.write_text(frag)
            wb_record["worksheets"].append(
                {"sheet": name, "chartType": ctype, "file": str(out_path.relative_to(ROOT)), "bytes": len(frag)}
            )

        dash_dir = PATTERNS / "dashboards"
        dash_dir.mkdir(parents=True, exist_ok=True)
        for db in root.findall(".//dashboards/dashboard"):
            name = db.get("name", "unnamed")
            frag = ET.tostring(db, encoding="unicode")
            out_path = dash_dir / f"{safe_name(wb)}__{safe_name(name)}.xml"
            out_path.write_text(frag)
            wb_record["dashboards"].append(
                {"dashboard": name, "file": str(out_path.relative_to(ROOT)), "bytes": len(frag)}
            )

        ds_dir = PATTERNS / "datasources"
        ds_dir.mkdir(parents=True, exist_ok=True)
        for ds in root.findall(".//datasources/datasource"):
            name = ds.get("name", ds.get("caption", "unnamed"))
            conn = ds.find("connection")
            if conn is None:
                continue
            frag = ET.tostring(conn, encoding="unicode")
            (ds_dir / f"{safe_name(wb)}__{safe_name(name)}.xml").write_text(frag)

        index.append(wb_record)
        ok += 1
        time.sleep(0.5)

    (PATTERNS / "index.json").write_text(json.dumps(index, indent=2))

    type_counts: dict[str, int] = {}
    for rec in index:
        for w in rec["worksheets"]:
            type_counts[w["chartType"]] = type_counts.get(w["chartType"], 0) + 1
    print(f"\nextracted from {ok} workbooks -> {PATTERNS}")
    print("chart type counts:", json.dumps(type_counts, indent=2))
    print("twb versions:", sorted({r['twbVersion'] for r in index}))


if __name__ == "__main__":
    main()
