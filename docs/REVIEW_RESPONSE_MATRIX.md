# Referee-revision audit, SOFTX-D-26-01552

18 November 2026. This is a scientific-evidence inventory, not an editor's acceptance or a declaration of completed experimental validation.

| Requirement | Reproducible implementation / supporting analysis | Status |
|---|---|---|
| Known-truth synthetic close/missing/spurious modes | `examples/reviewer_benchmark.py`; per-seed counts, full coverage/error tables | Implemented |
| Matching baselines on identical inputs | `examples/reviewer_benchmark.py`, `examples/reviewer_real_data.py`; greedy frequency, greedy MAC, forced Hungarian | Implemented on synthetic/processed features; no external package head-to-head |
| Threshold, DOF, beta and dummy-cost grids | `examples/reviewer_benchmark.py`, `examples/reviewer_scaling.py` | Implemented; no physical calibration |
| Exact assignment matrix and default rejection bound | `docs/REVIEW_VALIDATION.md`; isolated eligible pair cost <=0.44 versus dummy 0.6 | Verified mathematically |
| Full plate decisions, 21-DOF AutoMAC and 70.5/74.5-Hz subspace | `examples/reviewer_plate_audit.py`; reviewer revision package | Implemented from historical processed vectors; not original raw impact replay |
| Lab plate geometry, physical registration and input force provenance | See [issue #5](https://github.com/bkullukcu/ModalBridge/issues/5) | Outstanding |
| Explicit rotation/LOS input contracts | `src/modalbridge/sensor_frames.py` and `docs/SENSOR_FRAMES.md` | Implemented; original instrument orientations unverified |
| FLOOD source replay and historical-versus-core cost discrepancy | `examples/reviewer_real_data.py`, `docs/REAL_DATA_VALIDATION.md` | Source reanalysis executed; provider labels not physical truth |
| ETH source replay (piezo, DMM, impacts) and condition comparison | `docs/REAL_DATA_VALIDATION.md` and original-source replay report | Source reanalysis executed; mode identity unverified |
| Computational timing, environment and test matrix | `examples/reviewer_scaling.py`, GitHub Actions | Implemented; single-machine microbenchmark |
| Related software positioning | Related-work notes in revised manuscript; pyFBS and pyOMA original documentation | Text comparison implemented; comparative deployment outstanding |
| Complete referee responses | Editable author-review response letter in revision package | Draft; authors must check statements and missing data |
| Final archive, new Code Ocean capsule and new DOI | No new version minted automatically | Outstanding: only after acceptance of exact new source |

## Evidence boundaries

* A 0.6 MAC gate, 20% frequency gate and 0.6 dummy cost do not independently reject a single eligible high-MAC distractor. The 0.2 dummy threshold observed in synthetic tests is not a universal optimum.
* The original FLOOD adapter uses `0.7*(1-MAC)+0.3*(delta/0.2)`, not the public core `1-MAC+0.2*delta`. Their apparent equal coverage hides different decisions and provider-label agreement.
* The legacy plate matching operates on only seven position-consistent labels (21 scalar DOFs); a naive all-label match does not establish trustworthy physical registration.
* The ETH comparison is resonance-response matching at predefined bands, not independent identification of poles or structural damage location.
* The August 2026 test-stand report was velocity-only, whereas the October analysis mentions force-referenced processing. Its exact source lineage must be reconciled before claims about coherence, H1 estimates, or instrumentation are made.

Related tasks and data gaps: [issue #5](https://github.com/bkullukcu/ModalBridge/issues/5).

No public release, scientific interpretation change, schema breaking change or merge into `main` is authorised by these audit entries.
