"""Complete reduced-support plate correspondence audit from processed vectors.

The supplied files must be original/reproduced 21-DOF complex response vectors.
This does not recover or invent unprovided raw impact records or spatial maps.
Example:
  python examples/reviewer_plate_audit.py --reference without_modes.npz \\
    --candidate with_modes.npz --output review_plate
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from scipy.linalg import subspace_angles
from modalbridge import ModeSet, complex_mac, match_modes, assignment_stability
from modalbridge.audit import global_assignment_margins


def read_modes(path):
    with np.load(path, allow_pickle=False) as z:
        return ModeSet(z["frequency"], z["shapes"], tuple(z["dof_ids"]))


def rejection_cause(mac_row, shift_row, dummy_cost=0.6,
                    min_mac=0.6, max_relative_shift=0.2, frequency_weight=0.2):
    """Return the first demonstrable gate or optimizer reason, not physical absence."""
    mac_good = mac_row >= min_mac
    freq_good = shift_row <= max_relative_shift
    eligible = mac_good & freq_good
    if not eligible.any():
        if not mac_good.any():
            return "no candidate passes MAC gate"
        if not freq_good.any():
            return "no candidate passes frequency gate"
        return "no candidate passes both gates"
    if np.min(1-mac_row[eligible]+frequency_weight*shift_row[eligible]) >= dummy_cost:
        return "dummy preferred"
    return "global assignment competition"


def audit(reference, candidate, output, seed=2026, bootstrap_repeats=300):
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    a, b = read_modes(reference), read_modes(candidate)
    result = match_modes(a, b)
    margins = global_assignment_margins(a, b)
    stability = assignment_stability(a, b, seed=seed, n_boot=bootstrap_repeats)
    # AutoMAC uses a single physical support per configuration.
    np.savetxt(out/"automac_reference.csv", complex_mac(a.shapes, a.shapes), delimiter=",")
    np.savetxt(out/"automac_candidate.csv", complex_mac(b.shapes, b.shapes), delimiter=",")
    rows = []
    for p, g in zip(result["pairs"], margins):
        i, j = p["reference"], p["candidate"]
        rows.append(dict(
            reference=i, reference_frequency_hz=float(a.frequency[i]),
            candidate="" if j is None else j,
            candidate_frequency_hz="" if j is None else float(b.frequency[j]),
            status=p["status"], mac="" if j is None else float(result["mac"][i, j]),
            relative_frequency_shift="" if j is None else float(result["relative_shift"][i, j]),
            cost=float(p["cost"]), row_margin="" if p["margin"] is None else float(p["margin"]),
            global_margin="" if j is None else float(g["global_gap"]),
            dof_resampling_frequency=float(stability["frequency"][i, -1 if j is None else j]),
            reason="selected" if j is not None else rejection_cause(
                result["mac"][i], result["relative_shift"][i]),
        ))
    with (out/"plate_eight_reference_audit.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    # Do not assume the 70/74-Hz columns exist in an arbitrary experiment.
    # The caller selects the tested near-frequency pair by reference indices.
    return rows


def compare_subspace(reference, candidate, reference_columns, candidate_columns):
    a, b = read_modes(reference), read_modes(candidate)
    i = np.asarray(reference_columns, dtype=int)
    j = np.asarray(candidate_columns, dtype=int)
    if len(i) != len(j) or len(i) < 1 or len(set(i)) != len(i) or len(set(j)) != len(j):
        raise ValueError("equal-length unique column selections required")
    if not all(0 <= k < a.shapes.shape[1] for k in i) or not all(
            0 <= k < b.shapes.shape[1] for k in j):
        raise ValueError("column index outside mode set")
    if tuple(a.dof_ids) != tuple(b.dof_ids):
        raise ValueError("DOFs must be aligned in one physical coordinate frame")
    angle = subspace_angles(a.shapes[:, i], b.shapes[:, j])
    return dict(reference_columns=i.tolist(), candidate_columns=j.tolist(),
                principal_angles_degrees=np.rad2deg(angle).tolist(),
                minimum_squared_cosine=float(np.min(np.cos(angle)**2)),
                interpretation="response subspace consistency; not physical mode truth")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bootstrap-repeats", type=int, default=300)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--near-reference", nargs=2, type=int, default=None)
    parser.add_argument("--near-candidate", nargs=2, type=int, default=None)
    args = parser.parse_args()
    audit(args.reference, args.candidate, args.output, args.seed, args.bootstrap_repeats)
    if args.near_reference is not None and args.near_candidate is not None:
        (args.output/"subspace.json").write_text(
            json.dumps(compare_subspace(
                args.reference, args.candidate, args.near_reference, args.near_candidate
            ),indent=2)+"\\n",encoding="utf-8")
    print("Plate audit written to",args.output)


if __name__ == "__main__":
    main()
