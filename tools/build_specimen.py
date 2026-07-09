#!/usr/bin/env python3
"""Generate the chart-specimen workbook: one worksheet per chart type on
superstore.csv, arranged in a grid dashboard. Serves as (a) empirical
verification that each chart-xml-library recipe renders, and (b) a visual
catalog for the open-source repo.

Hygiene defaults (lint_design D1-D11) are injected automatically.

Usage: python3 tools/build_specimen.py   -> output/chart-specimen.twb
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DS = "federated.superstore"
DATA_DIR = str(ROOT / "data")
K_FMT = "c!en_US!&quot;$&quot;#,##0,K;-&quot;$&quot;#,##0,K"
CUR = "c!en_US!&quot;$&quot;#,##0;-&quot;$&quot;#,##0"

CSV_COLUMNS = [
    ("Row ID", "integer"), ("Order ID", "string"), ("Order Date", "date"),
    ("Ship Date", "date"), ("Ship Mode", "string"), ("Customer ID", "string"),
    ("Customer Name", "string"), ("Segment", "string"), ("Country/Region", "string"),
    ("City", "string"), ("State/Province", "string"), ("Postal Code", "string"),
    ("Region", "string"), ("Product ID", "string"), ("Category", "string"),
    ("Sub-Category", "string"), ("Product Name", "string"), ("Sales", "real"),
    ("Quantity", "integer"), ("Discount", "real"), ("Profit", "real"),
]

CALCS = [
    # (name, caption, datatype, role, type, formula, default-format)
    ("Calc_Sales2", "Sales (twin)", "real", "measure", "quantitative", "[Sales]", K_FMT),
    ("Calc_Profit2", "Profit (twin)", "real", "measure", "quantitative", "[Profit]", K_FMT),
    ("Calc_Target", "Sales Target", "real", "measure", "quantitative", "[Sales] * 1.2", K_FMT),
    ("Calc_HalfPos", "Funnel Right", "real", "measure", "quantitative", "[Sales] / 2", K_FMT),
    ("Calc_HalfNeg", "Funnel Left", "real", "measure", "quantitative", "-[Sales] / 2", K_FMT),
    ("Calc_SalesBin", "Sales Bin ($250)", "integer", "dimension", "ordinal", "INT(FLOOR([Sales] / 250) * 250)", None),
]

BASE_COL_DECL = {
    "Region": ("string", "dimension", "nominal"),
    "Segment": ("string", "dimension", "nominal"),
    "Ship Mode": ("string", "dimension", "nominal"),
    "Sub-Category": ("string", "dimension", "nominal"),
    "Order Date": ("date", "dimension", "ordinal"),
    "Sales": ("real", "measure", "quantitative"),
    "Profit": ("real", "measure", "quantitative"),
    "Row ID": ("integer", "measure", "quantitative"),
}
CALC_DECL = {c[0]: (c[2], c[3], c[4], c[5], c[6]) for c in CALCS}

BLUE, GREY_MARK = "#4e79a7", "#c9c9c9"


def col_decl(field, indent="            "):
    if field in CALC_DECL:
        dt, role, typ, formula, fmt = CALC_DECL[field]
        fmt_attr = f" default-format='{fmt}'" if fmt else ""
        return (f"{indent}<column datatype='{dt}'{fmt_attr} name='[{field}]' role='{role}' type='{typ}'>\n"
                f"{indent}  <calculation class='tableau' formula='{formula}' />\n"
                f"{indent}</column>")
    dt, role, typ = BASE_COL_DECL[field]
    fmt = f" default-format='{K_FMT}'" if field in ("Sales", "Profit") else ""
    return f"{indent}<column datatype='{dt}'{fmt} name='[{field}]' role='{role}' type='{typ}' />"


def instance(inst):
    """'sum:Sales:qk' -> column-instance element + base field name."""
    deriv_map = {"none": "None", "sum": "Sum", "avg": "Avg", "cnt": "Count",
                 "yr": "Year", "tmn": "Month-Trunc", "tqr": "Quarter-Trunc", "usr": "User"}
    parts = inst.split(":")
    prefix, field = parts[0], parts[1]
    typ = "quantitative" if inst.endswith(":qk") else ("ordinal" if inst.endswith(":ok") else "nominal")
    return (f"            <column-instance column='[{field}]' derivation='{deriv_map[prefix]}' "
            f"name='[{inst}]' pivot='key' type='{typ}' />"), field


def worksheet(spec):
    name = spec["name"]
    insts = spec["instances"]
    decls, fields = [], []
    for i in insts:
        d, f = instance(i)
        decls.append(d)
        if f not in fields:
            fields.append(f)
    field_decls = "\n".join(col_decl(f) for f in fields)
    inst_decls = "\n".join(decls)

    def ref(i):
        return f"[{DS}].[{i}]"

    rows = spec.get("rows", "")
    cols = spec.get("cols", "")

    # axis title clears for every qk instance on shelves
    axis_rules = []
    for shelf, text in (("rows", rows), ("cols", cols)):
        for i in insts:
            if i.endswith(":qk") and f"[{i}]" in text:
                axis_rules.append(f"            <format attr='title' class='0' field='{ref(i)}' scope='{shelf}' value='' />")
    dual = spec.get("dual")
    if dual:
        shelf = dual["shelf"]
        second = dual["second"]
        axis_rules.append(
            f"            <encoding attr='space' class='0' field='{ref(second)}' "
            f"field-type='quantitative' fold='true' scope='{shelf}' synchronized='true' type='space' />")
        axis_rules.append(f"            <format attr='display' class='0' field='{ref(second)}' scope='{shelf}' value='false' />")
        if dual.get("hide_first"):
            axis_rules.append(f"            <format attr='display' class='0' field='{ref(dual['first'])}' scope='{shelf}' value='false' />")
    for extra in spec.get("axis_extra", []):
        axis_rules.append("            " + extra)
    if (rows or cols) and not any("stroke-" in r for r in axis_rules):
        axis_rules.append("            <format attr='stroke-size' value='0' />")
    axis_block = ("          <style-rule element='axis'>\n" + "\n".join(dict.fromkeys(axis_rules)) +
                  "\n          </style-rule>") if axis_rules else ""

    zero = spec.get("zeroline", "off")
    zero_block = ("          <style-rule element='zeroline'>\n"
                  + ("            <format attr='line-visibility' value='off' />" if zero == "off" else
                     "            <format attr='stroke-color' value='#c0c0c0' />\n            <format attr='stroke-size' value='1' />")
                  + "\n          </style-rule>")

    def _lf(entry):
        inst, fmt = entry if isinstance(entry, tuple) else (entry, K_FMT)
        return f"            <format attr='text-format' field='{ref(inst)}' value='{fmt}' />"
    cell_formats = "\n".join(_lf(e) for e in spec.get("label_fields", []))
    cell_block = (f"          <style-rule element='cell'>\n{cell_formats}\n          </style-rule>") if cell_formats else ""

    mark_color = spec.get("mark_color")
    mark_extra = f"\n            <format attr='mark-color' value='{mark_color}' />" if mark_color else ""
    labels_on = "false" if spec.get("labels") is False else "true"
    palette = spec.get("palette")
    pal_block = ""
    if palette:
        inst_p, mapping = palette
        maps = "\n".join(
            f"                <map to='{color}'>\n                  <bucket>{bucket}</bucket>\n                </map>"
            for bucket, color in mapping.items())
        pal_block = (f"            <style>\n              <style-rule element='mark'>\n"
                     f"                <encoding attr='color' field='{ref(inst_p)}' type='palette'>\n{maps}\n"
                     f"                </encoding>\n              </style-rule>\n            </style>")

    panes = []
    for p in spec["panes"]:
        attrs = "".join(f" {k}='{v}'" for k, v in p.get("attrs", {}).items())
        encs = "\n".join(f"              <{tag} column='{ref(col)}' />" for tag, col in p.get("enc", []))
        tooltip = p.get("tooltip", spec.get("tooltip"))
        tt = ""
        if tooltip:
            runs = [f"                <run bold='true'><![CDATA[<{ref(tooltip[0])}>]]></run>"]
            for label, i in tooltip[1:]:
                runs.append("                <run>Æ&#10;</run>")
                runs.append(f"                <run fontcolor='#787878'>{label}:  </run>")
                runs.append(f"                <run bold='true'><![CDATA[<{ref(i)}>]]></run>")
            tt = ("\n            <customized-tooltip show-buttons='false'>\n              <formatted-text>\n"
                  + "\n".join(runs) + "\n              </formatted-text>\n            </customized-tooltip>")
        sizing = p.get("sizing", "")
        panes.append(f"""          <pane{attrs} selection-relaxation-option='selection-relaxation-allow'>
            <view>
              <breakdown value='auto' />
            </view>
            <mark class='{p["mark"]}' />{sizing}
            <encodings>
{encs}
            </encodings>{tt}
          </pane>""")

    sorts = "\n".join("          " + x for x in spec.get("sorts", []))
    filters = "\n".join("          " + x for x in spec.get("filters", []))

    return f"""    <worksheet name='{name}'>
      <layout-options>
        <title>
          <formatted-text>
            <run bold='true' fontcolor='#333333' fontname='Tableau Medium' fontsize='12'>{spec["title"]}</run>
          </formatted-text>
        </title>
      </layout-options>
      <table>
        <view>
          <datasources>
            <datasource caption='Superstore' name='{DS}' />
          </datasources>
          <datasource-dependencies datasource='{DS}'>
{field_decls}
{inst_decls}
{pal_block}
          </datasource-dependencies>
{filters}
{sorts}
          <aggregation value='true' />
        </view>
        <style>
          <style-rule element='gridline'>
            <format attr='stroke-size' scope='rows' value='0' />
            <format attr='stroke-size' scope='cols' value='0' />
          </style-rule>
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
{zero_block}
{axis_block}
          <style-rule element='mark'>
            <format attr='mark-labels-show' value='{labels_on}' />
            <format attr='mark-labels-cull' value='true' />{mark_extra}
          </style-rule>
{cell_block}
          <style-rule element='worksheet'>
            <format attr='display-field-labels' scope='cols' value='false' />
            <format attr='display-field-labels' scope='rows' value='false' />
            <format attr='font-family' value='Tableau Book' />
            <format attr='color' value='#333333' />
          </style-rule>
        </style>
        <panes>
{chr(10).join(panes)}
        </panes>
        <rows>{rows}</rows>
        <cols>{cols}</cols>
      </table>
    </worksheet>"""


def R(i):
    return f"[{DS}].[{i}]"


YEAR_FILTER = [
    f"<filter class='categorical' column='{R('yr:Order Date:ok')}'>"
    "<groupfilter function='union'>"
    "<groupfilter function='member' level='[yr:Order Date:ok]' member='2025' />"
    "<groupfilter function='member' level='[yr:Order Date:ok]' member='2026' />"
    "</groupfilter></filter>",
    f"<slices><column>{R('yr:Order Date:ok')}</column></slices>",
]

SHEETS = [
    dict(name="SP Lollipop", title="Lollipop — ranking with less ink",
         instances=["none:Sub-Category:nk", "sum:Sales:qk", "sum:Calc_Sales2:qk"],
         rows=f"[{DS}].[none:Sub-Category:nk]",
         cols=f"({R('sum:Sales:qk')} + {R('sum:Calc_Sales2:qk')})",
         panes=[
             dict(mark="Bar", attrs={"x-axis-name": R("sum:Sales:qk")}, enc=[("lod", "none:Sub-Category:nk")],
                  sizing="\n            <mark-sizing custom-mark-size-in-axis-units='0.3' mark-alignment='mark-alignment-center' mark-sizing-setting='marks-scaling-on' use-custom-mark-size='true' />"),
             dict(mark="Circle", attrs={"x-axis-name": R("sum:Calc_Sales2:qk")},
                  enc=[("lod", "none:Sub-Category:nk"), ("text", "sum:Calc_Sales2:qk")]),
         ],
         dual=dict(shelf="cols", second="sum:Calc_Sales2:qk", first="sum:Sales:qk", hide_first=True),
         sorts=[f"<sort class='computed' column='{R('none:Sub-Category:nk')}' direction='DESC' using='{R('sum:Sales:qk')}' />"],
         tooltip=["none:Sub-Category:nk", ("Sales", "sum:Sales:qk")],
         label_fields=["sum:Calc_Sales2:qk", ("sum:Sales:qk", "c&quot;&quot;;&quot;&quot;")], mark_color=BLUE),

    dict(name="SP Dumbbell", title="Dumbbell — 2025 vs 2026 profit",
         instances=["none:Ship Mode:nk", "sum:Profit:qk", "sum:Calc_Profit2:qk", "yr:Order Date:ok"],
         rows=f"[{DS}].[none:Ship Mode:nk]",
         cols=f"({R('sum:Profit:qk')} + {R('sum:Calc_Profit2:qk')})",
         panes=[
             dict(mark="Line", attrs={"x-axis-name": R("sum:Profit:qk")}, enc=[("lod", "none:Ship Mode:nk"), ("path", "yr:Order Date:ok")]),
             dict(mark="Circle", attrs={"x-axis-name": R("sum:Calc_Profit2:qk")},
                  enc=[("lod", "none:Ship Mode:nk"), ("color", "yr:Order Date:ok")]),
         ],
         dual=dict(shelf="cols", second="sum:Calc_Profit2:qk", first="sum:Profit:qk"),
         palette=("yr:Order Date:ok", {"2025": "#c9c9c9", "2026": "#4e79a7"}),
         filters=YEAR_FILTER, zeroline="keep", labels=False,
         tooltip=["none:Ship Mode:nk", ("Profit", "sum:Profit:qk")]),

    dict(name="SP Bullet", title="Bullet — sales vs target (target = +20%)",
         instances=["none:Region:nk", "sum:Sales:qk", "sum:Calc_Target:qk"],
         rows=f"[{DS}].[none:Region:nk]",
         cols=f"({R('sum:Sales:qk')} + {R('sum:Calc_Target:qk')})",
         panes=[
             dict(mark="Bar", attrs={"x-axis-name": R("sum:Sales:qk")}, enc=[("lod", "none:Region:nk"), ("text", "sum:Sales:qk")]),
             dict(mark="GanttBar", attrs={"x-axis-name": R("sum:Calc_Target:qk")},
                  enc=[("lod", "none:Region:nk")]),
         ],
         dual=dict(shelf="cols", second="sum:Calc_Target:qk", first="sum:Sales:qk", hide_first=True),
         sorts=[f"<sort class='computed' column='{R('none:Region:nk')}' direction='DESC' using='{R('sum:Sales:qk')}' />"],
         tooltip=["none:Region:nk", ("Sales", "sum:Sales:qk"), ("Target", "sum:Calc_Target:qk")],
         label_fields=["sum:Sales:qk"], mark_color=BLUE),

    dict(name="SP Funnel", title="Funnel — mirrored halves by ship mode",
         instances=["none:Ship Mode:nk", "sum:Calc_HalfNeg:qk", "sum:Calc_HalfPos:qk", "sum:Sales:qk"],
         rows=f"[{DS}].[none:Ship Mode:nk]",
         cols=f"({R('sum:Calc_HalfNeg:qk')} + {R('sum:Calc_HalfPos:qk')})",
         panes=[
             dict(mark="Bar", enc=[("lod", "none:Ship Mode:nk")]),
             dict(mark="Bar", attrs={"x-axis-name": R("sum:Calc_HalfPos:qk")},
                  enc=[("lod", "none:Ship Mode:nk"), ("text", "sum:Sales:qk")]),
         ],
         sorts=[f"<sort class='computed' column='{R('none:Ship Mode:nk')}' direction='DESC' using='{R('sum:Sales:qk')}' />"],
         dual=dict(shelf="cols", second="sum:Calc_HalfPos:qk", first="sum:Calc_HalfNeg:qk", hide_first=True),
         tooltip=["none:Ship Mode:nk", ("Sales", "sum:Sales:qk")],
         label_fields=["sum:Sales:qk", ("sum:Calc_HalfNeg:qk", "c&quot;&quot;;&quot;&quot;")], mark_color=BLUE),

    dict(name="SP Pie", title="Pie — only ever for 2-3 parts (segment share)",
         instances=["none:Segment:nk", "sum:Sales:qk"],
         rows="", cols="",
         panes=[dict(mark="Pie", enc=[("color", "none:Segment:nk"), ("wedge-size", "sum:Sales:qk"), ("text", "sum:Sales:qk")])],
         tooltip=["none:Segment:nk", ("Sales", "sum:Sales:qk")],
         label_fields=["sum:Sales:qk"]),

    dict(name="SP Sparkline", title="Sparkline — trend without a chart's cost",
         instances=["tmn:Order Date:qk", "sum:Sales:qk"],
         rows=f"[{DS}].[sum:Sales:qk]",
         cols=f"[{DS}].[tmn:Order Date:qk]",
         panes=[dict(mark="Line", enc=[])],
         axis_extra=[f"<format attr='display' field='{R('sum:Sales:qk')}' scope='rows' value='false' />",
                     f"<format attr='display' field='{R('tmn:Order Date:qk')}' scope='cols' value='false' />"],
         labels=False,
         tooltip=["tmn:Order Date:qk", ("Sales", "sum:Sales:qk")], mark_color=BLUE),

    dict(name="SP Stacked Bar", title="Stacked bar — composition by region",
         instances=["none:Region:nk", "none:Segment:nk", "sum:Sales:qk"],
         rows=f"[{DS}].[none:Region:nk]",
         cols=f"[{DS}].[sum:Sales:qk]",
         panes=[dict(mark="Bar", enc=[("color", "none:Segment:nk")])],
         palette=("none:Segment:nk", {"&quot;Consumer&quot;": "#4e79a7", "&quot;Corporate&quot;": "#86b0d2", "&quot;Home Office&quot;": "#c9c9c9"}),
         sorts=[f"<sort class='computed' column='{R('none:Region:nk')}' direction='DESC' using='{R('sum:Sales:qk')}' />"],
         tooltip=["none:Region:nk", ("Segment", "none:Segment:nk"), ("Sales", "sum:Sales:qk")]),

    dict(name="SP Grouped Bar", title="Grouped bar — nested dimensions",
         instances=["none:Region:nk", "none:Segment:nk", "sum:Sales:qk"],
         rows=f"[{DS}].[none:Region:nk] / [{DS}].[none:Segment:nk]",
         cols=f"[{DS}].[sum:Sales:qk]",
         panes=[dict(mark="Bar", enc=[("color", "none:Segment:nk")])],
         palette=("none:Segment:nk", {"&quot;Consumer&quot;": "#4e79a7", "&quot;Corporate&quot;": "#86b0d2", "&quot;Home Office&quot;": "#c9c9c9"}),
         tooltip=["none:Segment:nk", ("Sales", "sum:Sales:qk")]),

    dict(name="SP Slope", title="Slope — segment sales, 2025 vs 2026",
         instances=["yr:Order Date:ok", "none:Segment:nk", "sum:Sales:qk"],
         rows=f"[{DS}].[sum:Sales:qk]",
         cols=f"[{DS}].[yr:Order Date:ok]",
         panes=[dict(mark="Line", enc=[("color", "none:Segment:nk"), ("text", "sum:Sales:qk")])],
         palette=("none:Segment:nk", {"&quot;Consumer&quot;": "#4e79a7", "&quot;Corporate&quot;": "#86b0d2", "&quot;Home Office&quot;": "#c9c9c9"}),
         filters=YEAR_FILTER,
         tooltip=["none:Segment:nk", ("Sales", "sum:Sales:qk")],
         label_fields=["sum:Sales:qk"]),

    dict(name="SP Histogram", title="Histogram — order-line sales distribution ($250 bins)",
         instances=["none:Calc_SalesBin:ok", "cnt:Row ID:qk"],
         rows=f"[{DS}].[cnt:Row ID:qk]",
         cols=f"[{DS}].[none:Calc_SalesBin:ok]",
         panes=[dict(mark="Bar", enc=[("text", "cnt:Row ID:qk")])],
         label_fields=[("cnt:Row ID:qk", "n#,##0;-#,##0")],
         tooltip=["none:Calc_SalesBin:ok", ("Order lines", "cnt:Row ID:qk")], mark_color=BLUE),

    dict(name="SP Area", title="Area — monthly sales magnitude",
         instances=["tmn:Order Date:qk", "sum:Sales:qk"],
         rows=f"[{DS}].[sum:Sales:qk]",
         cols=f"[{DS}].[tmn:Order Date:qk]",
         panes=[dict(mark="Area", enc=[])],
         axis_extra=[f"<format attr='stroke-color' scope='cols' value='#d0d0d0' />",
                     f"<format attr='stroke-size' scope='rows' value='0' />"],
         tooltip=["tmn:Order Date:qk", ("Sales", "sum:Sales:qk")], mark_color=BLUE),

    dict(name="SP Treemap", title="Treemap (experimental) — sub-category share",
         instances=["none:Sub-Category:nk", "sum:Sales:qk", "sum:Profit:qk"],
         rows="", cols="",
         panes=[dict(mark="Square",
                     enc=[("lod", "none:Sub-Category:nk"), ("size", "sum:Sales:qk"),
                          ("color", "sum:Profit:qk"), ("text", "none:Sub-Category:nk")])],
         tooltip=["none:Sub-Category:nk", ("Sales", "sum:Sales:qk"), ("Profit", "sum:Profit:qk")]),
]


def dashboard():
    zones, zid = [], 10
    cols_n = 3
    cell_w = 100000 // cols_n
    rows_n = (len(SHEETS) + cols_n - 1) // cols_n
    title_h = 6000
    cell_h = (100000 - title_h) // rows_n
    zones.append(f"""          <zone h='{title_h}' w='96000' x='2000' y='0' id='2' type-v2='text' forceUpdate='true'>
            <formatted-text>
              <run bold='true' fontcolor='#333333' fontname='Tableau Bold' fontsize='22'>CHART SPECIMEN BOOK</run>
              <run fontcolor='#666666' fontname='Tableau Book' fontsize='11'>  |  every recipe in chart-xml-library, rendered from superstore.csv</run>
            </formatted-text>
            <zone-style>
              <format attr='border-style' value='none' />
              <format attr='padding' value='12' />
            </zone-style>
          </zone>""")
    for r in range(rows_n):
        row_sheets = SHEETS[r * cols_n:(r + 1) * cols_n]
        children = []
        for c, spec in enumerate(row_sheets):
            zid += 1
            children.append(f"""            <zone fixed-size='486' is-fixed='true' h='{cell_h}' w='{cell_w}' x='{c * cell_w}' y='{title_h + r * cell_h}' id='{zid}' name='{spec["name"]}' show-title='true'>
              <zone-style>
                <format attr='border-style' value='none' />
                <format attr='margin' value='8' />
                <format attr='padding' value='14' />
                <format attr='background-color' value='#ffffff' />
              </zone-style>
            </zone>""")
        zid += 1
        zones.append(f"""          <zone fixed-size='490' is-fixed='true' h='{cell_h}' w='100000' x='0' y='{title_h + r * cell_h}' id='{zid}' param='horz' type-v2='layout-flow'>
{chr(10).join(children)}
          </zone>""")
    return f"""    <dashboard name='Chart Specimen Book'>
      <style />
      <size maxheight='2100' maxwidth='1500' minheight='2100' minwidth='1500' sizing-mode='fixed' />
      <zones>
        <zone h='100000' w='100000' x='0' y='0' id='1' param='vert' type-v2='layout-flow'>
{chr(10).join(zones)}
          <zone-style>
            <format attr='border-style' value='none' />
            <format attr='padding' value='12' />
            <format attr='background-color' value='#f7f7f7' />
          </zone-style>
        </zone>
      </zones>
    </dashboard>"""


def main():
    csv_cols = "\n".join(
        f"            <column datatype='{dt}' name='{n}' ordinal='{i}' />"
        for i, (n, dt) in enumerate(CSV_COLUMNS))
    ds_calcs = "\n".join(col_decl(c[0], indent="      ") for c in CALCS)
    ds_base = "\n".join(col_decl(f, indent="      ") for f in BASE_COL_DECL)
    sheets = "\n".join(worksheet(s) for s in SHEETS)

    twb = f"""<?xml version='1.0' encoding='utf-8' ?>
<workbook original-version='18.1' source-build='2026.1.0 (20261.26.0410.0924)' source-platform='mac' version='18.1' xmlns:user='http://www.tableausoftware.com/xml/user'>
  <preferences />
  <datasources>
    <datasource caption='Superstore' inline='true' name='{DS}' version='18.1'>
      <connection class='federated'>
        <named-connections>
          <named-connection caption='superstore' name='textscan.superstore'>
            <connection class='textscan' directory='{DATA_DIR}' filename='superstore.csv' workgroup-auth-mode='as-is' />
          </named-connection>
        </named-connections>
        <relation connection='textscan.superstore' name='superstore.csv' table='[superstore#csv]' type='table'>
          <columns character-set='UTF-8' header='yes' locale='en_US' separator=','>
{csv_cols}
          </columns>
        </relation>
      </connection>
{ds_base}
{ds_calcs}
    </datasource>
  </datasources>
  <worksheets>
{sheets}
  </worksheets>
  <dashboards>
{dashboard()}
  </dashboards>
  <windows>
    <window class='dashboard' maximized='true' name='Chart Specimen Book'>
      <viewpoints />
      <active id='-1' />
      <device-preview selected='Desktop' />
    </window>
  </windows>
</workbook>"""
    out = ROOT / "output" / "chart-specimen.twb"
    out.write_text(twb)
    print(f"wrote {out} ({len(SHEETS)} specimens)")


if __name__ == "__main__":
    main()
