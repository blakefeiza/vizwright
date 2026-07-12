import json
import sys
import run_state as rs


def _run(monkeypatch, tmp_path, *args):
    monkeypatch.setattr(rs, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["run_state.py", *args])
    return rs.main()


def test_lifecycle(monkeypatch, tmp_path):
    assert _run(monkeypatch, tmp_path, "r1", "reset") == 0
    assert _run(monkeypatch, tmp_path, "r1", "bump") == 0
    assert _run(monkeypatch, tmp_path, "r1", "record", "--score", "56", "--verdict", "ITERATE") == 0
    assert _run(monkeypatch, tmp_path, "r1", "bump") == 0
    assert _run(monkeypatch, tmp_path, "r1", "record", "--score", "92", "--verdict", "PASS") == 0
    state = json.loads((tmp_path / "runs" / "r1" / "iteration_state.json").read_text())
    assert state["status"] == "passed"
    assert state["iteration"] == 2
    assert state["history"][-1]["score"] == 92


def test_cap_returns_exit_3(monkeypatch, tmp_path):
    _run(monkeypatch, tmp_path, "r2", "reset")
    for _ in range(3):
        assert _run(monkeypatch, tmp_path, "r2", "bump") == 0
    # 4th bump is over the cap
    assert _run(monkeypatch, tmp_path, "r2", "bump") == 3
    state = json.loads((tmp_path / "runs" / "r2" / "iteration_state.json").read_text())
    assert state["status"] == "exhausted"


def test_survives_reload(monkeypatch, tmp_path):
    _run(monkeypatch, tmp_path, "r3", "reset")
    _run(monkeypatch, tmp_path, "r3", "bump")
    # simulate a fresh process: load() reads from disk
    monkeypatch.setattr(rs, "ROOT", tmp_path)
    assert rs.load("r3")["iteration"] == 1
