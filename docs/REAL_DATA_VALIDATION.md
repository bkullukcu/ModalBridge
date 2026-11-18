# Real measured-data validation for SoftwareX referee response

**Evidence status, 18 November 2026:** The analysis below was executed in a separate working container against previously supplied sources. The GitHub checkout contains scripts and synthetic tests, **not** restricted or third-party original measurements. Source-level replays, their file hashes, and derived CSV outputs are retained in the author's working revision bundle. The new scripts are not part of archived v0.9.2; freeze a new version/DOI after review.

## Reproducibility commands

Install \`pip install -e ".[dev,external]"\`. Provide the input paths explicitly:

\`\`\`bash
python examples/reviewer_real_data.py \
  --plate-reference /data/without_modes.npz \
  --plate-candidate /data/with_modes.npz \
  --eth-mac /results/eth/mac_matrices.csv \
  --eth-peaks /results/eth/peak_frequencies.csv \
  --flood-data /data/CableStayedBridge_SHM_features_2026-03-27_2026-04-10.csv \
  --flood-mapping /data/CableStayedBridge_sensor_channel_mapping.csv \
  --flood-dictionary /data/CableStayedBridge_SHM_features_data_dictionary.csv \
  --output /results/reviewer_real_data
\`\`\`

For the ETH source-data preprocessing (separate from the above processed-MAC ablation), use the *historical author-revision* \`examples/analyze_ethzurich_real.py\` with the three original archives \`DMM.zip\`, \`Piezoelectric Accelerometers.zip\` and \`Phase1of2_Impacts.zip\`. The historical author code and exact archive hashes must be kept alongside that replay; the public package's maintained \`modalbridge.ethzurich\` API is the preprocessing dependency. The existing historical \`examples/analyze_flood_real.py\` recomputes the adapter's legacy aggregate results from the original FLOOD CSV and dictionaries.

## Source-level checks performed

- FLOOD source CSV: **718 source rows**, **660 valid times**, **653 record pairs** no more than 60 min apart, **6 gaps skipped**, **4,414 reference candidates**. Reprocessing reproduced **3,923 accepted / 491 unmatched**, accepted median complex MAC **0.9964607857** and **98.7255%** agreement with *provider* tracking labels under the historical FLOOD adapter.
- ETH original ZIP SHA-256:
  - \`DMM.zip\`: \`87f3962934964f140a042150c61aac0731997a0cd8344370f17ca1a710508e29\`
  - \`Piezoelectric Accelerometers.zip\`: \`f158e1dec690d17b92c8b51eb9493320d869be44c117347be0db0f25d3789b4b\`
  - \`Phase1of2_Impacts.zip\`: \`42ac154495682981834bf7e4bb8477bd0cedd0418388fb6f28e16b08028dfc73\`
  - Recomputed healthy/damaged median peak changes: piezo **-1.60, -1.98, -1.58, -1.38%**; optical DMM **-1.79, -1.66, -1.36, -1.31%**. DMM Tests 14/15 common-layout MAC diagonals: **0.958, 0.943, 0.921, 0.826**.
  - Piezoelectric base \`Gy/Gx\` RMS was approximately **115** for Tests 11/12 and approximately **1.12–1.14** for Tests 13–17; the scale anomaly must be retained as a source-data quality limitation.
- Plate: historical motor-present/absent processed complex vectors had **21 common DOFs from 7 coordinate-consistent point labels out of 45 shared labels**, and exactly **8** reference and **8** candidate response peaks. This latest pass reused historical processed \`.npz\` vectors rather than replaying the original force and velocity time histories.

## Exact method comparison, same reference candidates in each dataset

| Dataset / method | Selected / references | Coverage | Provider-label agreement among selected |
|---|---:|---:|---:|
| PLATE, core dummy=0.2 | 4/8 | 50.00% | not independently known |
| PLATE, core dummy=0.4 | 6/8 | 75.00% | not independently known |
| PLATE, core dummy=0.6 | 6/8 | 75.00% | not independently known |
| ETH, core dummy=0.2 | 45/48 | 93.75% | not independently known |
| ETH, core dummy=0.4 or 0.6 | 48/48 | 100.00% | not independently known |
| FLOOD, nearest-frequency (greedy) | 4,097/4,414 | 92.82% | 94.65% |
| FLOOD, greedy complex MAC | 4,097/4,414 | 92.82% | 93.48% |
| FLOOD, Hungarian without rejection | 4,097/4,414 | 92.82% | 93.36% |
| FLOOD, *historical adapter* | 3,923/4,414 | 88.88% | 98.73% |
| FLOOD, *core cost*, dummy=0.6 | 3,923/4,414 | 88.88% | 98.27% |
| FLOOD, *core cost*, dummy=0.4 | 3,922/4,414 | 88.85% | 98.27% |
| FLOOD, *core cost*, dummy=0.2 | 3,864/4,414 | 87.54% | 98.89% |

**Key methodological distinction:** The historical FLOOD adapter used \`0.7*(1-MAC) + 0.3*delta/0.2\`, whereas \`modalbridge.core.match_modes\` uses \`1-MAC + 0.2*delta\`. Both have the same admissibility gates and dummy cost 0.6 for this comparison. Even though both select **3,923** references, **22 row decisions differ**. The 98.73% provider-label agreement is for the **historical adapter only**, not for the core function. The core-cost result uses pairwise intersected channels on FLOOD, whereas the strict public \`ModeSet\` API requires one fixed common DOF support. This is an analytical cost-function ablation, not a literal call to \`match_modes\` on missing-channel sets.

The 317 unassigned references in forced FLOOD baselines are due to insufficient candidate cardinality or unavailable finite scores, and **not** intentionally rejected pairs. Do not call the baselines' greater coverage superior without acknowledging unsupported correspondences.

## Outstanding scientific issues

1. No plate raw time-record replay, motor geometry/support description or independently validated physical registration has been completed in this branch; the old processed \`.npz\` inputs are only an intermediate reproducibility level.
2. ETH peak-band IDs and FLOOD provider labels are not independently known physical modal correspondences. The high agreement numbers cannot be redefined as true accuracy or false-match probabilities.
3. FLOOD candidate pairs may be compared on different channel intersections. A strict fixed-support sensitivity study (and direction/orientation audit) is necessary before attributing differences only to assignment logic.
4. A principled threshold selection method requires independent truth, held-out calibration, or a stated asymmetric cost model. Dummy cost 0.2 is **not** a verified universal optimum.
5. A head-to-head comparison with independently maintained mode-tracking implementations and a repeated scan experiment are still open.

No software performance or experimental identity claim should be inferred beyond these executed checks.
