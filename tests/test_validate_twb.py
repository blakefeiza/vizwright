import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _validate():
    spec = importlib.util.spec_from_file_location("validate_twb", ROOT / "tools" / "validate_twb.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


MINIMAL_OK = """<?xml version='1.0' encoding='utf-8' ?>
<workbook source-build='2026.1.0' version='18.1'>
  <worksheets></worksheets>
  <dashboards></dashboards>
  <windows></windows>
</workbook>"""


def test_missing_source_build_fails(tmp_path, capsys):
    p = tmp_path / "no_build.twb"
    p.write_text(MINIMAL_OK.replace("source-build='2026.1.0' ", ""))
    assert _validate().main(str(p)) == 1
    assert "source-build" in capsys.readouterr().out


def test_bad_xml_fails(tmp_path):
    p = tmp_path / "bad.twb"
    p.write_text("<workbook><unclosed></workbook>")
    assert _validate().main(str(p)) == 1


def test_minimal_valid_passes(tmp_path):
    p = tmp_path / "ok.twb"
    p.write_text(MINIMAL_OK)
    assert _validate().main(str(p)) == 0
