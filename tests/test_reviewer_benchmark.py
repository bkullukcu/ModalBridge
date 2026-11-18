"""Regression contracts for independent-truth reviewer benchmark."""
import importlib.util
from pathlib import Path
import numpy as np
from modalbridge import ModeSet, match_modes

SCRIPT = Path(__file__).resolve().parents[1] / "examples" / "reviewer_benchmark.py"
spec = importlib.util.spec_from_file_location("reviewer_benchmark", SCRIPT)
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)


def test_missing_truth_and_phase_invariance():
    a, b, truth = benchmark.make_case(seed=7, noise_level=0.0)
    assert len(truth) == 6 and truth.count(None) == 1
    assert len({j for j in truth if j is not None}) == 5
    result = match_modes(a, b)
    predicted = [p["candidate"] for p in result["pairs"]]
    assert all(predicted[i] == truth[i] for i in range(6) if truth[i] is not None)
    # Default dummy cost is too permissive to reject the high-MAC distractor.
    assert predicted[benchmark.MISSING_REFERENCE] is not None
    assert match_modes(a, b, unmatched_cost=0.2)["pairs"][benchmark.MISSING_REFERENCE]["candidate"] is None


def test_score_does_not_hide_false_rejections():
    outcome = benchmark.score([0, None, 2, None], [0, 1, None, None])
    assert outcome["correct_acceptances"] == 1
    assert outcome["false_acceptances"] == 1
    assert outcome["correct_rejections"] == 1
    assert outcome["false_rejections"] == 1
    assert outcome["coverage"] == 0.5
    assert outcome["error_among_accepted"] == 0.5


def test_dummy_cost_can_abstain_even_when_pair_passes_gates():
    a = ModeSet([40], np.array([[1], [0], [0]], complex), (0, 1, 2))
    b = ModeSet([40], np.array([[np.sqrt(0.7)], [np.sqrt(0.3)], [0]], complex), (0, 1, 2))
    assert match_modes(a, b, unmatched_cost=0.2)["pairs"][0]["candidate"] is None
    assert match_modes(a, b, unmatched_cost=0.6)["pairs"][0]["candidate"] == 0


def test_forced_baselines_and_reproducibility():
    a, b, truth = benchmark.make_case(seed=13, noise_level=0.15)
    for name in benchmark.METHODS[1:]:
        pairs = benchmark.forced_assignments(a, b, name)
        assert len(set(pairs)) == len(a.frequency)
    assert benchmark.make_case(13, 0.15)[2] == truth
    assert benchmark.evaluate(13, 0.15) == benchmark.evaluate(13, 0.15)


def test_exports_mean_and_scatter(tmp_path):
    rows, sens = benchmark.run(tmp_path, seeds=3)
    assert len(rows) == 3 * 3 * 4
    assert len(sens) == 3 * 3 * 3 * 3
    for filename in ("per_seed.csv", "summary.csv", "sensitivity_per_seed.csv",
                     "sensitivity_summary.csv", "manifest.json"):
        assert (tmp_path / filename).is_file()
