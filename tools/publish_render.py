#!/usr/bin/env python3
"""Publish a .twbx to Tableau Cloud and export rendered PNGs of its views.

Closes the render loop without Tableau Desktop: the design-linter reads the
exported PNGs from runs/<run>/renders/.

Credentials come from the repo-root .env (gitignored) or real
environment variables:
    TABLEAU_SERVER_URL   e.g. https://10ax.online.tableau.com
    TABLEAU_SITE_ID      the site content URL (the bit after /site/ in the browser)
    TABLEAU_PAT_NAME     personal access token name
    TABLEAU_PAT_SECRET   personal access token secret

Usage:
    python3 tools/publish_render.py output/<run>.twbx --renders runs/<run>/renders
    python3 tools/publish_render.py output/<run>.twbx --project default --dashboard-only
"""

import argparse
import os
import re
import sys
import zipfile
from pathlib import Path

import tableauserverclient as tsc

ROOT = Path(__file__).resolve().parent.parent


def cloudify(twbx: Path) -> Path:
    """Rewrite textscan directory attrs to package-relative 'Data'.

    Tableau Cloud's publish check resolves file connections inside the
    package; absolute local paths fail with 'directory is missing or has
    been moved' (verified live). Desktop-facing twbx keeps the absolute
    path; this produces a -cloud sibling for publishing.
    """
    out = twbx.with_name(twbx.stem + "-cloud.twbx") if not twbx.stem.endswith("-cloud") else twbx
    if out == twbx:
        return twbx
    with zipfile.ZipFile(twbx) as zin, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.namelist():
            data = zin.read(item)
            if item.endswith(".twb"):
                text = re.sub(
                    r"(<connection class='textscan'[^>]*directory=')[^']*(')",
                    r"\1Data\2",
                    data.decode("utf-8"),
                )
                data = text.encode("utf-8")
            zout.writestr(item, data)
    return out


def load_env() -> dict:
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())
    keys = ["TABLEAU_SERVER_URL", "TABLEAU_SITE_ID", "TABLEAU_PAT_NAME", "TABLEAU_PAT_SECRET"]
    missing = [k for k in keys if not os.environ.get(k)]
    if missing:
        sys.exit(f"missing credentials: {', '.join(missing)} (set in {env_file} or env)")
    return {k: os.environ[k] for k in keys}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("twbx", type=Path)
    ap.add_argument("--project", default="default", help="Tableau project name")
    ap.add_argument("--renders", type=Path, default=None,
                    help="output dir for PNGs (default runs/<twbx-stem>/renders)")
    ap.add_argument("--dashboard-only", action="store_true",
                    help="export only dashboard views (falls back to name match via --view)")
    ap.add_argument("--view", default=None,
                    help="export only the view with this exact name (the REST API often "
                         "omits sheet_type, so name matching is the reliable filter)")
    args = ap.parse_args()

    creds = load_env()
    run_stem = args.twbx.stem.removesuffix("-cloud")
    renders = args.renders or (ROOT / "runs" / run_stem / "renders")
    renders.mkdir(parents=True, exist_ok=True)
    publish_twbx = cloudify(args.twbx)
    if publish_twbx != args.twbx:
        print(f"cloudified -> {publish_twbx.name} (package-relative data paths)")

    auth = tsc.PersonalAccessTokenAuth(
        creds["TABLEAU_PAT_NAME"], creds["TABLEAU_PAT_SECRET"], creds["TABLEAU_SITE_ID"]
    )
    server = tsc.Server(creds["TABLEAU_SERVER_URL"], use_server_version=True)

    with server.auth.sign_in(auth):
        projects = list(tsc.Pager(server.projects))
        project = next(
            (p for p in projects if p.name.lower() == args.project.lower()), None
        )
        if project is None:
            sys.exit(f"project '{args.project}' not found; have: {[p.name for p in projects]}")

        wb_item = tsc.WorkbookItem(project_id=project.id, show_tabs=True)
        wb = server.workbooks.publish(
            wb_item, str(publish_twbx), tsc.Server.PublishMode.Overwrite
        )
        print(f"published: {wb.name} (id {wb.id}) -> project '{project.name}'")

        server.workbooks.populate_views(wb)
        opts = tsc.ImageRequestOptions(
            imageresolution=tsc.ImageRequestOptions.Resolution.High, maxage=1
        )
        exported = []
        for view in wb.views:
            if args.view and view.name != args.view:
                continue
            if args.dashboard_only and view.sheet_type not in (None, "None", "dashboard"):
                continue
            server.views.populate_image(view, opts)
            safe = re.sub(r"[^A-Za-z0-9_-]+", "_", view.name)[:60]
            out = renders / f"{safe}.png"
            out.write_bytes(view.image)
            exported.append(out)
            print(f"exported: {view.name} ({view.sheet_type}) -> {out}")

        if not exported:
            print("no views exported (check --dashboard-only / workbook contents)")
            return 1
    print(f"\n{len(exported)} render(s) in {renders} — ready for design-linter")
    return 0


if __name__ == "__main__":
    sys.exit(main())
