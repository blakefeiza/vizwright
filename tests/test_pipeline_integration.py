"""End-to-end happy path: the specimen generator produces a workbook that
passes BOTH gates (structural + design). This guards validate_twb, lint_design,
finalize_windows, and build_specimen together — if any drifts, this breaks."""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "superstore.csv"


def _load(mod_name):
    spec = importlib.util.spec_from_file_location(mod_name, ROOT / "tools" / f"{mod_name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.mark.skipif(not DATA.exists(), reason="demo dataset not present")
def test_specimen_builds_validates_and_lints(monkeypatch):
    build = _load("build_specimen")
    validate = _load("validate_twb")
    lint = _load("lint_design")
    finalize = _load("finalize_windows")

    build.main()  # writes output/chart-specimen.twb
    twb = ROOT / "output" / "chart-specimen.twb"
    assert twb.exists()

    monkeypatch.setattr(sys, "argv", ["finalize_windows.py", str(twb)])
    assert finalize.main(str(twb)) == 0
    assert validate.main(str(twb)) == 0, "specimen workbook fails structural validation"
    assert lint.main(str(twb)) == 0, "specimen workbook fails design lint"
