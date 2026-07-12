import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BAD_WORKSHEET = """<?xml version='1.0' encoding='utf-8' ?>
<workbook source-build='2026.1.0' version='18.1'>
  <worksheets>
    <worksheet name='Bad Bar'>
      <table>
        <view><datasource-dependencies datasource='ds' /></view>
        <style></style>
        <panes><pane><mark class='Bar' /></pane></panes>
        <rows>[ds].[none:Cat:nk]</rows>
        <cols>[ds].[sum:Val:qk]</cols>
      </table>
    </worksheet>
  </worksheets>
  <dashboards></dashboards>
  <windows></windows>
</workbook>"""


def _lint():
    spec = importlib.util.spec_from_file_location("lint_design", ROOT / "tools" / "lint_design.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def test_unhygienic_worksheet_fails(tmp_path, capsys):
    p = tmp_path / "bad.twb"
    p.write_text(BAD_WORKSHEET)
    assert _lint().main(str(p)) == 1
    out = capsys.readouterr().out
    # the bare worksheet trips the field-label and gridline checks at minimum
    assert "D1" in out
    assert "D3" in out
