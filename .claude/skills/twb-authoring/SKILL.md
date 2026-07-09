---
name: twb-authoring
description: How to author valid Tableau workbook (.twb) XML from scratch — file skeleton, datasource connections, worksheet anatomy, dashboard zones, and the validate-then-package workflow. Use whenever writing or editing Tableau XML.
---

# Tableau Workbook (.twb) XML Authoring

A `.twb` is UTF-8 XML. A `.twbx` is a zip containing the `.twb` plus a `Data/`
folder with data files. Target `version='18.1'` — every current Tableau Public
VOTD workbook we mined uses it, and Desktop 2024.1–2026.1 opens it.

**Ground rules (learned from mining 20 VOTD winners):**
1. NEVER invent XML. Adapt patterns from `knowledge/xml-patterns/` or the
   snippets in the chart-xml-library skill.
2. Back up the current `.twb` before every edit (`cp file.twb file.twb.bak-N`).
3. After every edit: run `python3 tools/validate_twb.py <file>` and fix
   errors before packaging with `python3 tools/package_twbx.py`.
4. Field references must match the datasource column names EXACTLY,
   including bracket syntax: `[Sales]`, `[Order Date]`.

## Workbook skeleton (element order matters)

```xml
<?xml version='1.0' encoding='utf-8' ?>
<workbook original-version='18.1' source-build='2026.1.0 (20261.26.0410.0924)'
          source-platform='mac' version='18.1'
          xmlns:user='http://www.tableausoftware.com/xml/user'>
  <preferences />
  <datasources> ... </datasources>
  <worksheets> ... </worksheets>
  <dashboards> ... </dashboards>
  <windows> ... generate with tools/finalize_windows.py, see below ... </windows>
</workbook>
```

Three hard requirements confirmed by live Tableau load errors (2026-07-09):
- `source-build` on `<workbook>` is REQUIRED — omitting it fails the load
  with "Error(2,125): missing required attribute 'source-build'".
- A dashboard `<window>` must NOT be self-closing: its content model
  requires `<viewpoints>` + `<active id='-1' />` children.
- The dashboard window's `<viewpoints>` must contain one
  `<viewpoint name='<worksheet>'><zoom type='entire-view' /></viewpoint>`
  per worksheet used in the dashboard, AND every worksheet needs its own
  `<window class='worksheet'>` with a standard `<cards>` block. Missing
  viewpoints crash the loader with generic Internal Error 2805CF18
  (assert `HasVisualDoc` in DashboardController).

Do not hand-write the `<windows>` block — after authoring worksheets and
dashboards, run:

```bash
python3 tools/finalize_windows.py output/<name>.twb
```

It rebuilds the whole block in canonical form from the workbook's own
worksheets and dashboard zones. Then validate and package as usual.

Top-level order in real workbooks: `preferences, datasources, (actions),
worksheets, dashboards, windows`. Omit `document-format-change-manifest`,
`repository-location`, and `_.fcp.*` feature-flag attributes — they are
optional and Tableau regenerates them.

## Datasource: CSV via federated textscan

```xml
<datasource caption='Superstore' inline='true' name='federated.superstore' version='18.1'>
  <connection class='federated'>
    <named-connections>
      <named-connection caption='superstore' name='textscan.superstore'>
        <connection class='textscan' directory='/absolute/path/to/data'
                    filename='superstore.csv' workgroup-auth-mode='as-is' />
      </named-connection>
    </named-connections>
    <relation connection='textscan.superstore' name='superstore.csv'
              table='[superstore#csv]' type='table'>
      <columns character-set='UTF-8' header='yes' locale='en_US' separator=','>
        <column datatype='string'  name='Region'     ordinal='0' />
        <column datatype='date'    name='Order Date' ordinal='1' />
        <column datatype='real'    name='Sales'      ordinal='2' />
        <column datatype='integer' name='Quantity'   ordinal='3' />
      </columns>
    </relation>
  </connection>
  <column datatype='real' name='[Sales]' role='measure' type='quantitative' />
  <column datatype='string' name='[Region]' role='dimension' type='nominal' />
  <column datatype='date' name='[Order Date]' role='dimension' type='ordinal' />
</datasource>
```

Notes:
- `table='[filename#csv]'` — the `.csv` extension becomes `#csv`.
- Declare EVERY column in `<columns>` with the right `datatype`
  (`string | integer | real | date | datetime | boolean`) and `ordinal`
  matching CSV column order (0-based). Column `name` has NO brackets here.
- The `<column>` elements after `</connection>` (bracketed names) set
  role/type; also home for calculated fields:

```xml
<column caption='Profit Ratio' datatype='real' name='[Calculation_ProfitRatio]'
        role='measure' type='quantitative'>
  <calculation class='tableau' formula='SUM([Profit])/SUM([Sales])' />
</column>
```

Calculated-field role rules (corpus-verified):
- Row-level formula (`[Region]='West'`, `IF [Discount]>0.2 THEN...`):
  `role='dimension'` (if categorical/boolean) — shelf instances use
  `derivation='None'` → `[none:Calculation_X:nk]`.
- ANY formula containing an aggregate (`SUM(`, `AVG(`, ...): MUST be
  `role='measure'` even when boolean/nominal (e.g. `SUM([Profit])>=0` is
  `role='measure' type='nominal' datatype='boolean'`). Shelf instances use
  `derivation='User'` → `[usr:Calculation_X:nk]` (nominal) or
  `[usr:Calculation_X:qk]` (quantitative). Declaring an aggregate calc as
  role='dimension' crashes Tableau's loader with a generic Internal Error.

## Worksheet anatomy

```xml
<worksheet name='Sales by Region'>
  <table>
    <view>
      <datasources>
        <datasource caption='Superstore' name='federated.superstore' />
      </datasources>
      <datasource-dependencies datasource='federated.superstore'>
        <!-- every raw column used -->
        <column datatype='string' name='[Region]' role='dimension' type='nominal' />
        <column datatype='real' name='[Sales]' role='measure' type='quantitative' />
        <!-- every derived instance used on any shelf -->
        <column-instance column='[Region]' derivation='None'
                         name='[none:Region:nk]' pivot='key' type='nominal' />
        <column-instance column='[Sales]' derivation='Sum'
                         name='[sum:Sales:qk]' pivot='key' type='quantitative' />
      </datasource-dependencies>
      <aggregation value='true' />
    </view>
    <style> ... style-rules, see below ... </style>
    <panes>
      <pane selection-relaxation-option='selection-relaxation-allow'>
        <view><breakdown value='auto' /></view>
        <mark class='Bar' />
        <encodings> ... optional color/size/label/text encodings ... </encodings>
      </pane>
    </panes>
    <rows>[federated.superstore].[none:Region:nk]</rows>
    <cols>[federated.superstore].[sum:Sales:qk]</cols>
  </table>
</worksheet>
```

### column-instance naming grammar (critical)

`[derivation-prefix:FieldName:type-key]`
- Dimension as-is: `[none:Region:nk]` (nk = nominal key, ok = ordinal key)
- Sum/Avg/Count: `[sum:Sales:qk]`, `[avg:Sales:qk]`, `[cnt:Order ID:qk]`,
  `[ctd:Customer Name:qk]` (count distinct)
- Date truncations (continuous, green): `[tyr:Order Date:qk]` (year),
  `[tqr:...]` (quarter), `[tmn:Order Date:qk]` (month)
- Date parts (discrete, blue): `[yr:Order Date:ok]`, `[mn:Order Date:ok]`
- The derivation attribute spells it out: `None, Sum, Avg, Cnt, CntD,
  Year-Trunc, Month-Trunc, Year, Month` etc.

Every column-instance used in `<rows>`, `<cols>`, or `<encodings>` MUST be
declared in `<datasource-dependencies>`, and every raw `column` it derives
from too. `validate_twb.py` checks this.

### Shelf expressions
- Multiple fields on a shelf: concatenate — `[ds].[a] / [ds].[b]` nests.
- Dual axis / measure values are advanced; prefer one measure per sheet.

### Encodings (inside `<pane>`)

```xml
<encodings>
  <color column='[federated.superstore].[none:Category:nk]' />
  <size column='[federated.superstore].[sum:Quantity:qk]' />
  <text column='[federated.superstore].[sum:Sales:qk]' />   <!-- mark labels / BAN -->
  <lod column='[federated.superstore].[none:State:nk]' />    <!-- detail shelf -->
</encodings>
```

### Sorting a dimension by a measure

```xml
<sort class='computed' column='[federated.superstore].[none:Region:nk]'
      direction='DESC' using='[federated.superstore].[sum:Sales:qk]' />
```
Place directly inside `<view>` after datasource-dependencies.

### Filters

```xml
<filter class='categorical' column='[federated.superstore].[none:Region:nk]'>
  <groupfilter function='member' level='[none:Region:nk]' member='&quot;West&quot;' />
</filter>
```
Also declare `<slices><column>...same column...</column></slices>` after filters.

### Worksheet style rules (inside `<table><style>`)

```xml
<style>
  <style-rule element='gridline'>
    <format attr='stroke-color' value='none' scope='rows' />
    <format attr='stroke-color' value='none' scope='cols' />
  </style-rule>
  <style-rule element='axis'>
    <format attr='stroke-color' value='#e0e0e0' />
  </style-rule>
  <style-rule element='worksheet'>
    <format attr='font-family' value='Tableau Book' />
    <format attr='color' value='#333333' />
  </style-rule>
  <style-rule element='mark'>
    <format attr='mark-labels-show' value='true' />
    <format attr='mark-labels-cull' value='true' />
  </style-rule>
</style>
```
Common elements: `mark, cell, table, axis, pane, label, worksheet, zeroline,
header, gridline, datalabel, title`. Kill gridlines by default; VOTD winners
run near-zero gridline ink.

### Fixed mark color (single-hue bars — no color legend)

```xml
<style-rule element='mark'>
  <format attr='mark-color' value='#4e79a7' />
</style-rule>
```

### Worksheet title

```xml
<layout-options>
  <title>
    <formatted-text>
      <run bold='true' fontcolor='#333333' fontname='Tableau Medium' fontsize='12'>Sales by Region</run>
    </formatted-text>
  </title>
</layout-options>
```
Place `<layout-options>` inside `<worksheet>` before `<table>`.

## Dashboard anatomy

```xml
<dashboard name='Executive Overview'>
  <style />
  <size maxheight='900' maxwidth='1400' minheight='900' minwidth='1400' sizing-mode='fixed' />
  <zones>
    <zone h='100000' w='100000' x='0' y='0' id='1' param='vert' type-v2='layout-flow'>
      <!-- children: title zone, rows of charts, spacers -->
      <zone h='8000' w='98000' x='1000' y='1000' id='2' type-v2='text' forceUpdate='true'>
        <formatted-text>
          <run bold='true' fontcolor='#333333' fontname='Tableau Bold' fontsize='24'>DASHBOARD TITLE</run>
        </formatted-text>
        <zone-style>
          <format attr='border-style' value='none' />
          <format attr='margin' value='8' />
        </zone-style>
      </zone>
      <zone h='40000' w='48000' x='1000' y='10000' id='3' name='Sales by Region'>
        <zone-style>
          <format attr='border-style' value='none' />
          <format attr='margin' value='8' />
        </zone-style>
      </zone>
      <zone-style>
        <format attr='border-style' value='none' />
        <format attr='padding' value='16' />
        <format attr='background-color' value='#f5f5f5' />
      </zone-style>
    </zone>
  </zones>
</dashboard>
```

Rules:
- Coordinates are in a 0–100000 virtual grid (both axes), independent of
  pixel size. `x + w <= 100000`, `y + h <= 100000`.
- One root zone (`param='vert'`, full 100000×100000). Children can be
  worksheet zones (`name='<exact worksheet name>'`, no type-v2), text zones
  (`type-v2='text'`), spacers (`type-v2='empty'` + `fixed-size`), or nested
  `layout-flow` containers (`param='horz'|'vert'`).
- Every zone needs a unique integer `id`.
- Fixed dashboard size (e.g. 1400×900) keeps agent-computed layout exact.
- Worksheet zones hide titles unless you add
  `show-title='true'`; simpler to rely on worksheet `<layout-options><title>`.
- `<windows>` at workbook end should name the dashboard so it opens first.

## Validate → package → deliver

```bash
python3 tools/validate_twb.py output/<name>.twb        # structural lint
python3 tools/package_twbx.py output/<name>.twb data/superstore.csv
# -> output/<name>.twbx  (zip: workbook.twb + Data/superstore.csv)
```

If Tableau reports errors on open, the message names the element — diff
against the last `.bak` and consult `knowledge/xml-patterns/` for a working
example of that element.
