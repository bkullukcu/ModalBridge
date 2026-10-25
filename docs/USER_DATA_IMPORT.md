# Importing response and modal vectors

ModalBridge compares complex shapes on aligned physical degrees of freedom (DOFs). Every input channel identifies a physical point and measurement direction. The `quantity_kind` field distinguishes resonance-response vectors (`resonance_response`) from independently identified mode shapes (`identified_mode`).

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

The resulting NPZ files are compatible with `load_modes()`: `frequency` (candidate), complex `shapes` (physical DOF, candidate) and `dof_ids` (physical point and direction). Additional arrays record candidate IDs, frame, physical quantity and optional sensor positions in metres. Each `*.npz.manifest.json` records input and output hashes.

## CSV schema

Each CSV row describes one candidate × physical point × direction. Map `candidate`, `point`, `direction`, `frequency`, `real`, `imag` and optionally x/y/z coordinates. Direction takes `X`, `Y` or `Z` in a declared common reference frame. For example, point `P03` measured along Y receives the DOF ID `P03|Y`.

Choose `quantity_kind` (`resonance_response` or `identified_mode`) from the measurement and analysis procedure. Also declare `reference_frame`, `frequency_unit` (`Hz`/`kHz`), `response_unit` and `coordinate_unit` (`m`, `mm` or `not_available`). For each candidate, supply a complete set of DOFs with consistent frequencies and finite, nonzero response vectors.

## NumPy input

NPZ arrays are `frequency` (M), `shapes` (D, M) complex, `dof_ids` (D) as `physical-point|X/Y/Z`, `mode_ids` (M) and optionally `coordinates` (D, 3). The JSON schema supplies the corresponding physical units and reference frame. Use numerical and string arrays.

```python
from modalbridge.user_data import convert, audit_pair
convert('own_modes.csv', 'own_schema.json', 'own_modes.npz')
print(audit_pair('reference.npz', 'own_modes.npz', tolerance_m=1e-4))
```

## Coordinate and direction alignment

The `audit-inputs` command checks declared reference frames, shared physical DOF identifiers and available coordinates using the requested tolerance. Prepare a common coordinate frame and measurement directions before import. For data with channel identifiers and absent measured coordinates, the audit records the coordinate verification status as `not verified`.

## Magnitude/phase exports

For linear magnitude/phase CSVs, set `"complex_format": "magnitude_phase"` and map the `magnitude` and `phase` columns. Declare `phase_unit` (`degree` or `radian`), `phase_sign` (`1` or `-1`) and `phase_reference`. The importer applies the recorded phase convention. NPZ shapes are complex-valued by default; `allow_real_only: true` handles deliberately real-valued inputs.

The bundled generated NPZ fixtures `examples/step3_user_data/reference_numpy.npz` and `candidate_numpy.npz` can be converted using `examples/step3_user_data/schema.json`.
