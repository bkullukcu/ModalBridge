# Importing measured response and modal vectors

ModalBridge matches **explicitly aligned physical DOFs**, not vectors that merely share row indices. An impact-derived response vector is a **resonance response**, not necessarily a structural eigenmode. The input schema retains this distinction.

## Quick start

```bash
python -m pip install -e .
modalbridge convert examples/step3_user_data/reference.csv \
  --schema examples/step3_user_data/schema.json --output ref.npz
modalbridge convert examples/step3_user_data/candidate.csv \
  --schema examples/step3_user_data/schema.json --output cand.npz
modalbridge audit-inputs ref.npz cand.npz --tolerance-m 0.0001
modalbridge ref.npz cand.npz --output matches.json
```

Outputs are compatible with the original `load_modes()` API: `frequency` (candidate), complex `shapes` (physical DOF, candidate), `dof_ids` (physical point + direction). Additional arrays describe mode candidate IDs, coordinate reference frame, physical quantity and optional sensor positions in metres. Sidecar files `*.npz.manifest.json` contain raw/mapping/output SHA-256 values.

## CSV schema

Each row is one **candidate × physical point × response direction**. Map `candidate`, `point`, `direction`, `frequency`, `real`, `imag`; optionally x/y/z positions (all or none). `direction` must be one of X/Y/Z, **in a common declared reference frame**. ID `P03|Y` is generated from point `P03` and direction `Y`, which prevents comparing X and Y displacement/velocity by accident.

Declare `quantity_kind` as `identified_mode` **only if independently identified**; otherwise `resonance_response`. Also supply `reference_frame`, `frequency_unit` (`Hz`/`kHz`), `response_unit` and `coordinate_unit` (`m`, `mm` or `not_available`). At a given candidate frequency, frequency values must agree across all DOFs and every candidate must cover all DOFs. Response vectors with zero norm are rejected.

## NumPy input

NPZ arrays: `frequency` (M), `shapes` (D,M) complex, `dof_ids` (D) explicitly `physical-point|X/Y/Z`, `mode_ids` (M); optional `coordinates` (D,3). The JSON schema remains mandatory because a numeric array alone cannot establish frame, physical meaning or units. No pickle/object arrays are accepted.

```python
from modalbridge.user_data import convert, audit_pair
convert('own_modes.csv', 'own_schema.json', 'own_modes.npz')
print(audit_pair('reference.npz', 'own_modes.npz', tolerance_m=1e-4))
```

## Physical-coordinate checks

`audit-inputs` refuses different reference-frame labels, insufficient common physical DOFs, coordinates on only one side, or contradictory positions for common IDs. It does **not** geometrically register datasets, rotate complex vector components, infer fiducial correspondences or prove eigenmode identity. If no coordinates were measured on either side, it labels them as **not verified** rather than claiming agreement. A passing audit is necessary, not sufficient, for physical identity. Later MAC and frequency matches are mathematical correspondences conditional on the data supplied.

## Magnitude/phase exports

Measured **linear** magnitude and phase CSVs may use `"complex_format": "magnitude_phase"` with `magnitude` and `phase` column mappings plus explicit `phase_unit` (`degree`/`radian`), `phase_sign` (`1`/`-1`) and `phase_reference`. These declarations prevent tacit reversal of complex phase. NumPy `shapes` must have complex dtype unless `allow_real_only: true` is explicitly declared; missing phases must not silently become zero.

Preformatted synthetic NumPy input examples are available as `examples/step3_user_data/reference_numpy.npz` and `candidate_numpy.npz` and can be passed to the same `modalbridge convert` command with the example `schema.json`.
