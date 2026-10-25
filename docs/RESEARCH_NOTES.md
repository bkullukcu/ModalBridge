# Research notes

The bundled fixtures contain generated response vectors for deterministic tests. For experimental reproduction, obtain the ETH Zürich or FLOOD records from their source archives and preserve the measurement metadata and processing settings.

Physical DOF alignment uses position and measurement direction, followed by complex MAC and frequency-based matching. The `quantity_kind` metadata distinguishes resonance-response vectors from independently identified eigenmodes. Interpret matching results with the experiment-specific modal analysis.

A known-truth synthetic matching demonstration is available:

```bash
python examples/reproduce.py --output example_output
```

The expected permutation is defined in the example code and checked by the automated tests.
