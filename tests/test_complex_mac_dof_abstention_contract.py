"""Synthetic contracts for complex MAC, physical DOFs, and abstention.

Fixtures are algebraic checks, not experimental modal-identification evidence.
"""
import numpy as np
import pytest

from modalbridge.core import ModeSet, align_dofs, complex_mac, match_modes


def test_complex_mac_preserves_phase_and_independent_complex_scaling():
    a = np.array([[1 + 2j, 0j], [2 - 1j, 1j], [0.5j, 2 + 0j]])
    b = a * np.array([2 - 3j, -1 + 4j])[None, :]
    np.testing.assert_allclose(
        complex_mac(a, b), complex_mac(a, a), rtol=1e-12, atol=1e-12
    )
    np.testing.assert_allclose(np.diag(complex_mac(a, b)), 1.0, atol=1e-12)


def test_weighted_complex_mac_rejects_zero_energy_on_selected_dofs():
    a = np.array([[1j], [0j], [0j]])
    b = np.array([[1 + 0j], [1j], [0j]])
    with pytest.raises(ValueError, match="zero weighted shape energy"):
        complex_mac(a, b, weights=[0.0, 1.0, 0.0])


def test_alignment_uses_physical_ids_not_row_order():
    ids = ("P01|X", "P01|Y", "P02|X", "P03|Z")
    a = ModeSet([40.0], np.array([[1j], [2], [3j], [4]]), ids)
    permutation = [3, 1, 0, 2]
    b = ModeSet([40.0], a.shapes[permutation], tuple(ids[i] for i in permutation))
    aligned_a, aligned_b, common = align_dofs(a, b)
    assert set(common) == set(ids)
    np.testing.assert_array_equal(aligned_a, aligned_b)
    assert match_modes(a, b)["pairs"][0]["status"] == "matched"


def test_frequency_gate_rejects_even_perfect_complex_shape():
    ids = ("P01|X", "P02|Y", "P03|Z")
    shape = np.array([[1 + 1j], [2 - 1j], [3j]])
    a = ModeSet([40.0], shape, ids)
    b = ModeSet([80.0], (2j) * shape, ids)
    result = match_modes(a, b, max_relative_shift=0.2)
    assert result["mac"][0, 0] == pytest.approx(1.0)
    assert result["pairs"][0]["candidate"] is None
    assert result["pairs"][0]["status"] == "unmatched"


def test_equal_cost_candidates_are_flagged_ambiguous_not_confident():
    ids = ("P01|X", "P02|Y", "P03|Z")
    shape = np.array([[1j], [2], [3j]])
    a = ModeSet([50.0], shape, ids)
    b = ModeSet([50.0, 50.0], np.column_stack([shape[:, 0], shape[:, 0]]), ids)
    pair = match_modes(a, b)["pairs"][0]
    assert pair["candidate"] in (0, 1)
    assert pair["status"] == "ambiguous"
    assert pair["margin"] == pytest.approx(0.0)
