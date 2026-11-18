"""Reduced-support modal audit regression; no experimental accuracy claims."""
import csv
import importlib.util
from pathlib import Path
import numpy as np
import pytest


PATH = Path(__file__).resolve().parents[1] / "examples" / "reviewer_plate_audit.py"
spec = importlib.util.spec_from_file_location("reviewer_plate_audit", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def make_npz(tmp_path):
    x = np.eye(8, 3, dtype=complex)
    a = tmp_path/"a.npz"
    b = tmp_path/"b.npz"
    values = dict(frequency=np.array([40., 70., 100.]),
                  shapes=x, dof_ids=np.arange(8))
    np.savez(a, **values)
    np.savez(b, **values)
    return a, b


def test_complete_audit_and_automac(tmp_path):
    a,b=make_npz(tmp_path)
    rows=module.audit(a,b,tmp_path/"out",bootstrap_repeats=10)
    assert len(rows)==3
    assert all(z["status"]=="matched" for z in rows)
    assert all(z["reason"]=="selected" for z in rows)
    matrix=np.loadtxt(tmp_path/"out"/"automac_reference.csv",delimiter=",")
    np.testing.assert_allclose(matrix,np.eye(3))
    with (tmp_path/"out"/"plate_eight_reference_audit.csv").open() as f:
        assert len(list(csv.DictReader(f)))==3


def test_subspace_self_similarity_and_bad_indices(tmp_path):
    a,b=make_npz(tmp_path)
    ss=module.compare_subspace(a,b,[0,1],[0,1])
    assert ss["minimum_squared_cosine"] == pytest.approx(1)
    with pytest.raises(ValueError):
        module.compare_subspace(a,b,[0,0],[0,1])


def test_gating_rejection_is_not_physical_absence():
    assert module.rejection_cause(np.array([.4]),np.array([.01])) == (
        "no candidate passes MAC gate"
    )
    assert module.rejection_cause(np.array([.9]),np.array([.3])) == (
        "no candidate passes frequency gate"
    )
