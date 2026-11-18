# SoftwareX SOFTX-D-26-01552: revision status matrix

Status: **work in progress**, not a completed referee response or a claim that all objections have been addressed.

| Review topic | What this branch implements | What is still necessary |
|---|---|---|
| Same-realization simple baselines (R1–R4) | Nearest-frequency, greedy-MAC, forced Hungarian vs package matcher on seeded synthetic vectors | Comparison to published implementations and to the real experiments |
| Close modes, missing/spurious candidates, noise and phase (R1–R4) | Six-reference known-truth task, 70/71-Hz pair, missing 86-Hz counterpart, correlated false candidate, 40 seeds and three complex-noise levels | FE or analytically physical model with documented modal truth |
| Coverage obscuring false rejection (R1–R4) | Four confusion counts, coverage and conditional error, sample mean/SD and complete per-seed CSV | Journal figures and statistical interpretation with independent data |
| Threshold sensitivity and dummy cost (R2–R4) | MAC gate/dummy-cost grid, frequency gate/beta/sparse-DOF grid; direct documented upper bound of 0.44 | Selection of physically defensible, independently calibrated operating points |
| Exact rejection matrix (R2–R3) | Full n-by-(m+n) matrix and dummy-column logic documented | Confirm algorithm choice with authors; do not silently change public defaults |
| Plate: registration/FRFs and DOF availability (R1, R4) | Data requirements identified, no invented measurements | Recover source FRFs, coordinates, figures, hardware and settings; re-run and report |
| Bridge / four-storey independent validation (R2–R4) | Clear distinction between dataset labels and truth | New experiments or independent correspondence evidence |
| Measurement direction transforms (R1) | Explicitly warns coordinate registration does not rotate sensor vectors | Implement/test physical vector transforms for relevant sensors if supported by metadata |
| Related software (R3) | Baseline definitions; no unverified claims | Read primary papers and test against maintained pyFBS/pyOMA/commercial functionality |
| Reproducibility capsule (R3) | Exact commands and JSON manifest, two focused test modules | Archive experimental data/scripts with permission and pin software release |
| Computational cost (R4) | Hardware/platform-recorded timing microbenchmark with mode/DOF sizes | Repeat across declared platforms and interpret distribution |

Publication action: do not transfer the rejected manuscript unchanged. After empirical data are assembled and validation reviewed, update each claim in the paper to match results that can actually be regenerated.