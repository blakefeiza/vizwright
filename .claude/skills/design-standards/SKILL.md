---
name: design-standards
description: Data visualization design standards and 100-point scoring rubric for dashboards — visual hierarchy, color discipline, spacing, chart hygiene. Derived from Tableau Viz of the Day winners. Use when designing a dashboard layout or lint-scoring a rendered dashboard screenshot.
---

# Dashboard Design Standards (VOTD-derived)

Derived from 300 cataloged Viz of the Day winners (2025-04 → 2026-07) and
close study of the top-favorited business dashboards
(`knowledge/votd/images/*.png`). These rules are enforced by the
design-linter agent using the rubric at the bottom.

## 1. Visual hierarchy — size first
- Exactly ONE dashboard title, the largest text on the page (24–28pt).
  Subtitle in 11–13pt grey on the same band, often stating the question or
  date context ("Tracking risk volume, severity, and time to resolution").
- Section/worksheet titles: 11–13pt, medium weight. Body/labels: 8–10pt.
- BAN numbers are the exception: 24–32pt bold — they ARE the message.
- Emphasis within text: bold or color on the key word/number only, never
  whole sentences. Hierarchy must survive a squint test: title → BANs →
  charts → detail.

## 2a. Color redundancy & accessibility (never color alone)
- Color must never be the ONLY channel carrying essential information —
  a reader who can't discern the hues must still get the message. Pair
  color with position (sorted order), direct labels, the takeaway title
  naming the members, or shape. Our standard moves: negative bars are red
  AND plot left of the zero line AND carry negative labels; focus regions
  are blue AND named in the title.
- Add visual separation between contiguous areas of color: stacked-bar
  segments get thin white borders so adjacent fills read as distinct
  (grammar in chart-xml-library recipe 15).
- Critical information is never interaction-only. Tooltips enrich; the
  headline, the ranking, and the anomaly must all be visible on the
  static render. (Our render-based lint enforces this implicitly — the
  linter only sees the PNG.)
- Written descriptions (captions, alt text, tooltips): objective and
  unambiguous. Actual values, not interpretations ("+16% vs 2025", never
  "growing rapidly"); spell out ambiguous formats ("June 2026" not
  "6/26"); describe what data MEANS, not what it looks like ("West
  region, the profit leader" — not "the dark blue line").

## 2. Color — sparse and intentional
- Greyscale is the default. Color exists to answer the question, not decorate.
- ONE hue family + at most one accent. VOTD winners are strongly
  monochromatic (lavender+coral, navy+per-section accent, orange on grey).
- NEVER one-color-per-category bars ("rainbow bars" = instant lint fail).
  A dimension only gets categorical color when color IS the encoding and
  there are ≤4 members; otherwise emphasize the focus member vs grey.
- Semantic color: red/negative, green-or-blue/positive, used consistently.
  Colorblind-safe pairs (blue/orange preferred over red/green when possible).
- Sequential palettes for maps/heatmaps, single-hue ramp.
- Recommended default palette: ink `#333333`, secondary text `#666666`,
  axis/grid `#e0e0e0`, canvas `#f7f7f7`, card `#ffffff`, primary `#4e79a7`,
  accent `#e15759`, positive `#59a14f`, negative `#e15759`.

## 3. Layout, spacing, padding
- Card model: white chart cards on a light-grey canvas, consistent gutters
  (≥8px equivalents everywhere; nothing touching edges).
- ONE column grid per dashboard: vertical gutters align across rows so the
  canvas shows through as continuous lines — a gutter that jogs sideways
  between rows reads as a mistake (lint D12 enforces: rows with equal
  column counts must share exact boundaries). Prefer the golden ratio
  (61800/38200 on the virtual grid) for 2-column rows. A row with a
  different column count (the 4-BAN band) is a deliberate rhythm change
  and may use its own divisions.
- Leading edges align: charts, titles, and text blocks share the same
  left edge.
- Fixed dashboard size (1400×900 landscape default).
- Grid discipline: BAN row top, primary chart largest and top-left of the
  chart area (reading order F-pattern), supporting charts below/right.
- Related metrics adjacent; repeated structures identical (same axis ranges,
  same ordering) so columns can be compared — see the Call Center winner's
  four identical channel columns.
- Whitespace is a separator; avoid visible borders — use spacing, not lines.

## 4. Chart hygiene
- Line discipline: every line — gridline, axis ruler, row/column divider,
  zero line, banding — is an explicit decision, never a default. Ask what
  it helps the reader do; if the answer is nothing, it's clutter and
  whitespace does the job. Zero-lines only where negative values exist
  (subtle grey). Axis rulers only for time orientation on line charts.
  Dividers/banding only in dense text tables.
- Axes: never squished — a chart's data must occupy >60% of its zone.
  Hide redundant axis when direct labels are on (bar labels at bar ends).
- Sort bars by value (not alphabetically) unless dimension has natural order.
- Numbers abbreviated: $470.5K, 2.1M, 64.4%. Month axes as letters
  (J F M A M J...) or MMM.
- Maximize the plot area: the data gets the pixels. Keep vertical-axis
  labels as short as clarity allows; move units into the title or a BAN
  ("Sales ($K)" in the title beats "$" repeated on every tick); long
  category names can sit inside the plot area when they don't obscure
  marks.
- Every chart earns its place by answering part of THE question. Cut
  anything that is decoration. 4–6 content zones max per dashboard.
- Tooltips are free real estate — put detail there, not on the canvas.
  But CURATED: a header (the dimension member, bold) + 2–4 labeled values
  that add context. Never the default all-pills dump; never raw
  calculation names.
- Axis titles are almost always redundant ("Quarter of Order Date",
  "Profit") — the chart title carries the meaning; clear them. Field/shelf
  labels likewise. Hide the value axis entirely when bars carry direct
  labels.
- BANs carry context: comparison delta (▲ 24.4% vs PY) in semantic color.
- The subtitle states the question and period — never values that BANs
  already display (duplication + truncation risk).

## 5. Text & annotation
- Dashboard title states the subject; subtitle states the question/period.
- Chart titles state the takeaway when possible ("West drives 31% of
  profit"), not just the dimensions ("Sales by Region").
- Color-match title phrases to their marks (Storytelling-with-Data move):
  the words naming the focus get the focus hue, loss phrases get the loss
  hue, de-emphasized members get grey. The title becomes the legend. One
  color language across the entire dashboard — never a hue that means one
  thing in a title and another in a chart.
- Numbers: abbreviate on axes and labels ($20K), keep full precision in
  tooltips (exact-value twin calc). BAN tooltips must add information or
  say something the number doesn't — never repeat the BAN.
- No legend if direct labeling or a boolean highlight can replace it.
- Footer: data source + date, 8pt grey. (In our pipeline: "Generated by
  vizwright" + run date.)

## Known failure modes (auto-flag; from live agent testing)
1. Rainbow bars — categorical palette on a plain bar chart.
2. Squished axes — chart compressed into a corner of its zone.
3. Gridline noise — default gridlines left on everywhere.
4. Cramped padding — zones touching each other or canvas edges.
5. Flat hierarchy — title same size as chart labels.
6. Legend sprawl — legends for single-color charts or duplicating labels.
7. Orphan color — a color that appears once and encodes nothing.
8. Unsorted bars — alphabetical category order hiding the ranking.

## Lint scoring rubric (100 points)

Score a rendered screenshot against the design_spec. Deduct per violation;
floor 0 per category. PASS ≥ 85 with no category at 0.

| Category | Pts | Deductions |
|---|---|---|
| Visual hierarchy | 20 | -8 no dominant title; -6 BANs not scannable; -4 per level-skip (body text bigger than section titles) |
| Color discipline | 20 | -10 rainbow bars; -5 >2 hue families; -5 non-semantic red/green; -3 orphan color |
| Layout & spacing | 20 | -6 cramped/touching zones; -6 misaligned grid; -4 dead whitespace hole; -4 reading order fights importance |
| Chart hygiene | 20 | -6 squished axis; -4 gridline noise; -4 unsorted bars; -3 redundant legend; -3 unabbreviated numbers |
| Insight communication | 20 | -8 charts don't answer the stated question; -6 no takeaway titles/BAN deltas; -6 decoration chart present |

Report format (design-linter agent): total score, per-category scores, each
violation as `[category] -N pts: <what/where> → <specific XML-level fix>`,
then verdict PASS / ITERATE.
