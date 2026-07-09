#!/usr/bin/env python3
"""Structural linter for hand-authored Tableau .twb XML.

Checks (E = error, W = warning):
  E1  XML well-formed, <workbook> root with version attribute
  E2  every datasource has a connection; textscan files exist on disk
  E3  every field used on rows/cols/encodings/sort/filter of a worksheet is
      declared in that worksheet's <datasource-dependencies>
  E4  every column-instance's base column is also declared
  E5  dashboard worksheet zones reference existing worksheets
  E6  zone geometry: 0 <= x,y and x+w, y+h <= 100000; unique zone ids
  E7  <windows> references an existing dashboard/worksheet
  W1  raw columns in dependencies missing from the datasource relation
      columns AND not defined as datasource <column> (calc fields)

Exit code 0 = clean (warnings allowed), 1 = errors.

Usage: python3 tools/validate_twb.py output/dashboard.twb
"""

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

FIELD_REF = re.compile(r"\[([^\]]+)\]\.\[([^\]]+)\]")


def strip_ns(name: str) -> str:
    return name.split("}")[-1]


def main(path_str: str) -> int:
    path = Path(path_str)
    errors: list[str] = []
    warns: list[str] = []

    try:
        tree = ET.parse(path)
    except ET.ParseError as e:
        print(f"E1 XML parse error: {e}")
        return 1
    root = tree.getroot()
    if strip_ns(root.tag) != "workbook":
        errors.append("E1 root element is not <workbook>")
    if not root.get("version"):
        errors.append("E1 <workbook> missing version attribute")
    if not root.get("source-build"):
        errors.append("E1 <workbook> missing source-build attribute (Tableau refuses to load without it)")

    # --- datasources ---
    ds_columns: dict[str, set[str]] = {}
    ds_names: set[str] = set()
    for ds in root.findall(".//datasources/datasource"):
        name = ds.get("name", "")
        # skip worksheet-level datasource stubs (no children)
        if ds.find("connection") is None and not list(ds):
            continue
        ds_names.add(name)
        cols: set[str] = set()
        conn = ds.find("connection")
        if conn is None:
            if name != "Parameters":  # the Parameters datasource has none by design
                errors.append(f"E2 datasource '{name}' has no <connection>")
        else:
            for c in conn.findall(".//relation//column"):
                cols.add(c.get("name", ""))
            for nc in conn.findall(".//named-connection/connection"):
                if nc.get("class") == "textscan":
                    d = Path(nc.get("directory", ""))
                    f = nc.get("filename", "")
                    if f and not (d / f).exists():
                        errors.append(f"E2 textscan file not found: {d / f}")
        for c in ds.findall("column"):
            cols.add(c.get("name", "").strip("[]"))
        # auto-generated geo fields
        cols.update({"Latitude (generated)", "Longitude (generated)"})
        ds_columns[name] = cols

    # --- worksheets ---
    ws_names: set[str] = set()
    for ws in root.findall(".//worksheets/worksheet"):
        wname = ws.get("name", "?")
        ws_names.add(wname)
        view = ws.find(".//table/view")
        if view is None:
            errors.append(f"E3 worksheet '{wname}' missing <table><view>")
            continue

        declared_instances: set[tuple[str, str]] = set()
        declared_raw: set[tuple[str, str]] = set()
        for dep in view.findall("datasource-dependencies"):
            dsn = dep.get("datasource", "")
            for ci in dep.findall("column-instance"):
                declared_instances.add((dsn, ci.get("name", "").strip("[]")))
            for c in dep.findall("column"):
                declared_raw.add((dsn, c.get("name", "").strip("[]")))
                if dsn in ds_columns and c.get("name", "").strip("[]") not in ds_columns[dsn]:
                    warns.append(
                        f"W1 '{wname}': column {c.get('name')} not in datasource '{dsn}' relation/columns"
                    )

        # E4: column-instance base columns declared
        for dep in view.findall("datasource-dependencies"):
            dsn = dep.get("datasource", "")
            for ci in dep.findall("column-instance"):
                if ci.get("name", "").strip("[]").startswith("io:"):
                    continue  # set instances derive from <group>, not columns
                base = ci.get("column", "").strip("[]")
                if (dsn, base) not in declared_raw:
                    errors.append(
                        f"E4 '{wname}': column-instance {ci.get('name')} base [{base}] not declared"
                    )

        # collect used refs from shelves, encodings, sorts (hard errors);
        # filters get warnings only (action-generated fields are legit there)
        used: set[tuple[str, str]] = set()
        table = ws.find("table")
        for tag in ("rows", "cols"):
            el = table.find(tag)
            if el is not None and el.text:
                used.update(FIELD_REF.findall(el.text))
        for enc in table.findall(".//panes/pane/encodings/*"):
            col = enc.get("column", "")
            used.update(FIELD_REF.findall(col))
        for s in view.findall("sort"):
            for attr in ("column", "using"):
                used.update(FIELD_REF.findall(s.get(attr, "")))
        used_in_filters: set[tuple[str, str]] = set()
        for f in view.findall("filter"):
            used_in_filters.update(FIELD_REF.findall(f.get("column", "")))

        def is_internal(inst: str) -> bool:
            # ':Measure Names' etc., action-generated filter fields,
            # implicit geo fields
            return (
                inst.startswith(":")
                or inst.startswith("Action (")
                or inst.startswith("io:")  # set in/out instances
                or "(generated)" in inst
                or inst == "Multiple Values"
            )

        for dsn, inst in used:
            if is_internal(inst):
                continue
            if (dsn, inst) in declared_instances or (dsn, inst) in declared_raw:
                continue
            errors.append(f"E3 '{wname}': field [{dsn}].[{inst}] used but not declared in dependencies")
        for dsn, inst in used_in_filters - used:
            if is_internal(inst):
                continue
            if (dsn, inst) in declared_instances or (dsn, inst) in declared_raw:
                continue
            warns.append(f"W2 '{wname}': filter field [{dsn}].[{inst}] not declared in dependencies")

    # --- dashboards ---
    db_names: set[str] = set()
    for db in root.findall(".//dashboards/dashboard"):
        dname = db.get("name", "?")
        db_names.add(dname)
        # ignore zones inside device layouts — they legitimately reuse ids
        device_zones = {id(z) for dl in db.findall(".//devicelayouts") for z in dl.findall(".//zone")}
        seen_ids: set[str] = set()
        for zone in db.findall(".//zone"):
            if id(zone) in device_zones:
                continue
            zid = zone.get("id", "")
            if zid in seen_ids:
                errors.append(f"E6 dashboard '{dname}': duplicate zone id {zid}")
            seen_ids.add(zid)
            zname = zone.get("name")
            ztype = zone.get("type-v2", "")
            if zname and ztype in ("", None) and zname not in ws_names:
                errors.append(f"E5 dashboard '{dname}': zone names unknown worksheet '{zname}'")
            try:
                x, y = int(zone.get("x", 0)), int(zone.get("y", 0))
                w, h = int(zone.get("w", 0)), int(zone.get("h", 0))
            except ValueError:
                errors.append(f"E6 dashboard '{dname}': non-integer zone geometry (id {zid})")
                continue
            if x < 0 or y < 0 or x + w > 100000 or y + h > 100000:
                errors.append(
                    f"E6 dashboard '{dname}': zone id {zid} out of bounds (x={x} y={y} w={w} h={h})"
                )

    # --- windows ---
    for win in root.findall(".//windows/window"):
        wn = win.get("name", "")
        if wn and wn not in db_names | ws_names:
            errors.append(f"E7 window references unknown sheet/dashboard '{wn}'")
        if win.get("class") == "dashboard":
            if win.find("viewpoints") is None or win.find("active") is None:
                errors.append(
                    f"E7 dashboard window '{wn}' must contain <viewpoints> and "
                    "<active id='-1' /> children (Tableau content-model requirement)"
                )
                continue
            # loader asserts HasVisualDoc per worksheet zone: every worksheet
            # in the dashboard needs a viewpoint (run tools/finalize_windows.py)
            vps = {vp.get("name") for vp in win.findall("viewpoints/viewpoint")}
            for db in root.findall(".//dashboards/dashboard"):
                if db.get("name") != wn:
                    continue
                for z in db.iter("zone"):
                    zn = z.get("name")
                    if zn and not z.get("type-v2") and zn not in vps:
                        errors.append(
                            f"E7 dashboard window '{wn}' missing <viewpoint> for "
                            f"worksheet '{zn}' (causes Internal Error 2805CF18)"
                        )

    for w in warns:
        print(f"  {w}")
    for e in errors:
        print(f"  {e}")
    if errors:
        print(f"FAIL: {len(errors)} error(s), {len(warns)} warning(s) in {path.name}")
        return 1
    print(f"OK: {path.name} passed ({len(warns)} warning(s))")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
