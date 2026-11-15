# ModalBridge — development roadmap

Priorities are proposals, not validated experimental results.

## P0: Robust matching and metadata
- Enforce citation/version/README DOI consistency and Python source syntax via CI.
- Expand tests for reordered, mismatched and duplicate physical DOFs, directions and coordinate frames.
- Maintain complex MAC phase invariance and tests for zero-energy, non-finite and near-tied response vectors.
- Test frequency gating, ambiguity and intentional abstention on known synthetic assignments.

## P1: Statistical and physical validity
- Examine sensitivity to matching thresholds and relative frequency shifts with deterministic reference examples.
- Document spatial correlation assumptions of DOF-resampling stability metrics.
- Separate measured resonance-response matching from modal identification claims in reports.

## P2: Public interface and interoperability
- Improve import audits for instrument exports with provenance of quantities, units and reference frames.
- Add machine-readable reports for thresholds, common DOFs, rejected candidates and unmatched references.
- Keep CLI/API compatibility and document schema changes.

## Acceptance criteria
Every matching change needs a known-truth synthetic test and a stated physical assumption. Never fabricate instrument data, mode identification evidence, or benchmark statistics.
