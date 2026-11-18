"""Known-truth synthetic correspondence benchmark for manuscript review.

No experimental dataset is generated or inferred. Run with:
    python examples/reviewer_benchmark.py --output review_output --seeds 40
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

from modalbridge import ModeSet, align_dofs, complex_mac, match_modes

METHODS = ("modalbridge", "nearest_frequency", "greedy_mac", "hungarian_forced")
NOISE_LEVELS = (0.0, 0.35, 0.80)  # Added complex-noise norm / noise-free shape norm
FREQUENCIES_HZ = np.array([40.0, 53.0, 70.0, 71.0, 86.0, 104.0])
MISSING_REFERENCE = 4


def make_case(seed: int, noise_level: float, dofs: int = 32):
    """Synthetic complex unit vectors; NOT identified physical eigenmodes.

    Complex Gaussian random columns are orthonormalized via QR. Five true
    candidates undergo independent complex Gaussian perturbations and random
    global phase rotations. The sixth reference has no true counterpart.
    One deliberately correlated but physically unrelated distractor is placed
    near the missing mode: its nominal MAC is 0.72, thus it passes the 0.60
    eligibility gate despite having no true correspondence. A second independent
    distractor is placed near the 70/71-Hz pair. Candidate order is permuted.
    """
    if dofs < len(FREQUENCIES_HZ) or not np.isfinite(noise_level) or noise_level < 0:
        raise ValueError("dofs >= 6 and finite nonnegative noise_level required")
    rng = np.random.default_rng(seed)
    n = len(FREQUENCIES_HZ)
    z = (rng.standard_normal((dofs, n)) + 1j * rng.standard_normal((dofs, n))) / np.sqrt(2)
    reference_shapes = np.linalg.qr(z)[0]
    retained = [i for i in range(n) if i != MISSING_REFERENCE]
    shapes, freqs, origins = [], [], []
    for i in retained:
        eps = (rng.standard_normal(dofs) + 1j * rng.standard_normal(dofs)) / np.sqrt(2 * dofs)
        phase = np.exp(1j * rng.uniform(-np.pi, np.pi))
        shapes.append((reference_shapes[:, i] + noise_level * eps) * phase)
        freqs.append(FREQUENCIES_HZ[i] * (1 + rng.normal(0, 0.008)))
        origins.append(i)
    for distractor_number, frequency in enumerate((86.2, 70.6)):
        z = (rng.standard_normal(dofs) + 1j * rng.standard_normal(dofs)) / np.sqrt(2)
        if distractor_number == 0:
            # Orthonormal projection makes MAC exactly 0.72 before rounding.
            missing_shape = reference_shapes[:, MISSING_REFERENCE]
            z -= missing_shape * np.vdot(missing_shape, z)
            z /= np.linalg.norm(z)
            z = np.sqrt(0.72) * missing_shape + np.sqrt(0.28) * z
        else:
            z /= np.linalg.norm(z)
        shapes.append(z)
        freqs.append(frequency)
        origins.append(None)
    permutation = rng.permutation(len(shapes))
    candidate = ModeSet(np.asarray(freqs)[permutation], np.column_stack(shapes)[:, permutation], tuple(range(dofs)))
    reference = ModeSet(FREQUENCIES_HZ, reference_shapes, tuple(range(dofs)))
    origin_to_candidate = {orig: j for j, orig in enumerate(np.asarray(origins, dtype=object)[permutation]) if orig is not None}
    truth = [origin_to_candidate.get(i) for i in range(n)]
    return reference, candidate, truth


def forced_assignments(reference: ModeSet, candidate: ModeSet, method: str, frequency_weight: float = 0.2):
    """Full-coverage naive baselines. All use the same paired DOFs and inputs.

    For these six-reference/seven-candidate examples every reference is forced
    to receive a candidate. A greedy algorithm enforces one-to-one assignments.
    """
    x, y, _ = align_dofs(reference, candidate)
    mac = complex_mac(x, y)
    delta = np.abs(reference.frequency[:, None] - candidate.frequency[None, :]) / reference.frequency[:, None]
    if method == "nearest_frequency":
        loss = delta
    elif method == "greedy_mac":
        loss = 1 - mac
    elif method == "hungarian_forced":
        loss = 1 - mac + frequency_weight * delta
    else:
        raise ValueError("unknown forced baseline")
    n, m = loss.shape
    if n > m:
        raise ValueError("forced baseline requires candidates >= references")
    if method == "hungarian_forced":
        rows, cols = linear_sum_assignment(loss)
        result = [None] * n
        for i, j in zip(rows, cols):
            result[int(i)] = int(j)
        return result
    result = [None] * n
    available_rows, available_cols = set(range(n)), set(range(m))
    while available_rows:
        i, j = min(((i, j) for i in available_rows for j in available_cols),
                   key=lambda ij: (loss[ij], ij[0], ij[1]))
        result[i] = int(j)
        available_rows.remove(i)
        available_cols.remove(j)
    return result


def score(predicted, truth):
    """Selective classification with an explicitly absent true counterpart."""
    if len(predicted) != len(truth) or not truth:
        raise ValueError("nonempty aligned predicted and truth labels required")
    tp = sum(p is not None and p == t for p, t in zip(predicted, truth))
    fp = sum(p is not None and p != t for p, t in zip(predicted, truth))
    tn = sum(p is None and t is None for p, t in zip(predicted, truth))
    fn = sum(p is None and t is not None for p, t in zip(predicted, truth))
    accepted = tp + fp
    return dict(correct_acceptances=tp, false_acceptances=fp, correct_rejections=tn,
                false_rejections=fn, coverage=accepted / len(truth),
                error_among_accepted=fp / accepted if accepted else None,
                correct_rejection_rate=tn / sum(t is None for t in truth),
                correct_acceptance_rate=tp / sum(t is not None for t in truth))


def evaluate(seed, noise, min_mac=0.6, max_relative_shift=0.2,
             frequency_weight=0.2, unmatched_cost=0.6):
    reference, candidate, truth = make_case(seed, noise)
    kwargs = dict(min_mac=min_mac, max_relative_shift=max_relative_shift,
                  frequency_weight=frequency_weight, unmatched_cost=unmatched_cost)
    modalbridge = [p["candidate"] for p in match_modes(reference, candidate, **kwargs)["pairs"]]
    result = {}
    for method in METHODS:
        prediction = modalbridge if method == "modalbridge" else forced_assignments(reference, candidate, method, frequency_weight)
        result[method] = score(prediction, truth)
    return result


def aggregate(rows, group_cols):
    """Sample SD across seeds; no confidence-interval or probability claims."""
    groups = {}
    for row in rows:
        key = tuple(row[c] for c in group_cols)
        groups.setdefault(key, []).append(row)
    out = []
    metrics = ("coverage", "error_among_accepted", "correct_acceptances", "false_acceptances",
               "correct_rejections", "false_rejections")
    for key, records in sorted(groups.items()):
        item = dict(zip(group_cols, key))
        item["runs"] = len(records)
        for metric in metrics:
            values = np.asarray([r[metric] for r in records if r[metric] is not None], float)
            item[metric + "_mean"] = float(values.mean()) if len(values) else None
            item[metric + "_sd"] = float(values.std(ddof=1)) if len(values) > 1 else None
            item[metric + "_defined_runs"] = int(len(values))
        out.append(item)
    return out


def write_csv(path, rows):
    if not rows:
        raise ValueError("no rows to export")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run(output: Path, seeds=40):
    if seeds < 2:
        raise ValueError("at least two seeds required for sample SD")
    output.mkdir(parents=True, exist_ok=True)
    results = []
    sensitivity = []
    for noise in NOISE_LEVELS:
        for seed in range(seeds):
            for method, metrics in evaluate(seed, noise).items():
                results.append(dict(seed=seed, noise_norm=noise, method=method, **metrics))
            # Every operating point is evaluated on the exact same realizations.
            for mac_gate in (0.4, 0.6, 0.8):
                for dummy in (0.2, 0.4, 0.6):
                    reference, candidate, truth = make_case(seed, noise)
                    prediction = [p["candidate"] for p in match_modes(
                        reference, candidate, min_mac=mac_gate,
                        max_relative_shift=0.2, frequency_weight=0.2,
                        unmatched_cost=dummy)["pairs"]]
                    sensitivity.append(dict(seed=seed, noise_norm=noise, min_mac=mac_gate,
                                            unmatched_cost=dummy, **score(prediction, truth)))
    write_csv(output / "per_seed.csv", results)
    write_csv(output / "summary.csv", aggregate(results, ("noise_norm", "method")))
    write_csv(output / "sensitivity_per_seed.csv", sensitivity)
    write_csv(output / "sensitivity_summary.csv", aggregate(sensitivity, ("noise_norm", "min_mac", "unmatched_cost")))
    manifest = dict(data_type="synthetic complex random vectors; not empirical/FE modes",
                    seeds=seeds, noise_norms=NOISE_LEVELS, reference_frequencies_hz=FREQUENCIES_HZ.tolist(),
                    reference_modes=len(FREQUENCIES_HZ), dofs=32, missing_reference=MISSING_REFERENCE,
                    distractor_frequencies_hz=[86.2, 70.6], correlated_distractor_nominal_mac=0.72, baseline_definition={
                        "nearest_frequency":"greedy one-to-one ascending relative frequency shift; forced coverage",
                        "greedy_mac":"greedy one-to-one descending complex MAC; forced coverage",
                        "hungarian_forced":"optimal one-to-one 1-MAC+0.2*relative_shift; forced coverage",
                        "modalbridge":"package match_modes with eligibility gates and private dummy columns"},
                    default_parameters=dict(min_mac=0.6, max_relative_shift=0.2,
                                            frequency_weight=0.2, unmatched_cost=0.6, ambiguity_margin=0.05),
                    frequency_noise="independent Gaussian relative SD 0.008 for true candidates; none for distractors",
                    complex_noise="CN(0, I/dofs), scaled by noise_norm times unit-norm reference shape",
                    global_phase="independent exp(i*Uniform(-pi,pi)) for each true candidate",
                    metrics="conditional error among accepted excludes abstentions; report coverage alongside")
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return results, sensitivity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("review_output"))
    parser.add_argument("--seeds", type=int, default=40)
    args = parser.parse_args()
    run(args.output, seeds=args.seeds)
    print(f"Synthetic benchmark CSVs and manifest: {args.output}")


if __name__ == "__main__":
    main()
