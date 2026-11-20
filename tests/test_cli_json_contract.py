"""CLI contract checks on generated NPZ fixtures (not measured modal data)."""
import json
import sys

import numpy as np
import pytest

from modalbridge import cli


def _fixture_pair(tmp_path):
    ids = np.array(["P01|X", "P02|Y", "P03|Z"])
    reference = np.array([[1 + 1j], [2 - 1j], [0.5 + 2j]])
    ref = tmp_path / "reference.npz"
    candidate = tmp_path / "candidate.npz"
    np.savez(ref, frequency=np.array([50.0]), shapes=reference, dof_ids=ids)
    np.savez(
        candidate,
        frequency=np.array([50.0]),
        shapes=(2 - 3j) * reference,
        dof_ids=ids,
    )
    return ref, candidate


def test_cli_writes_machine_readable_matching_contract(tmp_path, monkeypatch, capsys):
    reference, candidate = _fixture_pair(tmp_path)
    output = tmp_path / "results.json"
    monkeypatch.setattr(
        sys, "argv",
        ["modalbridge", str(reference), str(candidate), "--output", str(output)],
    )
    cli.main()
    assert capsys.readouterr().out.strip() == str(output)
    report = json.loads(output.read_text(encoding="utf-8"))
    assert set(report) == {"pairs", "common_dofs", "mac"}
    assert report["common_dofs"] == ["P01|X", "P02|Y", "P03|Z"]
    assert len(report["pairs"]) == 1
    assert report["pairs"][0]["candidate"] == 0
    assert report["pairs"][0]["status"] == "matched"
    assert report["mac"][0][0] == pytest.approx(1.0)


def test_cli_rejects_nonfinite_threshold_without_writing_report(
    tmp_path, monkeypatch
):
    reference, candidate = _fixture_pair(tmp_path)
    output = tmp_path / "invalid.json"
    monkeypatch.setattr(
        sys, "argv",
        [
            "modalbridge", str(reference), str(candidate),
            "--min-mac", "nan", "--output", str(output),
        ],
    )
    with pytest.raises(ValueError, match="invalid matching parameters"):
        cli.main()
    assert not output.exists()


def test_cli_version_matches_public_package(monkeypatch, capsys):
    from modalbridge import __version__

    monkeypatch.setattr(sys, "argv", ["modalbridge", "--version"])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out
