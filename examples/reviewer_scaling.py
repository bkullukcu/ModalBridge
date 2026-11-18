"""Complementary sparse-DOF/gate study and transparent timing microbenchmark.

Scientific performance results require reporting the execution environment.
"""
from __future__ import annotations
import argparse
import csv
import json
import platform
import sys
from pathlib import Path
from time import perf_counter

import numpy as np
from modalbridge import ModeSet, match_modes
from reviewer_benchmark import make_case, score


def write(path, rows):
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run(out: Path, seeds: int = 40, repeats: int = 5):
    if seeds < 1 or repeats < 1:
        raise ValueError('positive seeds and repeats required')
    out.mkdir(parents=True, exist_ok=True)
    rows=[]
    for dofs in (8, 16, 32):
        for noise in (0.35, 0.80):
            for seed in range(seeds):
                reference, candidate, truth = make_case(seed, noise, dofs)
                for frequency_gate in (0.03, 0.05, 0.2):
                    for beta in (0.0, 0.2, 0.6):
                        predicted = [p['candidate'] for p in match_modes(
                            reference, candidate, min_mac=0.6,
                            max_relative_shift=frequency_gate,
                            frequency_weight=beta, unmatched_cost=0.4)['pairs']]
                        rows.append(dict(dofs=dofs, noise_norm=noise, seed=seed,
                                         max_relative_shift=frequency_gate, frequency_weight=beta,
                                         **score(predicted,truth)))
    write(out/'dof_frequency_sensitivity.csv',rows)
    timing=[]
    for modes in (4, 8, 16, 32):
        for dofs in (32, 64, 128):
            rng=np.random.default_rng(12345+modes*100+dofs)
            x=rng.standard_normal((dofs,modes))+1j*rng.standard_normal((dofs,modes))
            y=x[:,rng.permutation(modes)] + 0.02*(rng.standard_normal((dofs,modes))+1j*rng.standard_normal((dofs,modes)))
            freq=np.linspace(30,110,modes)
            reference=ModeSet(freq,x,tuple(range(dofs)))
            candidate=ModeSet(freq,y,tuple(range(dofs)))
            match_modes(reference,candidate)  # warm-up
            for rep in range(repeats):
                start=perf_counter()
                match_modes(reference,candidate)
                timing.append(dict(modes=modes,dofs=dofs,repeat=rep,
                                   elapsed_ms=(perf_counter()-start)*1000))
    write(out/'timing.csv',timing)
    (out/'environment.json').write_text(json.dumps(dict(
        python=sys.version, platform=platform.platform(),
        numpy=np.__version__, scipy=__import__('scipy').__version__,
        timer='time.perf_counter; 1 warm-up; no thread count pinning',
        seeds=seeds, repeats=repeats), indent=2)+'\n',encoding='utf-8')
    return rows, timing


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=Path('review_output'))
    p.add_argument('--seeds',type=int,default=40)
    p.add_argument('--repeats',type=int,default=5)
    a=p.parse_args()
    run(a.output, a.seeds, a.repeats)
    print(f'CSV and execution metadata written to {a.output}')


if __name__=='__main__':
    main()
