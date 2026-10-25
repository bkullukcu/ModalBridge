"""Auditable external complex shape import for ModalBridge.

`quantity_kind` keeps measured resonance-response vectors distinguishable
from independently identified structural eigenmodes. Coordinate-based
reconciliation is checked, never guessed or optimised by this adapter.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
from .core import ModeSet


class InputContractError(ValueError):
    pass


def _sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def _cfg(path):
    with open(path, encoding='utf-8') as f: c = json.load(f)
    for key in ('reference_frame', 'response_unit'):
        if not isinstance(c.get(key), str) or not c[key].strip():
            raise InputContractError(f'{key} must be explicitly declared')
    if c.get('quantity_kind') not in {'identified_mode', 'resonance_response'}:
        raise InputContractError('quantity_kind must be identified_mode or resonance_response')
    if c.get('frequency_unit') not in {'Hz', 'kHz'}:
        raise InputContractError('frequency_unit must be Hz or kHz')
    if c.get('coordinate_unit') not in {'m', 'mm', 'not_available'}:
        raise InputContractError('coordinate_unit must be m, mm or not_available')
    return c


def _strings(values, label):
    s = pd.Series(values)
    if s.isna().any() or s.astype(str).str.strip().eq('').any():
        raise InputContractError(f'empty physical {label}')
    return s.astype(str).str.strip().to_numpy()


def _save(path, schema, output, cfg, freq, matrix, ids, mode_ids, coords=None, input_kind='csv'):
    if not len(ids) >= 3 or len(set(ids)) != len(ids) or not np.isfinite(freq).all() or np.any(freq <= 0) or not np.isfinite(matrix).all():
        raise InputContractError('at least 3 unique DOFs, positive frequencies and finite complex values required')
    modes = ModeSet(freq, matrix, tuple(ids))
    output = Path(output)
    if output.resolve() == Path(path).resolve():
        raise InputContractError('cannot overwrite raw source data')
    output.parent.mkdir(parents=True, exist_ok=True)
    data = {'frequency': modes.frequency, 'shapes': modes.shapes, 'dof_ids': np.asarray(modes.dof_ids, str),
            'mode_ids': np.asarray(mode_ids, str), 'quantity_kind': np.asarray(cfg['quantity_kind']),
            'reference_frame': np.asarray(cfg['reference_frame']), 'response_unit': np.asarray(cfg['response_unit'])}
    if coords is not None:
        coords = np.asarray(coords, float)
        if coords.shape != (len(ids), 3) or not np.isfinite(coords).all():
            raise InputContractError('coordinates must be finite (DOF,3)')
        point_positions = {}
        for dof, xyz in zip(ids, coords):
            point = str(dof).rsplit('|', 1)[0]
            if point in point_positions and not np.allclose(point_positions[point], xyz, rtol=0, atol=1e-8):
                raise InputContractError(f'physical point {point} has contradictory direction-coordinate entries')
            point_positions[point] = xyz
        if len({tuple(v) for v in point_positions.values()}) != len(point_positions):
            raise InputContractError('different physical point IDs share exact coordinates')
        data['coordinates_m'] = coords
    with output.open('wb') as f: np.savez_compressed(f, **data)
    manifest = {'schema_version': 'modalbridge-user-data-v1', 'input_type': input_kind,
        'source_file': Path(path).name, 'source_sha256': _sha(path),
        'mapping_file': Path(schema).name, 'mapping_sha256': _sha(schema),
        'output_file': output.name, 'output_sha256': _sha(output),
        'n_dofs': len(ids), 'n_candidates': len(freq),
        'quantity_kind': cfg['quantity_kind'], 'reference_frame': cfg['reference_frame'],
        'response_unit': cfg['response_unit'], 'complex_response': cfg.get('complex_format', 'real_imag') + '_to_rectangular', 'coordinates_available': coords is not None,
        'physical_modal_identity': 'not validated by importer',
        'coordinate_registration': 'not performed', 'algorithm_execution': False}
    output.with_suffix(output.suffix + '.manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return manifest


def convert_csv(input_path, schema_path, output_path):
    cfg = _cfg(schema_path)
    m = cfg.get('columns', {})
    df = pd.read_csv(input_path)
    # No reliance on array order: physical point and direction form DOF identity.
    fmt = cfg.get('complex_format', 'real_imag')
    if fmt not in {'real_imag', 'magnitude_phase'}:
        raise InputContractError('complex_format must be real_imag or magnitude_phase')
    keys = ('candidate', 'point', 'direction', 'frequency') + (('real','imag') if fmt == 'real_imag' else ('magnitude', 'phase'))
    names = {k: m.get(k, k) for k in keys + ('x', 'y', 'z')}
    absent = [names[k] for k in keys if names[k] not in df]
    if absent:
        raise InputContractError(f'missing columns: {absent}')
    coords_present = all(names[k] in df for k in ('x', 'y', 'z'))
    if any(names[k] in df for k in ('x', 'y', 'z')) and not coords_present:
        raise InputContractError('coordinates require a complete x/y/z triplet')
    if (cfg['coordinate_unit'] == 'not_available') != (not coords_present):
        raise InputContractError('coordinate_unit must reflect availability of x/y/z')
    df = df.copy()
    for key in ('candidate', 'point', 'direction'):
        df['__' + key] = _strings(df[names[key]], key)
    df['__direction'] = df['__direction'].str.upper()
    if not set(df['__direction']).issubset({'X', 'Y', 'Z'}):
        raise InputContractError('direction must be X, Y or Z in a declared common reference frame')
    # A physical point ID and a direction define the comparison DOF.
    df['__dof'] = df['__point'] + '|' + df['__direction']
    for k in (('frequency','real','imag') if fmt == 'real_imag' else ('frequency','magnitude','phase')) + (('x', 'y', 'z') if coords_present else ()): 
        df['__' + k] = pd.to_numeric(df[names[k]], errors='coerce')
    numeric = ['__frequency'] + (['__real', '__imag'] if fmt == 'real_imag' else ['__magnitude', '__phase']) + (['__x', '__y', '__z'] if coords_present else [])
    if not np.isfinite(df[numeric].to_numpy(float)).all():
        raise InputContractError('nonfinite or nonnumeric mode/response data')
    if fmt == 'magnitude_phase':
        if cfg.get('phase_unit') not in {'degree', 'radian'} or cfg.get('phase_sign') not in (1, -1) or not str(cfg.get('phase_reference', '')).strip():
            raise InputContractError('polar input requires phase_unit, phase_sign (+1/-1) and phase_reference')
        if (df['__magnitude'] < 0).any():
            raise InputContractError('linear magnitude must be nonnegative')
        phase = df['__phase'] * cfg['phase_sign']
        if cfg['phase_unit'] == 'degree': phase = np.deg2rad(phase)
        df['__real'] = df['__magnitude'] * np.cos(phase)
        df['__imag'] = df['__magnitude'] * np.sin(phase)
    df['__frequency'] *= 1000 if cfg['frequency_unit'] == 'kHz' else 1
    if np.any(df['__frequency'] <= 0):
        raise InputContractError('positive frequencies required')
    if df.duplicated(['__candidate', '__dof']).any():
        raise InputContractError('duplicate candidate/physical DOF rows')
    cand = list(dict.fromkeys(df['__candidate']))
    dof = sorted(df['__dof'].unique().tolist())
    if len(cand) != len(df['__candidate'].unique()):
        raise InputContractError('candidate IDs not unique')
    if len(dof) < 3:
        raise InputContractError('at least 3 physical DOFs required for comparison')
    freq = []
    cols = []
    for key in cand:
        chunk = df[df['__candidate'] == key].set_index('__dof').reindex(dof)
        if chunk['__real'].isna().any():
            raise InputContractError(f'candidate {key} has missing physical DOFs')
        values = chunk['__frequency'].to_numpy(float)
        if not np.allclose(values, values[0], rtol=0, atol=1e-8):
            raise InputContractError(f'candidate {key} changes frequency between DOFs')
        freq.append(values[0])
        cols.append(chunk['__real'].to_numpy(float) + 1j*chunk['__imag'].to_numpy(float))
    coords = None
    if coords_present:
        factor = .001 if cfg['coordinate_unit'] == 'mm' else 1.
        positions = []
        for identifier in dof:
            values = df.loc[df['__dof'] == identifier, ['__x', '__y', '__z']].to_numpy(float) * factor
            if not np.allclose(values, values[0], rtol=0, atol=1e-8):
                raise InputContractError(f'contradictory coordinates for {identifier}')
            positions.append(values[0])
        coords = np.asarray(positions)
        # Orthogonal DOFs at the SAME point are allowed to share position.
        point_positions = {}
        for identifier, xyz in zip(dof, coords):
            point = identifier.rsplit('|', 1)[0]
            if point in point_positions and not np.allclose(point_positions[point], xyz, rtol=0, atol=1e-8):
                raise InputContractError(f'point {point} changes location by direction')
            point_positions[point] = xyz
        if len({tuple(v) for v in point_positions.values()}) != len(point_positions):
            raise InputContractError('different physical point IDs share exact coordinates')
    return _save(input_path, schema_path, output_path, cfg, np.asarray(freq), np.stack(cols, axis=1), dof, cand, coords)


def convert_npz(input_path, schema_path, output_path):
    cfg = _cfg(schema_path)
    with np.load(input_path, allow_pickle=False) as z:
        required = {'frequency', 'shapes', 'dof_ids', 'mode_ids'}
        if not required <= set(z.files):
            raise InputContractError(f'NPZ missing {sorted(required - set(z.files))}')
        freq = np.asarray(z['frequency'], float)
        shapes = np.asarray(z['shapes'])
        ids = _strings(z['dof_ids'], 'dof')
        mids = _strings(z['mode_ids'], 'candidate')
        coords = np.asarray(z['coordinates'], float) if 'coordinates' in z else None
    if not cfg.get('allow_real_only', False) and not np.iscomplexobj(shapes):
        raise InputContractError('NPZ shapes must be complex or allow_real_only=true')
    if len(set(mids)) != len(mids) or freq.shape != (len(mids),) or shapes.shape != (len(ids), len(mids)):
        raise InputContractError('mode IDs/FRF shapes dimension mismatch')
    if any('|' not in x or x.rsplit('|',1)[1] not in ('X','Y','Z') for x in ids):
        raise InputContractError('dof_ids must be explicit "physical-point|X/Y/Z"')
    if (cfg['coordinate_unit'] == 'not_available') != (coords is None):
        raise InputContractError('coordinate unit must match coordinate availability')
    if coords is not None:
        coords = coords * (0.001 if cfg['coordinate_unit'] == 'mm' else 1)
    return _save(input_path, schema_path, output_path, cfg, freq * (1000 if cfg['frequency_unit']=='kHz' else 1), shapes, ids, mids, coords, 'npz')


def convert(input_path, schema_path, output_path):
    ext = Path(input_path).suffix.lower()
    if ext == '.csv': return convert_csv(input_path, schema_path, output_path)
    if ext == '.npz': return convert_npz(input_path, schema_path, output_path)
    raise InputContractError('supported input: .csv/.npz')


def audit_pair(reference_npz, candidate_npz, tolerance_m=1e-4):
    """Abort on inconsistent frames/coordinates; no registration is inferred.

    A successful audit is necessary, NOT sufficient, to establish physical DOF
    equivalence across instrument moves, damage states or test setups.
    """
    if not np.isfinite(tolerance_m) or tolerance_m < 0:
        raise InputContractError('tolerance_m must be nonnegative')
    results = []
    for p in [reference_npz, candidate_npz]:
        with np.load(p, allow_pickle=False) as z:
            required = {'dof_ids','frequency','shapes','reference_frame','quantity_kind'}
            if not required <= set(z.files):
                raise InputContractError(f'missing imported metadata in {p}')
            entry = {'path': str(p), 'ids': z['dof_ids'].astype(str),
                     'frame': str(z['reference_frame'].item()), 'kind': str(z['quantity_kind'].item()),
                     'coords': np.asarray(z['coordinates_m'], float) if 'coordinates_m' in z else None}
            results.append(entry)
    a,b = results
    if a['kind'] != b['kind']:
        raise InputContractError('quantity kinds differ; do not equate response vectors with identified eigenmodes')
    if a['frame'] != b['frame']:
        raise InputContractError('coordinate frames differ; perform documented registration first')
    common = sorted(set(a['ids']) & set(b['ids']))
    if len(common) < 3: raise InputContractError('fewer than 3 physically named common DOFs')
    if (a['coords'] is None) != (b['coords'] is None):
        raise InputContractError('coordinates on one side only; cannot audit physical consistency')
    max_delta = None
    if a['coords'] is not None:
        ai = {v: i for i, v in enumerate(a['ids'])}; bi = {v: i for i, v in enumerate(b['ids'])}
        delta = [float(np.linalg.norm(a['coords'][ai[k]] - b['coords'][bi[k]])) for k in common]
        max_delta = max(delta)
        if max_delta > tolerance_m:
            raise InputContractError(f'different positions under matching DOF ID (max {max_delta:.6g} m > {tolerance_m} m)')
    return {'common_dofs': len(common), 'frame': a['frame'], 'max_position_discrepancy_m': max_delta,
            'coordinates_verified': a['coords'] is not None,
            'reference_quantity_kind': a['kind'], 'candidate_quantity_kind': b['kind'],
            'physical_identity_independently_validated': False,
            'ready_for_mathematical_mac': True}
