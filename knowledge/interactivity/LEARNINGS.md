# Interactivity + advanced grammar — mined from Blake's MM workbook (2026-07-10)

Source: `mm-beeswarm/Historical Tropical Cyclones #MakeoverMonday.twb`
(Blake Feiza, Makeover Monday, IBTrACS hurricanes). Restyled derivative:
`output/atlantic-fury.twb`.

## Set actions (edit-group-action) — VERIFIED grammar
Two actions drive the beeswarm→map interactivity: hover and select both
ASSIGN the hovered/selected marks' SIDs into a set; the map filters to
set members.
```xml
<actions>
  <edit-group-action caption='Update SID Set' name='[Action1_...]'>
    <activation type='on-hover' />          <!-- or on-select -->
    <source type='all' />                   <!-- or dashboard='X' type='sheet' -->
    <add-or-remove-marks value='assign' />
    <params>
      <param name='selection-clear-set-option' value='do-nothing' />
      <param name='target-group' value='[federated.X].[Set 1]' />
    </params>
  </edit-group-action>
</actions>
```
Sets are `<group>` elements in the datasource:
```xml
<group caption='Selected SID Set' name='[Set 1]' name-style='unqualified' user:ui-builder='lasso-group'>
  <groupfilter function='member' level='[Calc_intensity]' member='5' />
</group>
```
The DEFAULT membership defines what a static render shows — set it to a
meaningful cohort (we used "all Cat-5 storms") so the dashboard works
without interaction (accessibility best practice). Filter a sheet by set:
`<filter class='categorical' column='[ds].[Set 1]' />`.

## Numeric bins with a parameter-driven size — VERIFIED
```xml
<column aggregation='None' caption='Year (bin)' datatype='integer' name='[Year (bin)]' role='dimension' type='quantitative'>
  <calculation class='bin' decimals='0' formula='[Calc_Year]' peg='0' size-parameter='[Parameters].[Parameter 1]' />
</column>
```
Bin used on a shelf as CONTINUOUS: `[none:Year (bin):qk]`.

## Beeswarm (table calc) — VERIFIED, full recipe
- Rows: `[usr:Calc_Beeswarm:qk:6]` — table-calc instances get a NUMERIC
  SUFFIX (`:qk:6`); note `endswith(':qk')` checks miss these.
- The INDEX()-based symmetric stagger formula lives in the workbook
  (Beeswarm calc): odd/even record counts alternate above/below y=0.
- Compute-using is declared on the column-instance:
```xml
<column-instance ...>
  <table-calc ordering-type='Field'>
    <order field='[ds].[SID]' />
    <order field='[ds].[Calc_intensity]' />
  </table-calc>
</column-instance>
```
- Ordering by intensity makes hot categories cluster at the swarm CENTER
  (storm-eye effect) — sort the addressing dimension by the color measure.

## Map layers + storm paths — VERIFIED
Multi-layer maps = multiple panes: base `Automatic` pane, `Line` pane
(paths: `<path column='[none:ISO_TIME:ok]' />` + `<lod SID>` + size/color),
`Multipolygon` pane (`<geometry column='[Geometry (generated)]' />`).
Rows/cols: `avg:LAT` / `avg:LON`. Basemap: `<mapsource name='Tableau' />`;
`<mapsource name='' />` = NO basemap (raw axes appear — only usable when
drawing all land yourself). Washout: `<style-rule element='map'><format
attr='washout' .../>`. **Base-map style: `<format attr='map-style'
value='dark' />` (also 'light'/'normal') in the element='map' style-rule —
attr 'style' is a no-op, it must be 'map-style' (verified live).**

## Map hygiene: disable pan/zoom/search/toolbar — VERIFIED
Lives in the dashboard window's viewpoint for the map worksheet
(tools/finalize_windows.py now emits this automatically for any sheet
with a mapsource):
```xml
<viewpoint name='Map'>
  <zoom type='entire-view' />
  <floating-toolbar-visibility value='2' />
  <geo-search-visibility value='1' />
  <map-navigation value='1' />
  <layer-control toolbar-button-enabled='false' />
</viewpoint>
```

## Set actions: the set's DEFINING LEVEL controls what hover assigns
Hover/select assigns the hovered marks' values OF THE SET'S OWN FIELD.
A set defined on an intensity calc assigns intensities (hover one dot →
every storm of that category). Define the set on the entity key ([SID])
and enumerate default members explicitly:
```xml
<group caption='Selected SID Set' name='[Set 1]' ...>
  <groupfilter function='union'>
    <groupfilter function='member' level='[SID]' member='&quot;1924288N16277&quot;' />
    ...
  </groupfilter>
</group>
```
Default membership = the static story (all 45 Cat-5s); hover = one storm.

## Dark theme — VERIFIED
Worksheet transparency alone is NOT enough; set BOTH:
```xml
<style-rule element='table'><format attr='background-color' value='#0e1520' /></style-rule>
<style-rule element='worksheet'><format attr='background-color' value='#0e1520' /> ... </style-rule>
```
plus dashboard root zone background. Light text: worksheet `color`
#c8d4e0; axis text: element='axis' `color` #7f92a6.

## Data gotcha
IBTrACS 'NA' basin (North Atlantic) parses as NULL. Blake's Atlantic
scoping uses `WMO_AGENCY = 'hurdat_atl'` instead — copy that filter, not
BASIN.
