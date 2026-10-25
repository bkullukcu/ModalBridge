import numpy as np
import pandas as pd
import pytest
from scipy.io import savemat
from modalbridge.external_shm import (load_flood_shab,modal_snapshot,matched_snapshot_pairs,inspect_mat_structure,
inspect_h5_structure,load_h5_numeric_dataset,h1_impact_frf,h5_sensor_window)

def _flood_csv(tmp_path):
    z=[]
    for i,f in enumerate([1.05,1.06]):
        d={'timestamp':f'2026-03-27 00:{i*30:02d}:00','freq_mode_01_Hz':f,'damping_mode_01':.02}
        for j,c in enumerate(['AM1Z','AV1Z','AV1X']):
            d[f'phi_mode_01_{c}_real']=j+1
            d[f'phi_mode_01_{c}_imag']=.2*(j+1)
        z.append(d)
    p=tmp_path/'flood.csv';pd.DataFrame(z).to_csv(p,index=False);return p

def test_flood_tracking(tmp_path):
    data=load_flood_shab(_flood_csv(tmp_path)); times=list(data.timestamp.unique())
    x=matched_snapshot_pairs(modal_snapshot(data,times[0]),modal_snapshot(data,times[1]))
    assert len(x)==1 and x[0]['candidate']==1 and x[0]['mac']>.99

def test_flood_unpaired_rejected(tmp_path):
    p=_flood_csv(tmp_path);d=pd.read_csv(p);d=d.drop(columns=['phi_mode_01_AM1Z_imag']);d.to_csv(p,index=False)
    with pytest.raises(ValueError,match='Unpaired'):load_flood_shab(p)

def test_flood_rejects_no_common_channels():
    x={1:{'frequency':1,'shape':{'a':1+0j,'b':2+0j,'c':3+0j}}}
    y={1:{'frequency':1,'shape':{'q':1+0j,'w':2+0j,'e':3+0j}}}
    assert matched_snapshot_pairs(x,y)[0]['candidate'] is None

def test_eth_mat_inventory(tmp_path):
    p=tmp_path/'impact.mat';savemat(p,{'acceleration':np.arange(64.),'frequency':np.array([100.])})
    assert inspect_mat_structure(p)['acceleration']['shape']==[64]

def test_hell_h5_inventory(tmp_path):
    h5py=pytest.importorskip('h5py')
    p=tmp_path/'data.h5'
    with h5py.File(p,'w') as z:z.create_dataset('sensors/acceleration',data=np.arange(32,dtype=float))
    inv=inspect_h5_structure(p)
    assert inv[0]['path']=='sensors/acceleration'
    assert len(load_h5_numeric_dataset(p,'sensors/acceleration'))==32
    assert len(h5_sensor_window(p,'sensors/acceleration',0,8))==8

def test_h1_frf_finite_nonempty():
    x=np.sin(np.arange(1024)*.17);y=2*x
    f,h=h1_impact_frf(x,y,fs if False else 100,nperseg=128)
    assert len(f)==65 and np.isfinite(h[np.isfinite(h)]).all()
