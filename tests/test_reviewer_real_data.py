"""Numerical tests of the real-data reviewer ablation, with synthetic fixtures only.

These tests do not establish physically correct modal correspondence.
"""
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT = Path(__file__).resolve().parents[1] / "examples" / "reviewer_real_data.py"
spec = importlib.util.spec_from_file_location("reviewer_real_data", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_correlated_distractor_abstention_depends_on_dummy():
    mac = np.array([[0.72]])
    delta = np.zeros((1, 1))
    assert module.assignments(mac, delta, "modalbridge", 0.2) == [None]
    assert module.assignments(mac, delta, "modalbridge", 0.6) == [0]
    assert module.rejection_reason(mac[0], delta[0], None, 0.2) == (
        "dummy_cheaper_than_eligible_candidates"
    )


def test_forced_baselines_are_cardinality_limited():
    mac = np.eye(3, 2)
    delta = np.zeros_like(mac)
    for name in module.BASELINES:
        pairs = module.assignments(mac, delta, name)
        assert len(pairs) == 3 and sum(p is None for p in pairs) == 1


def test_flood_pair_scores_use_shared_channels():
    left = {1: {"frequency": 40.0, "shape": {"x": 1j, "y": 1, "z": 1}}}
    right = {
        2: {"frequency": 40.2, "shape": {"x": 1j, "y": 1, "z": 1}},
        3: {"frequency": 40.0, "shape": {"x": 1j, "y": 1}},
    }
    aa, bb, mac, delta = module.pair_scores(left, right)
    assert aa == [1] and bb == [2, 3]
    np.testing.assert_allclose(mac[0, 0], 1)
    assert np.isnan(mac[0, 1]) and np.isnan(delta[0, 1])


def test_eth_band_names_are_not_integer_mode_labels(tmp_path):
    peaks = []
    macrows = []
    for test in (14, 15):
        for label, frequency in (("1.2-2 Hz", 1.7), ("3-5 Hz", 4.2)):
            peaks.append({
                "sensor": "dmm", "test": test, "band": label,
                "frequency_hz": frequency * (0.99 if test == 15 else 1)
            })
    for i in (1, 2):
        for j in (1, 2):
            macrows.append({
                "sensor": "dmm", "baseline_test": 14, "damaged_test": 15,
                "reference_band": i, "candidate_band": j,
                "mac": 0.99 if i == j else 0.01
            })
    p1, p2 = tmp_path / "peaks.csv", tmp_path / "mac.csv"
    pd.DataFrame(peaks).to_csv(p1, index=False)
    pd.DataFrame(macrows).to_csv(p2, index=False)
    rows = []
    manifest = module.replay_eth(p2, p1, rows)
    assert manifest["same_layout_comparisons"] == 1
    assert len([r for r in rows if r["method"] == "modalbridge"]) == 6


def test_plate_scores_match_original_match_modes(tmp_path):
    x = np.eye(6, 3, dtype=complex)
    record = {"frequency": np.array([40., 70., 100.]),
              "shapes": x, "dof_ids": np.arange(6)}
    a, b = tmp_path / "a.npz", tmp_path / "b.npz"
    np.savez(a, **record)
    np.savez(b, **record)
    rows = []
    assert module.replay_plate(a, b, rows)["common_dofs"] == 6
    assert sum(r["candidate"] is not None for r in rows
               if r["method"] == "modalbridge" and r["dummy_cost"] == 0.6) == 3
