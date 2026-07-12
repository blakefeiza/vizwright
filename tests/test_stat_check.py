import numpy as np
import pandas as pd
import stat_check as sc


def test_two_proportion_no_difference():
    r = sc.two_proportion(50, 100, 50, 100, 0.05)
    assert r["significant"] is False
    assert abs(r["z"]) < 1e-6


def test_two_proportion_clear_difference():
    r = sc.two_proportion(90, 100, 10, 100, 0.05)
    assert r["significant"] is True
    assert r["z"] > 0  # A rate higher than B


def test_compare_groups_identical_not_significant():
    rng = np.random.default_rng(1)
    vals = rng.normal(10, 2, 200)
    df = pd.DataFrame({"v": np.concatenate([vals, vals]),
                       "g": ["A"] * 200 + ["B"] * 200})
    r = sc.compare_groups(df, "v", "g", 0.05)
    assert r["any_significant"] is False
    assert r["comparisons"][0]["effect"] == "negligible"


def test_compare_groups_clear_separation():
    rng = np.random.default_rng(2)
    a = rng.normal(100, 5, 100)
    b = rng.normal(50, 5, 100)
    df = pd.DataFrame({"v": np.concatenate([a, b]), "g": ["A"] * 100 + ["B"] * 100})
    r = sc.compare_groups(df, "v", "g", 0.05)
    c = r["comparisons"][0]
    assert c["significant"] is True
    assert c["effect"] == "large"
    # Bonferroni never makes a p-value smaller than the raw
    assert c["p_bonferroni"] >= c["p_raw"]


def test_bonferroni_family_size():
    rng = np.random.default_rng(3)
    df = pd.DataFrame({"v": rng.normal(0, 1, 300),
                       "g": (["A"] * 100 + ["B"] * 100 + ["C"] * 100)})
    r = sc.compare_groups(df, "v", "g", 0.05)
    assert r["family_size"] == 3  # 3 groups -> 3 pairwise comparisons


def test_effect_label_thresholds():
    assert sc.effect_label(0.1) == "negligible"
    assert sc.effect_label(0.3) == "small"
    assert sc.effect_label(0.6) == "medium"
    assert sc.effect_label(1.2) == "large"
