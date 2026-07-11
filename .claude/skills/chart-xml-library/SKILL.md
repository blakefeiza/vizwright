---
name: chart-xml-library
description: Recipe book of Tableau chart types as twb XML — shelf patterns, mark classes, and encodings for BANs, bars, lines, scatter, maps, heatmaps, and a known-good dashboard layout skeleton. Mined from Viz of the Day winners. Use when choosing or building a specific chart.
---

# Chart XML Library (mined from VOTD winners)

Each recipe gives the `<mark>`, `<rows>`, `<cols>`, and `<encodings>` deltas.
Boilerplate (datasource-dependencies, style, panes wrapper) is in the
twb-authoring skill. `[ds]` = your datasource name, e.g. `[federated.superstore]`.
Raw examples: `knowledge/xml-patterns/<chart-type>/*.xml`.

Chart selection guide, organized by question intent (FT Visual Vocabulary).
Every recipe below is RENDER-VERIFIED via the specimen book
(`tools/build_specimen.py` → output/chart-specimen.twbx — regenerate and
publish it after changing any recipe).

| Intent | Question shape | Chart | Recipe |
|---|---|---|---|
| Magnitude | "How much overall?" | BAN / KPI card | 1 |
| Ranking | "Compare categories" | Horizontal bar, sorted | 2 |
| Ranking | "Compare, minimal ink" | Lollipop / dot plot | 9 |
| Change over time | "Trend?" | Line (month-truncated) | 3 |
| Change over time | "Trend + magnitude" | Area | 4 |
| Change over time | "Trend in a card" | Sparkline | 14 |
| Change over time | "Then vs now (2 periods)" | Slope | 16 |
| Deviation | "Before vs after / A vs B" | Dumbbell | 10 |
| Deviation | "Actual vs target" | Bullet | 11 |
| Correlation | "Two measures related?" | Scatter | 5 |
| Spatial | "Where geographically?" | Filled map | 6 |
| Magnitude | "Two dims × measure" | Heatmap / highlight table | 7 |
| Part-to-whole | "Composition (per category)" | Stacked bar | 15 |
| Ranking | "Compare within groups" | Grouped bar (nested dims) | 15 |
| Part-to-whole | "Share of total, 2-3 parts ONLY" | Pie | 13 |
| Part-to-whole | "Many parts, hierarchy" | Treemap | 18 |
| Flow | "Stage drop-off" | Funnel | 12 |
| Distribution | "Value spread" | Histogram (calc bins) | 17 |
| — | "Exact values / detail" | Text table (sparingly) | 8 |

Not yet in the library (need table-calc grammar; do not improvise):
waterfall, bump chart, box plot, 100%-stacked via percent-of-total.

## 1. BAN / KPI card
Text mark, measure on Text shelf, empty rows/cols. One BAN per sheet.
```xml
<panes><pane>
  <view><breakdown value='auto' /></view>
  <mark class='Text' />
  <encodings><text column='[ds].[sum:Sales:qk]' /></encodings>
</pane></panes>
<rows></rows>
<cols></cols>
```
Format the number big via pane style:
```xml
<style-rule element='mark'>
  <format attr='font-size' value='28' />
  <format attr='font-weight' value='bold' />
  <format attr='color' value='#333333' />
</style-rule>
```
VOTD pattern: BAN row = 3–4 cards across the top, each with a small caption
(worksheet title, 9–10pt grey) above the number.

## 2. Horizontal bar (sorted)
Dimension on rows, measure on cols, computed sort DESC, single color, labels on.
```xml
<mark class='Bar' />
<rows>[ds].[none:Region:nk]</rows>
<cols>[ds].[sum:Sales:qk]</cols>
<!-- in <view> -->
<sort class='computed' column='[ds].[none:Region:nk]' direction='DESC'
      using='[ds].[sum:Sales:qk]' />
```
Single-hue via `mark-color` style rule (see twb-authoring). To emphasize one
bar (e.g. the focus region), use a boolean calc on Color instead of a
categorical palette:
```xml
<column caption='Is Focus' datatype='boolean' name='[Calculation_IsFocus]' role='dimension' type='nominal'>
  <calculation class='tableau' formula='[Region]=&quot;West&quot;' />
</column>
<!-- encoding -->
<encodings><color column='[ds].[none:Calculation_IsFocus:nk]' /></encodings>
```

## 3. Line (trend over time)
Continuous month on cols (green pill = truncation `tmn`), measure on rows.
```xml
<mark class='Line' />
<rows>[ds].[sum:Sales:qk]</rows>
<cols>[ds].[tmn:Order Date:qk]</cols>
```
Dependencies: `<column-instance column='[Order Date]' derivation='Month-Trunc'
name='[tmn:Order Date:qk]' pivot='key' type='quantitative' />`.
Multi-line: add `<color column='[ds].[none:Segment:nk]' />` encoding — max
3–4 lines, grey the non-focus lines.

## 4. Area
Same shelves as line, `<mark class='Area' />`. Stack only when parts sum to a
meaningful whole.

## 5. Scatter (render-verified: "Bang for the Flop")
Continuous field on each shelf, a dimension on detail (`lod`) to make one
mark per item.
```xml
<mark class='Circle' />
<rows>[ds].[sum:Profit:qk]</rows>
<cols>[ds].[sum:Sales:qk]</cols>
<encodings>
  <color column='[ds].[none:Type:nk]' />   <!-- optional, needs a palette map -->
  <text column='[ds].[none:Label:nk]' />   <!-- optional, label standouts only -->
  <lod column='[ds].[none:Entity:nk]' />    <!-- REQUIRED: the mark grain -->
</encodings>
```
Add a zeroline style rule so the negative quadrant reads instantly:
```xml
<style-rule element='zeroline'><format attr='stroke-color' value='#c0c0c0' /></style-rule>
```

**Time scatter (dots over release date):** put a continuous date
truncation on cols — `[tyr:Order Date:qk]` (Year-Trunc), not an exact-date
instance. Measure on rows, item on `lod`.

**Log-scale axis (mined 2026-07-11, verified live).** When a measure spans
100×+ (most dots pile into the bottom fifth of a linear axis, top is dead
space), make the axis logarithmic. It's a `space` encoding with
`scale='log'` in the axis style-rule, on the shelf's measure instance:
```xml
<style-rule element='axis'>
  <encoding attr='space' class='0' field='[ds].[sum:PerfB:qk]'
            field-type='quantitative' scale='log' scope='rows' type='space' />
</style-rule>
```
`scope='rows'` for the y-axis, `'cols'` for x. All values must be > 0
(log has no zero). Log turned a sparse, mostly-empty scatter into an
even spread AND separated the two populations into clean bands.

**Label only the standouts** (avoid 50 overlapping labels): a calc that
returns a short name for notable marks and `''` otherwise, on the `text`
shelf. Cleaning names reads better:
`IF [PerfB] > 18 THEN REPLACE([Entity],'NVIDIA GeForce ','') ELSE '' END`.

**GOTCHA that silently blanks the whole worksheet (cost several renders):**
do NOT add `<tooltip>` encodings that duplicate a field already on a
shelf (e.g. `<tooltip column='[ds].[sum:PerfB:qk]'>` when `sum:PerfB` is on
rows). It renders the sheet blank on a white background with no error.
Use a `<customized-tooltip>` that references on-viz fields instead
(fields already on rows/cols/color/lod are available to it). Same failure
signature — blank white sheet — means "this worksheet errored," almost
always a bad encoding reference.

## 6. Filled map (US states)
State dimension on lod + auto lat/long. Declare the geographic role on the column:
```xml
<column datatype='string' name='[State/Province]' role='dimension' type='nominal'
        semantic-role='[State].[Name]' />
```
Worksheet:
```xml
<mark class='Automatic' />
<rows>[ds].[none:Latitude (generated):qk]</rows>
<cols>[ds].[none:Longitude (generated):qk]</cols>
<encodings>
  <lod column='[ds].[none:State/Province:nk]' />
  <color column='[ds].[sum:Sales:qk]' />
</encodings>
```
Declare generated fields in dependencies:
```xml
<column datatype='real' name='[Latitude (generated)]' role='measure' type='quantitative' />
<column datatype='real' name='[Longitude (generated)]' role='measure' type='quantitative' />
<column-instance column='[Latitude (generated)]' derivation='None' name='[none:Latitude (generated):qk]' pivot='key' type='quantitative' />
<column-instance column='[Longitude (generated)]' derivation='None' name='[none:Longitude (generated):qk]' pivot='key' type='quantitative' />
```
Maps are the most fragile chart type to hand-author. If the map fails to
render, fall back to a sorted bar of states — a VOTD-acceptable substitute.

## 7. Heatmap / highlight table
Two dimensions crossed, Square mark, measure on color (sequential palette).
```xml
<mark class='Square' />
<rows>[ds].[none:Sub-Category:nk]</rows>
<cols>[ds].[none:Region:nk]</cols>
<encodings>
  <color column='[ds].[sum:Sales:qk]' />
  <text column='[ds].[sum:Sales:qk]' />
</encodings>
```

## 8. Text table
Dimensions on rows, measure(s) as text. Use only for top-N detail panels.
```xml
<mark class='Text' />
<rows>[ds].[none:Product Name:nk]</rows>
<encodings><text column='[ds].[sum:Sales:qk]' /></encodings>
```

## Dual-axis grammar (unlocks recipes 9-12)

Two instances summed in parens on a shelf = two axes:
`<cols>([ds].[sum:Sales:qk] + [ds].[sum:Calc_Sales2:qk])</cols>`
(dual-axis the SAME measure via a twin calc `[Calc_X2]=[X]` — identical
instance names collide).

Each mark layer is a `<pane>` bound to its axis. **The axis-name attribute
matches the SHELF: cols → `x-axis-name`, rows → `y-axis-name`** (wrong
orientation = invisible marks, verified live):
```xml
<pane x-axis-name='[ds].[sum:Sales:qk]'> <mark class='Bar' /> ... </pane>
<pane x-axis-name='[ds].[sum:Calc_Sales2:qk]'> <mark class='Circle' /> ... </pane>
```

Overlay + synchronize via a `space` encoding on the SECOND instance in the
axis style-rule (without it the axes render side-by-side):
```xml
<style-rule element='axis'>
  <encoding attr='space' class='0' field='[ds].[sum:Calc_Sales2:qk]'
            field-type='quantitative' fold='true' scope='cols' synchronized='true' type='space' />
  <format attr='display' class='0' field='[ds].[sum:Calc_Sales2:qk]' scope='cols' value='false' />
</style-rule>
```
Hide the folded axis header (and usually the first too when labels carry
the values).

## Categorical palette maps (no default orange!)

Explicit member→color mapping lives in a `<style>` INSIDE
`datasource-dependencies` (string buckets keep their quotes):
```xml
<style>
  <style-rule element='mark'>
    <encoding attr='color' field='[ds].[none:Segment:nk]' type='palette'>
      <map to='#4e79a7'><bucket>&quot;Consumer&quot;</bucket></map>
      <map to='#86b0d2'><bucket>&quot;Corporate&quot;</bucket></map>
      <map to='#c9c9c9'><bucket>&quot;Home Office&quot;</bucket></map>
    </encoding>
  </style-rule>
</style>
```
Sequential-emphasis families (dark blue → light blue → grey) beat rainbow.

## 9. Lollipop / dot plot (ranking, minimal ink)
Dual-axis same measure: Bar pane (thin stem) + Circle pane. Suppress the
Bar pane's duplicate label with an empty text-format:
```xml
<!-- stem sizing on the Bar pane -->
<mark-sizing custom-mark-size-in-axis-units='0.3' mark-alignment='mark-alignment-center'
             mark-sizing-setting='marks-scaling-on' use-custom-mark-size='true' />
<!-- label only once -->
<style-rule element='cell'>
  <format attr='text-format' field='[ds].[sum:Calc_Sales2:qk]' value='c!en_US!&quot;$&quot;#,##0,K;-&quot;$&quot;#,##0,K' />
  <format attr='text-format' field='[ds].[sum:Sales:qk]' value='c&quot;&quot;;&quot;&quot;' />
</style-rule>
```
Drop the Bar pane entirely for a pure dot plot.

## 10. Dumbbell (A vs B per category)
Dual-axis same measure; Line pane (connector, `<path column='[ds].[yr:Order
Date:ok]' />`) + Circle pane colored by the 2-member dimension (palette:
earlier period grey, later blue). Filter the dimension to exactly 2 members.
Labels off (`mark-labels-show false`); zero line kept if negatives.

## 11. Bullet (actual vs target)
Dual-axis (sum:Actual + sum:Target); Bar pane (actual, labeled) +
GanttBar pane (target tick — no size encoding needed). Target can be a
calc (`[Sales] * 1.2`) or a real target column.

## 12. Funnel (stage drop-off)
Mirrored halves: calcs `[Calc_HalfPos]=[X]/2`, `[Calc_HalfNeg]=-[X]/2`,
dual-axis cols, both panes Bar, stage dimension on rows sorted DESC.
Hide both axes; suppress the negative half's labels with the
empty-format trick (`c&quot;&quot;;&quot;&quot;`); label the total on the
positive pane via `<text column='[ds].[sum:X:qk]' />`.

## 13. Pie (part-to-whole, 2-3 parts ONLY)
Mark `Pie`, empty shelves, `wedge-size` is the pie-specific encoding:
```xml
<mark class='Pie' />
<encodings>
  <color column='[ds].[none:Segment:nk]' />
  <wedge-size column='[ds].[sum:Sales:qk]' />
  <text column='[ds].[sum:Sales:qk]' />
</encodings>
```

## 14. Sparkline (trend in a card)
Line recipe with EVERYTHING off: `mark-labels-show false`, both axes
`display false`, no gridlines/rulers. Pairs beside a BAN.

## 15. Stacked / grouped bar
Stacked: bar recipe + categorical `<color>` encoding (≤4 members, palette
map required, labels per segment OK). Separate contiguous fills with thin
white borders so adjacent segments read as distinct marks:
```xml
<style-rule element='mark'>
  <format attr='border-color' value='#ffffff' />
  <format attr='border-width' value='1' />
  <format attr='border-style' value='solid' />
</style-rule>
```
Grouped: nest dimensions on the shelf —
`<rows>[ds].[none:Region:nk] / [ds].[none:Segment:nk]</rows>`.

## 16. Slope (two periods)
Line mark, discrete year on cols filtered to 2 members, measure on rows,
color by category (palette map), `<text>` labels on both endpoints.

## 17. Histogram (distribution)
No special bin XML needed — a calc dimension does it:
`[Calc_SalesBin] = INT(FLOOR([Sales] / 250) * 250)` (integer, dimension,
ordinal). Bins on cols as `[none:Calc_SalesBin:ok]`, `[cnt:Row ID:qk]` on
rows, Bar mark, plain-number label format.

## 18. Treemap (hierarchy share; verified but style it)
Square mark, EMPTY shelves, size+color+text encodings:
```xml
<mark class='Square' />
<encodings>
  <lod column='[ds].[none:Sub-Category:nk]' />
  <size column='[ds].[sum:Sales:qk]' />
  <color column='[ds].[sum:Profit:qk]' />
  <text column='[ds].[none:Sub-Category:nk]' />
</encodings>
```
Continuous color defaults to Tableau's orange-blue diverging ramp — fine
for profit +/- but set an explicit diverging palette when brand colors
matter (interpolated color grammar TBD; flag if needed).

## Known-good dashboard layout skeleton (executive overview)

1400×900 fixed. Virtual grid is 0–100000 on both axes.

**CRITICAL (learned from a live mis-render): a `layout-flow` container
stacks its children along its axis and reflows them — sibling zones with
absolute x/w do NOT tile side-by-side inside a `vert` container.** Every
row that holds multiple zones side-by-side MUST be an explicit
`param='horz'` layout-flow zone whose children split its width. Corpus
dashboards use 5–30 nested horz containers; flat zone lists render as a
full-width vertical stack.

Structure: root vert → one zone per row (text / horz container) →
children inside each horz row. Give rows `fixed-size` (pixels) +
`is-fixed='true'` to pin heights. Children of a horz row share its y/h;
their w values should sum to the row width.

**One column grid for the whole dashboard (lint D12):** every 2-column
row splits at the SAME x — prefer the golden ratio (61800/38200). Gutters
must stack into continuous vertical lines; a boundary that jogs between
rows breaks the canvas rhythm. Only a row with a different column count
(the BAN band) may use its own divisions.

```xml
<zones>
  <zone h='100000' w='100000' x='0' y='0' id='1' param='vert' type-v2='layout-flow'>
    <!-- Row 1: title band -->
    <zone fixed-size='80' is-fixed='true' h='9000' w='100000' x='0' y='0' id='2' type-v2='text' forceUpdate='true'>
      <formatted-text>
        <run bold='true' fontcolor='#333333' fontname='Tableau Bold' fontsize='26'>TITLE</run>
        <run fontcolor='#666666' fontname='Tableau Book' fontsize='12'>  |  subtitle with the question</run>
      </formatted-text>
      <zone-style><format attr='border-style' value='none' /><format attr='margin' value='8' /></zone-style>
    </zone>
    <!-- Row 2: BAN row (horz container, 3 cards) -->
    <zone fixed-size='120' is-fixed='true' h='14000' w='100000' x='0' y='9000' id='3' param='horz' type-v2='layout-flow'>
      <zone h='14000' w='33333' x='0'     y='9000' id='4' name='BAN Sales'  fixed-size='466' is-fixed='true'>
        <zone-style><format attr='border-style' value='none' /><format attr='margin' value='8' /><format attr='background-color' value='#ffffff' /></zone-style>
      </zone>
      <zone h='14000' w='33333' x='33333' y='9000' id='5' name='BAN Profit'>
        <zone-style><format attr='border-style' value='none' /><format attr='margin' value='8' /><format attr='background-color' value='#ffffff' /></zone-style>
      </zone>
      <zone h='14000' w='33334' x='66666' y='9000' id='6' name='BAN Orders'>
        <zone-style><format attr='border-style' value='none' /><format attr='margin' value='8' /><format attr='background-color' value='#ffffff' /></zone-style>
      </zone>
    </zone>
    <!-- Row 3: main charts (horz container, golden ratio) -->
    <zone h='42000' w='100000' x='0' y='23000' id='7' param='horz' type-v2='layout-flow'>
      <zone h='42000' w='61800' x='0'     y='23000' id='8' name='Primary Chart'>
        <zone-style><format attr='border-style' value='none' /><format attr='margin' value='8' /><format attr='background-color' value='#ffffff' /></zone-style>
      </zone>
      <zone h='42000' w='38200' x='61800' y='23000' id='9' name='Secondary Chart'>
        <zone-style><format attr='border-style' value='none' /><format attr='margin' value='8' /><format attr='background-color' value='#ffffff' /></zone-style>
      </zone>
    </zone>
    <!-- Row 4: support charts (same grid as row 3) -->
    <zone h='31000' w='100000' x='0' y='65000' id='10' param='horz' type-v2='layout-flow'>
      <zone h='31000' w='61800' x='0'     y='65000' id='11' name='Support Chart A'>
        <zone-style><format attr='border-style' value='none' /><format attr='margin' value='8' /><format attr='background-color' value='#ffffff' /></zone-style>
      </zone>
      <zone h='31000' w='38200' x='61800' y='65000' id='12' name='Support Chart B'>
        <zone-style><format attr='border-style' value='none' /><format attr='margin' value='8' /><format attr='background-color' value='#ffffff' /></zone-style>
      </zone>
    </zone>
    <!-- Row 5: footer -->
    <zone fixed-size='24' is-fixed='true' h='4000' w='100000' x='0' y='96000' id='13' type-v2='text' forceUpdate='true'>
      <formatted-text><run fontcolor='#666666' fontname='Tableau Book' fontsize='8'>Data source · date</run></formatted-text>
      <zone-style><format attr='border-style' value='none' /><format attr='margin' value='4' /></zone-style>
    </zone>
    <zone-style>
      <format attr='border-style' value='none' />
      <format attr='padding' value='12' />
      <format attr='background-color' value='#f7f7f7' />
    </zone-style>
  </zone>
</zones>
```
The `margin=8` + white `background-color` on chart zones gives the VOTD
"card" look. Real multi-container examples:
`knowledge/xml-patterns/dashboards/*.xml` (e.g. CaseOverview Executive
Summary: 19 horz containers).

## Number formatting (BANs, labels, axes)

Set `default-format` on the datasource `<column>` (verbatim corpus forms):
- Currency: `default-format='c!en_US!&quot;$&quot;#,##0;-&quot;$&quot;#,##0'`
- Percent: `default-format='p0.0%'`
- Plain: `default-format='n#,##0;-#,##0'`

Abbreviated currency (BANs, bar labels) via per-field `text-format` in the
worksheet `<style>`; the K/M suffix MUST be unquoted with scaling commas —
quoting it (`,&quot;K&quot;`) renders a literal suffix WITHOUT scaling
($292,296.8K disaster, verified live):
- Thousands: `c!en_US!&quot;$&quot;#,##0,K;-&quot;$&quot;#,##0,K` → $292K
- Millions: `c&quot;$&quot;#,##0,,.0M;-&quot;$&quot;#,##0,,.0M` → $2.3M

```xml
<format attr='text-format' field='[ds].[sum:Profit:qk]'
        value='c!en_US!&quot;$&quot;#,##0,K;-&quot;$&quot;#,##0,K' />
```

## Killing gridlines (corpus-verified form)

`stroke-color none` is unreliable; corpus workbooks zero the stroke size:
```xml
<style-rule element='gridline'>
  <format attr='stroke-size' scope='rows' value='0' />
  <format attr='stroke-size' scope='cols' value='0' />
</style-rule>
```

## Detail hygiene defaults (MUST — enforced by tools/lint_design.py)

Every chart worksheet ships with ALL of these on the first pass. They are
what separates "agent output" from a VOTD-quality dashboard; each was
verified against a live render 2026-07-09.

1. **Hide field labels** (kills the "Region"/"Sub-Ca.." shelf captions),
   inside `<style-rule element='worksheet'>`:
```xml
<format attr='display-field-labels' scope='cols' value='false' />
<format attr='display-field-labels' scope='rows' value='false' />
```

2. **Clear axis titles** for EVERY continuous (`:qk`) instance on rows or
   cols (nobody needs "Quarter of Order Date" under a chart whose title
   already says it), inside `<style-rule element='axis'>`:
```xml
<format attr='title' class='0' field='[ds].[tqr:Order Date:qk]' scope='cols' value='' />
```
   To hide a redundant value axis entirely (bars with direct labels):
```xml
<format attr='display' field='[ds].[sum:Profit:qk]' scope='cols' value='false' />
```

3. **Bar labels**: labels come from an explicit `<text>` encoding, and the
   abbreviated format binds under `element='cell'` — a text-format under
   `element='label'` does NOT bind (verified live):
```xml
<encodings><text column='[ds].[sum:Profit:qk]' /></encodings>
<!-- in <style> -->
<style-rule element='cell'>
  <format attr='text-format' field='[ds].[sum:Profit:qk]'
          value='c!en_US!&quot;$&quot;#,##0,K;-&quot;$&quot;#,##0,K' />
</style-rule>
```

4. **Curated tooltip** in every chart pane, after `</encodings>`. Only the
   fields that add context — never the default all-pills dump. Fields are
   referenced as CDATA; `Æ&#10;` inside a run is Tableau's line break:
```xml
<customized-tooltip show-buttons='false'>
  <formatted-text>
    <run bold='true'><![CDATA[<[ds].[none:Region:nk]>]]></run>
    <run>Æ&#10;</run>
    <run fontcolor='#787878'>Profit:  </run>
    <run bold='true'><![CDATA[<[ds].[sum:Profit:qk]>]]></run>
  </formatted-text>
</customized-tooltip>
```
   Referenced fields must be on an encoding shelf or declared via
   `<tooltip column='...' />` encodings and in datasource-dependencies.

5. **Text zones**: title and footer zones get `<format attr='padding'
   value='12' />` in their zone-style. The subtitle must NOT repeat values
   the BANs already show (keep it question + period; a truncated subtitle
   is worse than a short one).

6. **Every worksheet zone breathes**: `<format attr='padding' value='16' />`
   in the zone-style of every chart and BAN zone (alongside margin 8 +
   white background). Thin padding was the #1 human complaint on early
   renders.

7. **BAN cards**: numbers center-aligned, and the default tooltip (which
   just repeats the BAN) is replaced with one line of ADDITIONAL context:
```xml
<style-rule element='cell'>
  <format attr='text-align' value='center' />
  <format attr='vertical-align' value='center' />
  <format attr='text-format' field='[ds].[sum:Profit:qk]' value='c!en_US!&quot;$&quot;#,##0,K;-&quot;$&quot;#,##0,K' />
</style-rule>
<!-- in the pane, after </encodings>: static context, not the number again -->
<customized-tooltip show-buttons='false'>
  <formatted-text><run fontcolor='#787878'>93% from Technology + Office Supplies</run></formatted-text>
</customized-tooltip>
```

8. **Axis tick abbreviation ($20,000 → $20K)**: the ONLY thing that binds
   to axis ticks is the DATASOURCE-LEVEL `default-format` of the measure.
   Confirmed non-binding (do not retry): `text-format` in a
   `<style-rule element='axis'>`, and per-worksheet `default-format`
   overrides in datasource-dependencies. Pattern: set the K format on the
   datasource column, and add a full-precision twin calc for tooltips:
```xml
<column datatype='real' default-format='c!en_US!&quot;$&quot;#,##0,K;-&quot;$&quot;#,##0,K' name='[Profit]' ... />
<column caption='Profit (exact)' datatype='real' default-format='c!en_US!&quot;$&quot;#,##0;-&quot;$&quot;#,##0'
        name='[Calculation_ProfitExact]' role='measure' type='quantitative'>
  <calculation class='tableau' formula='[Profit]' />
</column>
```
   Tooltips reference `[sum:Calculation_ProfitExact:qk]`; axes/labels get
   $20K. Every field a tooltip references needs a `default-format`
   (rates/ratios like Discount get `p0.0%` or they render raw 0.1123).

9. **Line discipline — every line is a decision, none by default.** VOTD
   winners declare `stroke-size 0` over 1,200 times across 20 workbooks:
   they explicitly kill every line, then add back the few that earn a
   place. Whitespace separates; lines only orient. Default block for every
   chart sheet (dividers + banding OFF):
```xml
<style-rule element='table-div'>
  <format attr='stroke-size' scope='rows' value='0' />
  <format attr='line-visibility' scope='rows' value='off' />
  <format attr='stroke-size' scope='cols' value='0' />
  <format attr='line-visibility' scope='cols' value='off' />
</style-rule>
<style-rule element='pane'>
  <format attr='band-color' scope='rows' value='#00000000' />
  <format attr='band-color' scope='cols' value='#00000000' />
</style-rule>
```
   Then decide per sheet:
   | Line | Keep when | Grammar |
   |---|---|---|
   | Zero line | negatives exist (diverging bars, +/- lines) | `element='zeroline'`: `stroke-color #c0c0c0` + `stroke-size 1`; else `line-visibility off` |
   | Axis ruler | time orientation on line charts (x only) | `element='axis'`: `stroke-color scope='cols' #d0d0d0`, `stroke-size scope='rows' 0`; bars: `stroke-size 0` |
   | Gridlines | wide chart, unlabeled marks (rare) | default OFF via stroke-size 0 |
   | Dividers | dense text tables only | default OFF |
   | Banding | wide text tables only, `#f5f5f5` | default OFF (`#00000000`) |

10. **Title color emphasis (match mark color)**: chart titles are takeaway
   sentences; color the key phrases to match their marks — one hue
   language across the whole dashboard (focus/positive `#4e79a7`, loss
   `#e15759`, de-emphasized context `#999999`, ink `#333333`):
```xml
<formatted-text>
  <run bold='true' fontcolor='#4e79a7' fontname='Tableau Medium' fontsize='12'>West + East</run>
  <run bold='true' fontcolor='#333333' fontname='Tableau Medium' fontsize='12'> deliver 70% of profit — </run>
  <run bold='true' fontcolor='#999999' fontname='Tableau Medium' fontsize='12'>Central</run>
  <run bold='true' fontcolor='#333333' fontname='Tableau Medium' fontsize='12'> earns just 7.9¢ per sales dollar</run>
</formatted-text>
```
