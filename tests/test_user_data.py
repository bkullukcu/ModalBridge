import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from modalbridge.user_data import convert, audit_pair, InputContractError
from modalbridge.io import load_modes
from modalbridge.core import match_modes

FIX = Path(__file__).resolve().parents[1] / 'examples' / 'step3_user_data'


def test_convert_csv_match_existing_core_and_audit(tmp_path):
    a,b=tmp_path/'a.npz',tmp_path/'b.npz'
    convert(FIX/'reference.csv',FIX/'schema.json',a)
    convert(FIX/'candidate.csv',FIX/'schema.json',b)
    report=audit_pair(a,b)
    assert report['common_dofs']==4 and report['coordinates_verified']
    m=match_modes(load_modes(a),load_modes(b))
    assert np.min(np.diag(m['mac'])) > .99
    with np.load(a) as z:
        assert set(z['dof_ids'].astype(str))=={'P01|X','P02|X','P03|X','P04|X'}
        assert z['quantity_kind'].item()=='resonance_response'


def test_npz_convert_explicit_shape(tmp_path):
    x=tmp_path/'original.npz'
    np.savez(x,frequency=[91,170],shapes=np.array([[1,2],[3,4],[5,6]],complex),
             dof_ids=['P01|X','P02|Y','P03|X'],mode_ids=['M1','M2'],
             coordinates=[[0,0,0],[30,0,0],[60,0,0]])
    report=convert(x,FIX/'schema.json',tmp_path/'converted.npz')
    assert report['n_dofs']==3 and report['coordinates_available']


def test_failed_direction_cannot_be_silently_inferred(tmp_path):
    d=pd.read_csv(FIX/'reference.csv');d.loc[0,'axis']='w'
    file=tmp_path/'bad.csv';d.to_csv(file,index=False)
    with pytest.raises(InputContractError,match='direction'):
        convert(file,FIX/'schema.json',tmp_path/'m.npz')


def test_missing_dof_cell_is_fatal(tmp_path):
    d=pd.read_csv(FIX/'reference.csv').iloc[1:];file=tmp_path/'bad.csv';d.to_csv(file,index=False)
    with pytest.raises(InputContractError,match='missing physical DOFs'):
        convert(file,FIX/'schema.json',tmp_path/'m.npz')


def test_audit_detects_moved_sensor(tmp_path):
    a,b=tmp_path/'a.npz',tmp_path/'b.npz'
    convert(FIX/'reference.csv',FIX/'schema.json',a)
    d=pd.read_csv(FIX/'candidate.csv');d.loc[d.sensor_location=='P03','x_mm']+=4
    inp=tmp_path/'shift.csv';d.to_csv(inp,index=False)
    convert(inp,FIX/'schema.json',b)
    with pytest.raises(InputContractError,match='different positions'):
        audit_pair(a,b,tolerance_m=.0001)


def test_audit_refuses_different_frames(tmp_path):
    a,b=tmp_path/'a.npz',tmp_path/'b.npz'
    convert(FIX/'reference.csv',FIX/'schema.json',a)
    cfg=json.loads((FIX/'schema.json').read_text());cfg['reference_frame']='rotated-unregistered'
    schema=tmp_path/'config.json';schema.write_text(json.dumps(cfg))
    convert(FIX/'candidate.csv',schema,b)
    with pytest.raises(InputContractError,match='frames differ'):
        audit_pair(a,b)


def test_frequency_inconsistent_dof_is_fatal(tmp_path):
    d=pd.read_csv(FIX/'reference.csv');d.loc[0,'hz']+=2
    inp=tmp_path/'bad.csv';d.to_csv(inp,index=False)
    with pytest.raises(InputContractError,match='changes frequency'):
        convert(inp,FIX/'schema.json',tmp_path/'out.npz')


def test_polar_conversion_equals_real_imag(tmp_path):
    df=pd.read_csv(FIX/'reference.csv')
    z=df.h_real.to_numpy()+1j*df.h_imag.to_numpy()
    df['linear_mag']=abs(z);df['phase_in_degrees']=np.rad2deg(np.angle(z))
    df=df.drop(columns=['h_real','h_imag'])
    src=tmp_path/'polar.csv';df.to_csv(src,index=False)
    cfg=json.loads((FIX/'schema.json').read_text())
    cfg.update(complex_format='magnitude_phase',phase_unit='degree',phase_sign=1,phase_reference='relative to force excitation')
    cfg['columns'].pop('real');cfg['columns'].pop('imag')
    cfg['columns'].update(magnitude='linear_mag',phase='phase_in_degrees')
    sch=tmp_path/'config.json';sch.write_text(json.dumps(cfg))
    convert(src,sch,tmp_path/'polar.npz');convert(FIX/'reference.csv',FIX/'schema.json',tmp_path/'cart.npz')
    with np.load(tmp_path/'polar.npz') as p, np.load(tmp_path/'cart.npz') as c:
        assert np.allclose(p['shapes'],c['shapes'])


def test_audit_detects_mismatched_quantity_kinds(tmp_path):
    a,b=tmp_path/'a.npz',tmp_path/'b.npz'
    convert(FIX/'reference.csv',FIX/'schema.json',a)
    cfg=json.loads((FIX/'schema.json').read_text());cfg['quantity_kind']='identified_mode'
    sch=tmp_path/'config.json';sch.write_text(json.dumps(cfg))
    convert(FIX/'candidate.csv',sch,b)
    with pytest.raises(InputContractError,match='quantity kinds differ'):
        audit_pair(a,b)


def test_npz_real_only_shape_rejected(tmp_path):
    x=tmp_path/'real.npz';np.savez(x,frequency=[91],shapes=np.ones((3,1)),dof_ids=['P1|X','P2|X','P3|X'],
                                      mode_ids=['M1'],coordinates=[[0,0,0],[10,0,0],[20,0,0]])
    with pytest.raises(InputContractError,match='must be complex'):
        convert(x,FIX/'schema.json',tmp_path/'out.npz')
