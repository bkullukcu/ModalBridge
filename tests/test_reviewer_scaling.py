"""Minimal smoke test for sensitivity/scaling exports; timings are not asserted."""
import importlib.util
import sys
from pathlib import Path

EXAMPLES = Path(__file__).resolve().parents[1] / 'examples'
sys.path.insert(0, str(EXAMPLES))
spec = importlib.util.spec_from_file_location('reviewer_scaling', EXAMPLES/'reviewer_scaling.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def test_outputs_are_complete(tmp_path):
    rows, times = mod.run(tmp_path, seeds=1, repeats=1)
    assert len(rows) == 3*2*1*3*3
    assert len(times) == 4*3
    for p in ('dof_frequency_sensitivity.csv', 'timing.csv', 'environment.json'):
        assert (tmp_path / p).exists()
