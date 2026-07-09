# Roadmap / Next-session notes

## Chart chooser taxonomies to fold into the designer (Blake, 2026-07-09)
Blake shared three chart-chooser references to widen the designer agent's
vocabulary beyond the current 8 recipes:

1. **Chart Chooser — 56 Charts Analysis** (datavizclarity.com) — branches:
   comparison, composition, distribution, chronology, cartography. Each chart
   rated on cognitive overload / need for context / misleading risk — those
   ratings could become designer-agent guardrails (e.g. avoid "very likely
   misleading" types unless requested).
2. **Extreme Presentation chart chooser** (Andrew Abela) — "What would you
   like to show?" → comparison / relationship / distribution / composition.
3. **FT Visual Vocabulary** (ft.com/vocabulary) — 9 intents: deviation,
   correlation, ranking, distribution, change over time, magnitude,
   part-to-whole, spatial, flow. Best taxonomy of the three for mapping a
   business question to a chart intent.

Implementation sketch: new `chart-chooser` skill (or a section in
chart-xml-library) mapping question-intent → candidate charts → which have
working XML recipes (and which need a new recipe mined from
`knowledge/xml-patterns/`). Designer picks by intent, not by habit.

## Interactivity knowledge base (next major skill — Blake, 2026-07-10)
Goal: an `interactivity` skill + lint checks covering the full action
vocabulary, mined from real XML the same way the chart library was:
- **Filter actions** (click a chart → filter the dashboard) — the corpus
  ALREADY contains these: `<actions>` blocks exist in the mined VOTD
  workbooks (e.g. CaseOverview-ServiceDesk "Click on a chart to filter"),
  and validate_twb already tolerates their generated `Action (...)` fields.
  Start by extracting `<actions>` from knowledge/votd/twbx/*.twb.
- **Highlight actions** (hover → emphasize related marks).
- **Parameters** (corpus has `<column param-domain-type='list'>` examples +
  the special Parameters datasource) + parameter actions.
- **Set actions** (click → update a set → drive calcs/colors).
- **URL actions** (click → open link; go-to-sheet navigation).
- Hover vs click (select) trigger semantics; menu vs run-on-single-select.
- Best-in-class examples: Blake is in Andy Kriebel's Next Level Tableau
  cohort and will supply exemplar workbook XML — drop files into
  knowledge/interactivity/ for mining.
- Design principles to encode: interaction reveals detail, never the
  headline (best practice: don't require interaction for critical info); make
  targets big (whole-plot-area hover); every action needs a visible
  affordance cue (subtitle hint like "click a bar to filter").
- Specimen-book equivalent: an interactive specimen dashboard verifying
  each action type against the Cloud render + manual click-through.

## Milestone 2 — open-source quick start
- Genericize absolute paths (textscan directory) — template + setup script.
- Ship an example run (runs/ is gitignored; add `examples/`).
- Skill-regeneration prompts in README (retrain design-standards on your taste).
- Push to GitHub.

## Later
- ~~Automated render loop~~ DONE 2026-07-09: tools/publish_render.py publishes
  to a Tableau Cloud dev site and exports view PNGs.
  Note: Cloud publish requires package-relative textscan paths (directory='Data');
  the tool auto-rewrites (`cloudify`). Desktop keeps absolute paths.
- Test whether Desktop also opens relative-path twbx — if yes, unify to one variant.
- ~~Recipes: funnel, bullet, dual-axis~~ DONE 2026-07-10 (specimen book: 12 new types verified).
- Recipes still to add (need table-calc grammar): waterfall, bump, box plot, 100%-stacked.
- PR the VOTD `startIndex` pagination fix upstream to wjsutton/tableau-public-mcp
  (task chip already flagged).
