import lint_consistency as lc

# two minimal workbook strings that share a design system vs. one that drifts
CONSISTENT_A = """<workbook>
  <dashboards><dashboard name='A'><size maxheight='900' maxwidth='1400' /></dashboard></dashboards>
  <run fontname='Tableau Book' fontsize='24'>Title</run>
  <mark class='Bar' /> #4e79a7 <format attr='text-format' value='c#,##0' />
</workbook>"""

CONSISTENT_B = """<workbook>
  <dashboards><dashboard name='B'><size maxheight='900' maxwidth='1400' /></dashboard></dashboards>
  <run fontname='Tableau Book' fontsize='24'>Title</run>
  <mark class='Bar' /> #4e79a7 <format attr='text-format' value='c#,##0' />
</workbook>"""

DRIFTED = """<workbook>
  <dashboards><dashboard name='C'><size maxheight='950' maxwidth='1500' /></dashboard></dashboards>
  <run fontname='Comic Sans' fontsize='40'>Title</run>
  <mark class='Pie' /> #ff00ff <format attr='text-format' value='p0.0%' />
</workbook>"""


def _fp(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(content)
    return lc.fingerprint(p)


def test_identical_series_is_consistent(tmp_path):
    fps = [_fp(tmp_path, "a.twb", CONSISTENT_A), _fp(tmp_path, "b.twb", CONSISTENT_B)]
    assert lc.diff(fps) == []


def test_drift_is_flagged(tmp_path):
    fps = [_fp(tmp_path, "a.twb", CONSISTENT_A), _fp(tmp_path, "c.twb", DRIFTED)]
    warns = lc.diff(fps)
    assert warns  # at least one drift issue
    joined = " ".join(warns)
    assert "font" in joined or "canvas" in joined or "title-size" in joined


def test_fingerprint_extracts_brand_colors(tmp_path):
    fp = _fp(tmp_path, "a.twb", CONSISTENT_A)
    assert "#4e79a7" in fp["palette"]
    assert "Tableau Book" in fp["fonts"]
    assert fp["title_size"] == 24
