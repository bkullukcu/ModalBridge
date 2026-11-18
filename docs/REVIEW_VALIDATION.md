# Reviewer-driven validation supplement (synthetic evidence)

## Scope and reproducibility

These executable studies address the SoftwareX review of SOFTX-D-26-01552. Benchmark vectors are **synthetic complex random response patterns**, not finite-element eigenvectors or experimental modes. A correct synthetic label is not proof of physical modal identity.

From a checkout with `pip install -e '.[dev]'`:

```bash
python -m pytest -q tests/test_reviewer_benchmark.py tests/test_reviewer_scaling.py
python examples/reviewer_benchmark.py --output review_output --seeds 40
python examples/reviewer_scaling.py --output review_output --seeds 40 --repeats 5
```

Files: `manifest.json`, `per_seed.csv`, `summary.csv`, `sensitivity_per_seed.csv`, `sensitivity_summary.csv`, `dof_frequency_sensitivity.csv`, `timing.csv`, and `environment.json`. The summary reports mean and sample standard deviation over random seeds. Time measurements are *illustrative* and must be reported with their execution environment.

## Independent synthetic ground truth

- Six reference vectors of 32 complex DOFs, drawn as QR-orthonormalized circular complex Gaussian vectors. Frequencies: 40, 53, 70, 71, 86 and 104 Hz. The 70/71-Hz pair is intentionally close.
- Exactly five true counterparts, one intentionally missing reference (index 4 at 86 Hz), and two spurious distractor candidates. Candidate columns and their ground-truth indices are jointly permuted.
- Each true candidate has global phase `exp(i U[-pi,pi])`, additive complex Gaussian vector noise `CN(0,noise_norm² I/32)` with nominal norm ratios 0, 0.35 or 0.80, and independent Gaussian relative frequency error with standard deviation 0.008.
- One distractor near 86.2 Hz has a deliberately correlated complex response with squared projection (nominal MAC) 0.72 against the **missing** reference, though by construction no physical counterpart exists. Another 70.6-Hz distractor is independently generated and normalized.
- Seeds 0–39 change all random vector shapes, measurement perturbations, phases and candidate permutations. Every method uses the *same realization* for a given seed/noise setting.
- Sparse-DOF extension repeats the synthetic experiment at 8, 16, and 32 DOFs, two noise levels, three relative-frequency gates (0.03, 0.05, 0.2), and three frequency weights (0, 0.2, 0.6) with a fixed dummy cost 0.4. This explores sensitivity, not a realistic sensor placement optimization.

## Baselines, metrics and limitations

All methods align the same physical DOFs and compare the same reference/candidate arrays. The three baselines deliberately force one-to-one full coverage: `nearest_frequency` is greedy ascending relative frequency difference; `greedy_mac` is greedy descending complex MAC; `hungarian_forced` globally minimizes `1-MAC + 0.2*relative_shift` *without dummy alternatives*. These precisely defined simple comparator implementations are **not** evidence of relative performance against pyFBS, pyOMA or commercial software.

For each reference, truth is a unique candidate index or `None`. The outputs separate: correct acceptances, false acceptances, correct rejections of genuinely missing counterparts, and false rejections of genuinely present counterparts. Coverage is the fraction assigned a candidate; error among accepted is the false-acceptance count divided by all accepted pairs. When coverage is zero, conditional error is undefined and exported as a blank cell. A selective error rate must **never** be reported without coverage and the false-rejection count.

## Exact assignment matrix and critical bound

The implementation calculates `C_ij = 1-MAC_ij + beta * |f_i-g_j|/f_i`. Pairs failing either MAC gate or relative-frequency gate are ineligible. For `n` reference and `m` candidate vectors, SciPy solves a `n x (m+n)` matrix. Eligible candidate columns retain their real costs; ineligible pairs receive a large penalty. Each reference has its own private dummy column at `m+i` with `unmatched_cost`; all *other* dummy columns in that row receive a large penalty. The solver minimizes total assignment cost. The `ambiguous` status describes a *selected* pair with low row-local margin, not a rejected pair.

Under the defaults (`min_mac=0.6`, `max_relative_shift=0.2`, `frequency_weight=0.2`, `unmatched_cost=0.6`), each eligible real pair costs at most `1-0.6+0.2*0.2 = 0.44`. Therefore an **isolated eligible** pair cannot be rejected by the dummy penalty alone. Defaults abstain through eligibility gates or competition/global assignment; this is not independently calibrated rejection. The 0.72-MAC spurious candidate is intentionally chosen to expose the limitation. The sensitivity experiment varies MAC gates 0.4/0.6/0.8 and dummy costs 0.2/0.4/0.6. Do not present any resulting setting as an experimentally calibrated optimum.

Weights in weighted complex MAC default to identity (equal nonnegative per-DOF weights) unless explicitly supplied; global complex phase and scalar amplitude do not alter MAC. Application-specific weights should be justified by sensor uncertainty/quality and spatial coverage, not tuned retrospectively to achieve high agreement with the same matching labels.

## Coordinate, measurement and interpretation boundaries

- Existing `rigid_registration` fits **coordinates** from at least three non-collinear trusted 3D fiducials and reports residuals. It does **not** automatically rotate response vectors or verify sensor frames.
- Scanning LDV line-of-sight velocity, oblique uniaxial sensor output and local-frame triaxial components must be physically projected/rotated to a common basis before creating comparable `ModeSet` vectors; a coordinate-only transform does not do that.
- Resonance-peak forced-response shapes need not equal independently identified eigenmodes, and may depend on excitation point and on mode overlap. MAC and frequency proximity do not establish physical identity independently.
- Assignment frequencies under DOF bootstrap are diagnostic sensitivities, not calibrated posterior probabilities; spatial correlation is ignored.

## Experimental work not supplied by this benchmark

**Plate:** specimen geometry and support, added component's mass/stiffness/location, registration trace, excitation and vibrometer details, sampling/averaging/windowing, FRFs, available coherence, spatial RMS and peak selection, 45 labels versus seven physically consistent points, AutoMAC and full/filtered shape maps. Re-run all baselines and coordinate/registration ablations, report every pair's cost/margin/rejection gate, and test subspace diagnostics of the 70.5/74.5-Hz pair.

**Bridge:** original complex inputs/metadata, accepted/rejected distributions (MAC, frequency and thresholds), complete parameter configs, and *independent* validation. Agreement with provider tracking labels is **not** independently verified accuracy.

**Four-storey:** raw or identified response data, declared measurement units and sensor quantities, frequencies and shifts for all candidates, independently checkable correspondence and missing cases.

A separate analysis against existing mode-tracking software is also still needed. Do **not** invent experimental FRFs, coherence, coordinates, hardware specifications or performance gains when data are unavailable.