"""Source-traceable real-data ablations for reviewer validation.

Supply original data paths; no third-party measurements are bundled here.
Outputs are correspondence selections and agreement with provider labels,
NOT independently verified physical-mode accuracy.

python examples/reviewer_real_data.py --plate-reference /data/without_modes.npz \
  --plate-candidate /data/with_modes.npz --eth-mac /results/mac_matrices.csv \
  --eth-peaks /results/peak_frequencies.csv \
  --flood-data /data/CableStayedBridge_SHM_features_2026-03-27_2026-04-10.csv \
  --flood-mapping /data/CableStayedBridge_sensor_channel_mapping.csv \
  --flood-dictionary /data/CableStayedBridge_SHM_features_data_dictionary.csv \
  --output /results/real_ablation
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from modalbridge.core import ModeSet, align_dofs, complex_mac, match_modes
from modalbridge.external_shm import (
    load_flood_shab, modal_snapshot, matched_snapshot_pairs
)

BASELINES = ("nearest_frequency", "greedy_mac", "hungarian_no_rejection")
DUMMY_COSTS = (0.2, 0.4, 0.6)


def assignments(mac, delta, method, dummy_cost=0.6):
    """Same pairwise support for every method within a comparison.

    Non-rejection baselines are limited by unequal set cardinalities. The
    FLOOD adapter's 0.7/0.3 cost is distinct from the package's core cost.
    """
    mac, delta = np.asarray(mac, float), np.asarray(delta, float)
    if mac.ndim != 2 or mac.shape != delta.shape or not mac.shape[0]:
        raise ValueError("nonempty equal score matrices required")
    n, m = mac.shape
    eligible = np.isfinite(mac) & np.isfinite(delta)
    if method in ("modalbridge", "legacy_flood"):
        gated = eligible & (mac >= 0.6) & (delta <= 0.2)
        if method == "modalbridge":
            loss = 1 - mac + 0.2 * delta
            dummy = dummy_cost
        else:
            loss = 0.7 * (1 - mac) + 0.3 * (delta / 0.2)
            dummy = 0.6
        full = np.full((n, m+n), 1e6)
        full[:, :m] = np.where(gated, loss, 1e6)
        full[np.arange(n), m+np.arange(n)] = dummy
        rr, cc = linear_sum_assignment(full)
        output = [None]*n
        for i, j in zip(rr, cc):
            if j < m and gated[i, j] and loss[i, j] < dummy:
                output[int(i)] = int(j)
        return output
    if method == "nearest_frequency":
        loss = np.where(eligible, delta, 1e6)
    elif method == "greedy_mac":
        loss = np.where(eligible, 1-mac, 1e6)
    elif method == "hungarian_no_rejection":
        loss = np.where(eligible, 1-mac+0.2*delta, 1e6)
    else:
        raise ValueError("unsupported method")
    output = [None]*n
    if not m:
        return output
    if method == "hungarian_no_rejection":
        rr, cc = linear_sum_assignment(loss)
        for i, j in zip(rr, cc):
            if loss[i, j] < 1e6:
                output[int(i)] = int(j)
        return output
    remaining_rows = set(range(n))
    remaining_cols = set(range(m))
    while remaining_rows and remaining_cols:
        i, j = min(((i, j) for i in remaining_rows for j in remaining_cols),
                   key=lambda pair: (loss[pair], pair[0], pair[1]))
        if loss[i, j] >= 1e6:
            break
        output[i] = int(j)
        remaining_rows.remove(i)
        remaining_cols.remove(j)
    return output


def pair_scores(left, right, min_shared=3):
    """FLOOD's pair-dependent common-channel MAC, not the fixed-DOF core API."""
    aa, bb = sorted(left), sorted(right)
    mac = np.full((len(aa), len(bb)), np.nan)
    delta = np.full_like(mac, np.nan)
    for i, a in enumerate(aa):
        for j, b in enumerate(bb):
            channels = sorted(set(left[a]["shape"]) & set(right[b]["shape"]))
            if len(channels) < min_shared:
                continue
            x = np.asarray([left[a]["shape"][c] for c in channels], complex)
            y = np.asarray([right[b]["shape"][c] for c in channels], complex)
            denom = np.vdot(x, x).real * np.vdot(y, y).real
            if not np.isfinite(denom) or denom <= 0:
                continue
            mac[i, j] = np.clip(abs(np.vdot(x, y))**2 / denom, 0, 1)
            delta[i, j] = abs(left[a]["frequency"] - right[b]["frequency"]) / left[a]["frequency"]
    return aa, bb, mac, delta


def rejection_reason(mac_row, delta_row, result, dummy):
    if result is not None:
        return "accepted"
    permitted = np.isfinite(mac_row) & np.isfinite(delta_row)
    mac_ok = permitted & (mac_row >= 0.6)
    freq_ok = permitted & (delta_row <= 0.2)
    valid = mac_ok & freq_ok
    if not valid.any():
        if not mac_ok.any() and not freq_ok.any():
            return "both_gates_or_no_common_channels"
        if not mac_ok.any():
            return "mac_gate"
        if not freq_ok.any():
            return "frequency_gate"
        return "no_pair_passes_both_gates"
    cost = 1 - mac_row[valid] + 0.2 * delta_row[valid]
    if cost.min() >= dummy:
        return "dummy_cheaper_than_eligible_candidates"
    return "one_to_one_competition"


def add(rows, dataset, context, a, b, mac, delta, method, dummy, chosen):
    for i, j in enumerate(chosen):
        rows.append({
            "dataset": dataset, "comparison": context, "method": method,
            "dummy_cost": dummy, "reference": str(a[i]),
            "candidate": str(b[j]) if j is not None else None,
            "selected_mac": float(mac[i, j]) if j is not None else None,
            "relative_shift": float(delta[i, j]) if j is not None else None,
            "provider_label_agreement": (
                bool(a[i] == b[j]) if j is not None and dataset == "FLOOD-SHAB" else None
            ),
            "rejection_reason": (
                rejection_reason(mac[i], delta[i], j, dummy)
                if method == "modalbridge" else
                ("accepted" if j is not None else "cardinality_or_no_valid_candidate")
            ),
        })


def evaluate_case(rows, name, context, refs, cands, mac, delta, legacy=False):
    for method in BASELINES:
        add(rows, name, context, refs, cands, mac, delta, method, None,
            assignments(mac, delta, method))
    if legacy:
        add(rows, name, context, refs, cands, mac, delta, "legacy_flood", 0.6,
            assignments(mac, delta, "legacy_flood"))
    for dummy in DUMMY_COSTS:
        add(rows, name, context, refs, cands, mac, delta, "modalbridge", dummy,
            assignments(mac, delta, "modalbridge", dummy))


def replay_plate(refpath, candpath, rows):
    def read(path):
        with np.load(path, allow_pickle=False) as data:
            return ModeSet(data["frequency"], data["shapes"], tuple(data["dof_ids"]))
    a, b = read(refpath), read(candpath)
    x, y, ids = align_dofs(a, b)
    mac = complex_mac(x, y)
    delta = abs(a.frequency[:, None] - b.frequency[None, :]) / a.frequency[:, None]
    evaluate_case(rows, "PLATE", "motor absent-to-present",
                  range(len(a.frequency)), range(len(b.frequency)), mac, delta)
    for dummy in DUMMY_COSTS:
        core = [p["candidate"] for p in match_modes(a, b, unmatched_cost=dummy)["pairs"]]
        if core != assignments(mac, delta, "modalbridge", dummy):
            raise AssertionError("plate scores do not reproduce package core")
    return {"common_dofs": len(ids), "reference_modes": len(a.frequency),
            "candidate_modes": len(b.frequency),
            "provenance": "historical processed complex vectors; NOT original time-record replay"}


def replay_eth(macpath, peakpath, rows):
    measured = pd.read_csv(macpath)
    peaks = pd.read_csv(peakpath)
    # The dataset labels bands as '1.25-2.1 Hz' etc, not integer mode IDs.
    peaks["ordinal_band"] = peaks.groupby(["sensor", "test"]).cumcount()+1
    freq = {(r.sensor, int(r.test), int(r.ordinal_band)): float(r.frequency_hz)
            for r in peaks.itertuples()}
    contexts = []
    for (sensor, baseline, damaged), g in measured.groupby(
            ["sensor", "baseline_test", "damaged_test"]):
        aa = sorted(int(v) for v in g.reference_band.unique())
        bb = sorted(int(v) for v in g.candidate_band.unique())
        mac = np.full((len(aa), len(bb)), np.nan)
        for r in g.itertuples():
            mac[aa.index(int(r.reference_band)), bb.index(int(r.candidate_band))] = float(r.mac)
        if not np.isfinite(mac).all():
            raise ValueError("ETH complex MAC matrix incomplete")
        fref = np.array([freq[sensor, int(baseline), i] for i in aa])
        fcand = np.array([freq[sensor, int(damaged), i] for i in bb])
        delta = abs(fref[:, None] - fcand[None, :]) / fref[:, None]
        context = f"{sensor}:{baseline}->{damaged}"
        contexts.append(context)
        evaluate_case(rows, "ETH", context, aa, bb, mac, delta)
    return {"same_layout_comparisons": len(contexts), "contexts": contexts,
            "provenance": "MAC and peaks recomputed from original ETH archives; resonance-response vectors, not poles"}


def replay_flood(data, mapping, dictionary, rows):
    wide = pd.read_csv(data)
    mp = pd.read_csv(mapping)
    dd = pd.read_csv(dictionary)
    if "VariableName" not in dd:
        raise ValueError("FLOOD data dictionary missing VariableName")
    dynamic = set(mp.loc[mp.SensorGroup.astype(str).str.contains(
        "Dynamic", case=False), "ChannelID"])
    present = {k.split("phi_mode_01_")[1][:-5] for k in wide
               if k.startswith("phi_mode_01_") and k.endswith("_real")}
    if not dynamic.issubset(present):
        raise ValueError("FLOOD channel mapping not compatible with input fields")
    long = load_flood_shab(data)
    ts = pd.to_datetime(wide.timestamp, dayfirst=True)
    good = set(pd.to_datetime(long.timestamp, dayfirst=True).unique())
    times = sorted(t for t in ts.unique() if t in good)
    labels = dict(zip(ts, wide.timestamp))
    cache = {t: modal_snapshot(long, labels[t]) for t in times}
    usable = 0
    skipped = 0
    legacy_refs = legacy_accept = 0
    changed = 0
    for a0, b0 in zip(times[:-1], times[1:]):
        if (b0-a0)/np.timedelta64(1, "m") > 60:
            skipped += 1
            continue
        left, right = cache[a0], cache[b0]
        aa, bb, mac, delta = pair_scores(left, right)
        historical = matched_snapshot_pairs(left, right)
        reconstructed = assignments(mac, delta, "legacy_flood")
        target = [bb.index(p["candidate"]) if p["candidate"] is not None else None
                  for p in historical]
        if reconstructed != target:
            raise AssertionError("historical FLOOD adapter did not reproduce")
        legacy_refs += len(aa)
        legacy_accept += sum(j is not None for j in reconstructed)
        new = assignments(mac, delta, "modalbridge", 0.6)
        changed += sum(a != b for a, b in zip(reconstructed, new))
        usable += 1
        evaluate_case(rows, "FLOOD-SHAB", f"{a0}->{b0}",
                      aa, bb, mac, delta, legacy=True)
    return {
        "records": len(wide), "valid_times": len(times), "usable_pairs": usable,
        "skipped_gaps": skipped, "historical_references": legacy_refs,
        "historical_accepted": legacy_accept, "changed_legacy_vs_core_rows": changed,
        "dynamic_channel_count": len(dynamic),
        "provenance": "original CSV + mapping + dictionary; provider tracking labels are NOT ground truth",
    }


def save_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run(args):
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    rows, inputs, findings = [], {}, {}
    if args.plate_reference and args.plate_candidate:
        findings["PLATE"] = replay_plate(args.plate_reference, args.plate_candidate, rows)
        inputs.update(plate_reference=args.plate_reference, plate_candidate=args.plate_candidate)
    if args.eth_mac and args.eth_peaks:
        findings["ETH"] = replay_eth(args.eth_mac, args.eth_peaks, rows)
        inputs.update(eth_mac=args.eth_mac, eth_peaks=args.eth_peaks)
    if args.flood_data and args.flood_mapping and args.flood_dictionary:
        findings["FLOOD-SHAB"] = replay_flood(
            args.flood_data, args.flood_mapping, args.flood_dictionary, rows)
        inputs.update(flood_data=args.flood_data, flood_mapping=args.flood_mapping,
                      flood_dictionary=args.flood_dictionary)
    if not rows:
        raise ValueError("supply a complete plate, ETH or FLOOD input group")
    frame = pd.DataFrame(rows)
    summaries = []
    for (dataset, method, dummy), g in frame.groupby(
            ["dataset", "method", "dummy_cost"], dropna=False):
        accepted = g[g.candidate.notna()]
        matches = accepted.provider_label_agreement.dropna()
        summaries.append({
            "dataset": dataset, "method": method, "dummy_cost": dummy,
            "reference_count": len(g), "accepted_count": len(accepted),
            "coverage": len(accepted)/len(g),
            "provider_label_agreement": float(matches.mean()) if len(matches) else None,
            "selected_mac_median": float(accepted.selected_mac.median()) if len(accepted) else None,
        })
    save_csv(output/"per_reference_decisions.csv", rows)
    save_csv(output/"method_summary.csv", summaries)
    manifest = {"evidence": findings,
                "input_sha256": {key: hashlib.sha256(Path(value).read_bytes()).hexdigest()
                                 for key, value in inputs.items()},
                "limitations": [
                    "No independent empirical modal-identity ground truth.",
                    "Forced baselines can be cardinality-limited; that is NOT explicit rejection.",
                    "FLOOD MAC supports may differ between candidate pairs.",
                    "Historical FLOOD adapter cost differs from ModalBridge package core.",
                    "No parameter is calibrated on held-out physically validated structures.",
                ]}
    (output/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    return summaries, findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("plate-reference", "plate-candidate", "eth-mac", "eth-peaks",
                 "flood-data", "flood-mapping", "flood-dictionary"):
        parser.add_argument("--"+name, type=Path)
    parser.add_argument("--output", type=Path, required=True)
    summaries, findings = run(parser.parse_args())
    print(json.dumps({"summary": summaries, "findings": findings}, indent=2))


if __name__ == "__main__":
    main()
