# ModalBridge

**Comparing complex vibration-response shapes across structural configurations.**

ModalBridge matches frequency-associated response vectors using shared physical degrees of freedom (DOFs), complex modal assurance criterion (MAC) and frequency constraints. It can reject an ambiguous or implausible correspondence instead of forcing every reference candidate to match.

Measured resonance-response vectors are not automatically identified eigenmodes. The interpretation of each comparison depends on the measurement setup, DOF registration and modal identification method.

Version `v0.9.2` is a research preview; interfaces may change.

## Install

Python 3.10 or newer:

```bash
python -m pip install -e .
python examples/quickstart.py
```

The quickstart uses a known synthetic permutation of complex vectors. To run tests:

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
```

## Compare your own data

Each response vector must refer to a defined physical point and measurement direction. CSV and NPZ importers use a JSON schema to record response type, units and coordinate reference frame.

```bash
modalbridge convert examples/step3_user_data/reference.csv \
  --schema examples/step3_user_data/schema.json --output reference.npz
modalbridge convert examples/step3_user_data/candidate.csv \
  --schema examples/step3_user_data/schema.json --output candidate.npz

modalbridge audit-inputs reference.npz candidate.npz --tolerance-m 0.0001
modalbridge reference.npz candidate.npz --output matches.json
```

Run the audit before matching. It compares the declared frame, shared DOF identifiers and available coordinates; it does not estimate a rigid registration or prove that two modes have the same physical identity. The input formats and phase conventions are detailed in [the import guide](docs/USER_DATA_IMPORT.md).

## Interpretation and validation

Complex MAC measures similarity between vectors on the same ordered physical DOFs. A large MAC value is not proof of matching eigenmodes when measurement configurations or sensor positions differ. Frequency proximity alone is also insufficient. Report rejected candidates and any unverified coordinate assumptions.

The original ETH Zürich impact records, derived FRFs and experimental result tables are not part of this repository. The self-contained tests use synthetic cases. See [research notes](docs/RESEARCH_NOTES.md).

## Repository contents

- `src/modalbridge/` — matching, auditing, registration and input conversion
- `examples/` — known-truth example and CSV/NPZ import fixtures
- `tests/` — unit and regression tests
- `docs/` — import details and scientific constraints

## Citation and license

Software citation metadata is in [CITATION.cff](CITATION.cff). Cite underlying experimental datasets separately. Code is supplied under the MIT license, subject to institutional authorization before a public release. Independent physical mode identification remains an essential part of experimental validation.
