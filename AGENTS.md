# AGENTS.md — ModalBridge

Auditable complex vibration-response and mode-shape matching.

Read `README.md`, `ROADMAP.md`, `docs/RESEARCH_NOTES.md`, `docs/AI_DISCLOSURE.md`, `pyproject.toml` and relevant source/tests before editing.

## Autonomous development rules
1. Check open issues, PRs and `main` before choosing one narrowly scoped, verifiable task. Do not duplicate an active PR.
2. Change code and corresponding tests in a feature branch; open a draft PR to `main`. Never push to `main`, automatically merge, enable auto-merge or publish a release.
3. Prefer reproducible numerical tests, explicit input contracts, and stable user-facing APIs. Justify backward-incompatible changes before proposing them.
4. Never fabricate measurements, listeners, uncertainty estimates, acceptance thresholds, benchmark outcomes, citations or DOI records.
5. Identify AI-assisted changes in the PR and document assumptions and limitations. Keep examples and synthetic fixtures distinguishable from empirical data.
6. Preserve original data rights: no confidential, restricted or third-party measurements in public commits.

## Required verification
```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python examples/quickstart.py
python -m build
python -m twine check dist/*
```

Run available checks and report only observed results. GitHub Actions validates the supported Python/OS matrix. If CI fails, diagnose the code rather than relaxing the tests. Use `tests/test_public_contract.py` to protect release metadata and syntax.

## Scientific invariants
- Align DOFs by physical point and direction in one coordinate frame; row positions alone are not identifiers.
- Distinguish resonance response shapes from independently identified eigenmodes throughout import, matching and reporting.
- Test complex MAC phase/scaling invariance and numerical bounds, including zero-energy cases.
- Preserve explicit admissibility, ambiguity and unmatched outcomes; assignment frequency is not posterior probability.
- Reject ambiguous instrument units or unverified coordinate transformations instead of inventing metadata.
## PR acceptance checklist
- Provide problem statement and reproducible failure or clear docs/metadata rationale.
- Add focused regression tests for substantive changes.
- Report tests executed, missing checks, and CI state, including any unverified external datasets.
- Do not silently modify citation, license, file schemas, algorithms, audio calibration claims, or scientific metrics.
- Leave the final merge decision to the maintainer.
