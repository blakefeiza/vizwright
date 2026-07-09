#!/usr/bin/env python3
"""Mine Tableau Public Viz of the Day (VOTD) winners into a local catalog.

Fetches VOTD entries page-by-page from the public discover API, applies a
keyword-based first-pass classification (business / infographic / scientific /
data-art / sports-games / other), and writes knowledge/votd/votd_catalog.json.

Usage:
    python3 tools/mine_votd.py --max 300
"""

import argparse
import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

BASE = "https://public.tableau.com"
VOTD_PATH = "/public/apis/bff/discover/v2/vizzes/viz-of-the-day"
PAGE_LIMIT = 12  # API requires limit=12 exactly
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "knowledge" / "votd" / "votd_catalog.json"

TYPE_KEYWORDS = {
    "business": [
        "dashboard", "kpi", "sales", "revenue", "profit", "performance",
        "executive", "service desk", "sla", "tickets", "retention", "churn",
        "funnel", "conversion", "operations", "hr ", "attrition", "finance",
        "marketing", "customer", "supply chain", "inventory", "call center",
        "summary", "overview", "monitor", "backlog", "pipeline", "scorecard",
    ],
    "sports-games": [
        "nba", "nfl", "soccer", "football", "baseball", "olympic", "tennis",
        "f1", "premier league", "pokemon", "pokémon", "game", "gaming",
        "esports", "chess", "player", "trainer", "match",
    ],
    "scientific": [
        "climate", "earthquake", "hurricane", "species", "health", "disease",
        "covid", "vaccine", "genome", "astronomy", "space", "weather",
        "temperature", "emissions", "biodiversity", "epidemi", "sea turtle",
        "spatial", "projection", "census",
    ],
    "data-art": [
        "art", "generative", "kaleidoscope", "radial", "sankey diagram",
        "abstract", "creative", "music", "lyrics", "movie", "film",
        "typography", "illustration",
    ],
}


def classify(title: str, description: str) -> str:
    text = f"{title} {description}".lower()
    scores = {
        t: sum(1 for kw in kws if kw in text) for t, kws in TYPE_KEYWORDS.items()
    }
    best = max(scores, key=lambda t: scores[t])
    return best if scores[best] > 0 else "other"


def fetch_page(start_index: int) -> dict:
    # NB: the v2 API ignores `page`; pagination is via startIndex (response
    # returns `next` = the next startIndex, or null at the end).
    url = f"{BASE}{VOTD_PATH}?startIndex={start_index}&limit={PAGE_LIMIT}"
    req = urllib.request.Request(url, headers={"User-Agent": "votd-miner/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def strip_html(text: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", text or "")).strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=300, help="max entries to fetch")
    args = ap.parse_args()

    entries: list[dict] = []
    start = 0
    while len(entries) < args.max:
        try:
            data = fetch_page(start)
        except Exception as e:  # noqa: BLE001 - report and stop cleanly
            print(f"startIndex {start} failed: {e}", file=sys.stderr)
            break
        vizzes = data.get("contents") or []
        if not vizzes:
            break
        for v in vizzes:
            desc = strip_html(v.get("description", ""))
            entries.append(
                {
                    "title": strip_html(v.get("title", "")),
                    "author": v.get("authorDisplayName"),
                    "authorProfile": v.get("authorProfileName"),
                    "workbookRepoUrl": v.get("workbookRepoUrl"),
                    "defaultViewRepoUrl": v.get("defaultViewRepoUrl"),
                    "description": desc,
                    "curatedAt": v.get("curatedAt"),
                    "viewCount": v.get("viewCount"),
                    "favorites": v.get("numberOfFavorites"),
                    "curatedImageUrl": v.get("curatedImageUrl"),
                    "directUrl": v.get("directUrl"),
                    "vizType": classify(v.get("title", ""), desc),
                }
            )
        nxt = data.get("next")
        if nxt is None or nxt <= start:
            break
        start = nxt
        time.sleep(0.3)

    entries = entries[: args.max]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(entries, indent=2))

    counts: dict[str, int] = {}
    for e in entries:
        counts[e["vizType"]] = counts.get(e["vizType"], 0) + 1
    print(f"saved {len(entries)} entries -> {OUT}")
    print("type counts:", json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()
