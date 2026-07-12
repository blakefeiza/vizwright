"""Shared fixtures. Adds tools/ to the import path and builds throwaway
artifacts (PNGs, CSVs) so tests are self-contained on a fresh clone / CI."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))


@pytest.fixture
def blank_png(tmp_path):
    from PIL import Image
    p = tmp_path / "blank.png"
    Image.new("RGB", (1400, 900), "white").save(p)
    return p


@pytest.fixture
def dark_blank_png(tmp_path):
    from PIL import Image
    p = tmp_path / "dark.png"
    Image.new("RGB", (1400, 900), "#0d1117").save(p)
    return p


@pytest.fixture
def real_png(tmp_path):
    """A dashboard-like image: solid panels of varied luminance that survive
    the 96x96 downsample (high std + ink), the way real charts do."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (1400, 900), "white")
    dr = ImageDraw.Draw(im)
    # a title bar, a dark panel, and several "bars" of different grays
    dr.rectangle([40, 30, 1360, 110], fill=(20, 20, 20))          # title band
    dr.rectangle([40, 140, 680, 860], fill=(30, 40, 60))          # dark chart panel
    for i, shade in enumerate((70, 120, 170, 210, 90, 150)):      # bars
        dr.rectangle([720, 160 + i * 110, 720 + 40 * (i + 3), 250 + i * 110],
                     fill=(shade, shade, shade))
    p = tmp_path / "real.png"
    im.save(p)
    return p


@pytest.fixture
def tiny_png(tmp_path):
    from PIL import Image
    p = tmp_path / "tiny.png"
    Image.new("RGB", (100, 80), "white").save(p)
    return p
