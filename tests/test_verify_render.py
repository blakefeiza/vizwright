import sys
import verify_render as vr


def _check(p):
    return vr.check_image(p, 600, 400, 4.0, 0.02)


def test_blank_white_fails(blank_png):
    r = _check(blank_png)
    assert r["ok"] is False
    assert any("R3" in f for f in r["fails"])


def test_dark_blank_fails(dark_blank_png):
    r = _check(dark_blank_png)
    assert r["ok"] is False


def test_tiny_fails_dimensions(tiny_png):
    r = _check(tiny_png)
    assert r["ok"] is False
    assert any("R2" in f for f in r["fails"])


def test_real_passes(real_png):
    r = _check(real_png)
    assert r["ok"] is True


def test_empty_dir_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["verify_render.py", str(tmp_path)])
    assert vr.main() == 1  # zero renders -> gate fails


def test_main_passes_on_real(real_png, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["verify_render.py", str(real_png)])
    assert vr.main() == 0
