# Research notes

This repository contains only synthetic test and import fixtures. The ETH Zürich impact recordings, FLOOD measurements, complex FRF arrays and derived experimental result tables are not redistributed. Independent reproduction of reported study results requires the original sources and their processing settings.

ModalBridge requires matching physical degrees of freedom. Similar vectors on apparently corresponding channel indices need not represent the same point or direction. A matched resonance-response vector is not necessarily an identified eigenmode. MAC and frequency checks support correspondence assessment but cannot establish physical mode identity by themselves.

A known-truth synthetic matching demonstration is available:

```bash
python examples/reproduce.py --output example_output
```

Its expected permutation is defined in code; the resulting agreement does not establish experimental mode-tracking accuracy.
