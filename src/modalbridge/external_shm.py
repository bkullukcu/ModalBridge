"""External SHM dataset adapters: FLOOD-SHAB, ETH/PoliMi and Hell Bridge.

The SHM datasets are heterogeneous. Do not equate tracked operating-mode
labels to independently verified physical ground truth. All matching is
conditional on stable sensor/channel coordinates and correct DOF directions.
"""
import re
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment


def load_flood_shab(csv_path, *, min_channels=3):
    """Read wide 2026 FLOOD-SHAB CSV into long normalized complex shape rows.
    Output columns: timestamp, mode_id, freq_hz, damping, channel, real, imag.
    NaN (absent mode) is retained as missing, never replaced with zero.
    """
    df=pd.read_csv(csv_path)
    if 'timestamp' not in df.columns:raise ValueError('timestamp is required')
    rx=re.compile(r'^phi_mode_(\d{2})_(.+)_(real|imag)$')
    pairs={}
    for c in df.columns:
        m=rx.fullmatch(c)
        if m:pairs.setdefault((int(m.group(1)),m.group(2)),set()).add(m.group(3))
    for pair,kinds in pairs.items():
        if kinds!={'real','imag'}:raise ValueError('Unpaired complex shape component: '+str(pair))
    if not pairs:raise ValueError('No phi_mode_<nn>_<channel>_{real,imag} fields found')
    mode_ids=sorted(set(m for m,_ in pairs))
    rows=[]
    for mode in mode_ids:
        fcol=f'freq_mode_{mode:02d}_Hz'
        if fcol not in df:raise ValueError('Missing mode frequency '+fcol)
        for channel in sorted(c for m,c in pairs if m==mode):
            cols=[f'phi_mode_{mode:02d}_{channel}_real',f'phi_mode_{mode:02d}_{channel}_imag']
            chunk=pd.DataFrame({'timestamp':df['timestamp'],'mode_id':mode,'channel':channel,
                                'freq_hz':pd.to_numeric(df[fcol],errors='coerce'),
                                'real':pd.to_numeric(df[cols[0]],errors='coerce'),
                                'imag':pd.to_numeric(df[cols[1]],errors='coerce')})
            damping=f'damping_mode_{mode:02d}'
            chunk['damping']=pd.to_numeric(df[damping],errors='coerce') if damping in df else np.nan
            chunk=chunk.dropna(subset=['freq_hz','real','imag'])
            rows.append(chunk)
    long=pd.concat(rows,ignore_index=True) if rows else pd.DataFrame()
    long.attrs['min_channels_for_matching']=min_channels
    long.attrs['source']='10.5281/zenodo.20443860'
    return long


def modal_snapshot(long,timestamp):
    df=long[long['timestamp'].astype(str)==str(timestamp)]
    snapshots={}
    for mode,g in df.groupby('mode_id'):
        if not g['freq_hz'].notna().any(): continue
        snapshots[int(mode)]={'frequency':float(g['freq_hz'].median()),
                              'shape':{str(x.channel):complex(x.real,x.imag) for x in g.itertuples()}}
    return snapshots


def matched_snapshot_pairs(left,right,*,min_overlap=3,min_mac=.6,max_relative_frequency_shift=.2,unmatched_cost=.6):
    """Hungarian assignment with dummy rejection; scores conditional on shared DOFs.
    Returns abstentions, never claims mode-identity ground truth.
    """
    if min_overlap<2 or not (0<=min_mac<=1) or max_relative_frequency_shift<=0:raise ValueError('invalid matching settings')
    a=sorted(left);b=sorted(right);n=len(a);m=len(b)
    if not n:return []
    cost=np.full((n,m+n),1e6);scores={}
    for i,ai in enumerate(a):
        for j,bj in enumerate(b):
            keys=sorted(set(left[ai]['shape']) & set(right[bj]['shape']))
            if len(keys)<min_overlap:continue
            u=np.asarray([left[ai]['shape'][k] for k in keys]);v=np.asarray([right[bj]['shape'][k] for k in keys])
            den=float(np.vdot(u,u).real*np.vdot(v,v).real)
            if den<=0:continue
            mac=float(abs(np.vdot(u,v))**2/den)
            delta=abs(left[ai]['frequency']-right[bj]['frequency'])/left[ai]['frequency']
            if mac<min_mac or delta>max_relative_frequency_shift:continue
            score=.7*(1-mac)+.3*(delta/max_relative_frequency_shift)
            cost[i,j]=score;scores[(i,j)]={'mac':mac,'relative_shift':float(delta),'shared_channels':len(keys)}
        cost[i,m+i]=unmatched_cost
    rr,cc=linear_sum_assignment(cost)
    return [{'reference':a[i], 'candidate':b[j] if j<m and cost[i,j]<unmatched_cost else None,
             **(scores[(i,j)] if j<m and (i,j) in scores and cost[i,j]<unmatched_cost else {'mac':None,'relative_shift':None,'shared_channels':0})} for i,j in zip(rr,cc)]


def inspect_mat_structure(path):
    """Inspection only: ETH structure MAT files have differing layouts.
    No guessed hammer channel or DOF mapping is allowed.
    """
    from scipy.io import loadmat
    try:
        x=loadmat(path,simplify_cells=True)
    except NotImplementedError as exc:
        raise ValueError('MAT v7.3/HDF5: inspect with inspect_h5_structure') from exc
    return {k:{'shape':list(np.shape(v)),'dtype':str(np.asarray(v).dtype)} for k,v in x.items() if not k.startswith('__')}


def inspect_h5_structure(path):
    """Inventory hierarchical Hell Bridge H5 or ETH MAT v7.3 groups only."""
    import h5py
    fields=[]
    with h5py.File(path,'r') as h:
        def visit(k,obj):
            if isinstance(obj,h5py.Dataset):fields.append({'path':k,'shape':list(obj.shape),'dtype':str(obj.dtype)})
        h.visititems(visit)
    return fields


def load_h5_numeric_dataset(path,dataset_key,*,max_elements=10_000_000):
    """Explicit user-confirmed H5 key; never auto-substitute the wrong sensor."""
    import h5py
    with h5py.File(path,'r') as h:
        if dataset_key not in h:raise KeyError(f'Missing H5 dataset {dataset_key}')
        d=h[dataset_key]
        if not isinstance(d,h5py.Dataset) or d.size>max_elements or d.dtype.kind not in 'fiuc':
            raise ValueError('Dataset not suitable for bounded numerical load')
        return d[:]


def h1_impact_frf(force,response,sampling_rate_hz,*,nperseg=None):
    """Impact/testbench H1 cross-spectrum estimate from known force and acceleration.
    For ETH/PoliMi, caller MUST provide verified force and acceleration keys;
    for Hell Bridge, shaker force needs an independently verified load sensor.
    Returns accelerance m/s^2/N only if source calibration confirms units.
    """
    from scipy.signal import welch,csd
    f=np.asarray(force,float);y=np.asarray(response,float)
    if f.ndim!=1 or y.ndim!=1 or len(f)!=len(y) or len(f)<32 or not np.isfinite(f).all() or not np.isfinite(y).all() or sampling_rate_hz<=0:
        raise ValueError('force and response must be equal finite 1-D measured records')
    nperseg=int(nperseg or min(256,len(f)))
    if not 16<=nperseg<=len(f): raise ValueError('invalid nperseg')
    freq,pff=welch(f,fs=sampling_rate_hz,nperseg=nperseg)
    _,pyf=csd(f,y,fs=sampling_rate_hz,nperseg=nperseg)
    cutoff=max(float(np.max(pff))*1e-12,np.finfo(float).tiny)
    h=np.full(pff.shape,np.nan+1j*np.nan)
    np.divide(pyf,pff,out=h,where=pff>cutoff)
    return freq,h


def h5_sensor_window(path,key,start,stop):
    """Read bounded 1-D calibrated H5 array after explicit mapping verification."""
    import h5py
    with h5py.File(path,'r') as f:
        if key not in f:raise KeyError(key)
        d=f[key]
        if not isinstance(d,h5py.Dataset) or d.ndim!=1 or d.dtype.kind not in 'fi' or stop-start>3_000_000 or start<0 or stop>len(d):
            raise ValueError('Require explicit 1-D numerical channel, bounded slice')
        return d[start:stop]
