"""Experimental H1 complex transfer functions from ETH Zurich/PoliMi archives.

Scientific contracts
--------------------
Piezo acceleration: response (m/s^2) / base acceleration (m/s^2),
DMM displacement: response (m) / measured base displacement (m),
Impact accelerance: response acceleration (m/s^2) / impact force (N, per metadata).
The independently clocked piezo and DMM channels MUST NOT be cross-spectrally
combined. H1 vectors sampled at measured resonance peaks are NOT identified
mass-normalized eigenvectors.
"""
from dataclasses import dataclass
from pathlib import Path
from io import BytesIO
import zipfile
import numpy as np
from scipy.io import loadmat
from scipy.signal import csd, welch, find_peaks

TEST_META={
 11:('baseline','2.1'),12:('baseline','2.2'),13:('baseline','2.1'),
 14:('baseline','2.2'),15:('damaged','2.2'),16:('damaged','2.1'),17:('damaged','2.1'),
}
PIEZO_DOFS={
 '2.1':{'A':(76,1),'B':(77,1),'C':(73,-1),'D':(74,1),'E':(79,-1),'F':(80,1)},
 '2.2':{'A':(76,1),'B':(77,1),'C':(73,-1),'D':(74,1),'E':(82,1),'F':(83,1)},
}
COMMON_PIEZO=(73,74,76,77)
RESONANCE_WINDOWS=((1.25,2.1),(3.6,4.9),(6.6,8.0),(9.3,10.65))

@dataclass
class FRFRecord:
    test:int
    source:str
    frequencies:np.ndarray
    dofs:tuple
    h:np.ndarray  # (output DOF, frequency), complex
    coherence:np.ndarray
    reference:str
    fs:float
    duration_s:float


def h1(y,x,fs,nperseg):
    """Complex H1 = S_xy/S_xx; MSC; x and y sampled by SAME system."""
    x=np.asarray(x,float).ravel(); y=np.asarray(y,float)
    if y.ndim==1:y=y[None,:]
    if y.shape[1]!=len(x) or nperseg>len(x):raise ValueError('incompatible channels or segment size')
    f,sxx=welch(x,fs=fs,nperseg=nperseg,noverlap=nperseg//2,detrend='constant')
    h=[];cohs=[]
    for yi in y:
        _,sxy=csd(x,yi,fs=fs,nperseg=nperseg,noverlap=nperseg//2,detrend='constant')
        _,syy=welch(yi,fs=fs,nperseg=nperseg,noverlap=nperseg//2,detrend='constant')
        h.append(sxy/np.maximum(sxx,np.finfo(float).tiny))
        cohs.append(np.clip(abs(sxy)**2 / np.maximum(sxx*syy,np.finfo(float).tiny),0,1))
    return f,np.asarray(h),np.asarray(cohs)



def mimo_h1_x(y,base_x,base_y,fs,nperseg,ridge_fraction=1e-6):
    """Conditional complex H1 coefficient for base x given simultaneous x and y.

    Biaxial excitation requires MIMO treatment: single-input MSC may be low
    simply because the second independent excitation remains unmodelled. The
    2×2 Welch spectral normal equations use per-input RMS scaling to stabilize
    the solver, then convert the x coefficient back to physical units. This also
    insulates the x coefficient from an unknown constant Gy calibration factor
    (not from nonlinear corruption). Returned quality is MULTIPLE coherence.
    """
    y=np.asarray(y,float)
    if y.ndim==1:y=y[None]
    x=np.stack([np.asarray(base_x,float).ravel(),np.asarray(base_y,float).ravel()])
    if len(x[0])!=y.shape[1]:raise ValueError('inputs/outputs must have identical clock and length')
    rms=np.std(x,axis=1)
    if np.any(rms<=0):raise ValueError('zero-energy reference input')
    u=x/rms[:,None]
    cs=lambda a,b: csd(a,b,fs=fs,nperseg=nperseg,noverlap=nperseg//2,detrend='constant')[1]
    f=welch(u[0],fs=fs,nperseg=nperseg,noverlap=nperseg//2,detrend='constant')[0]
    suu=np.array([[cs(u[i],u[j]) for j in range(2)] for i in range(2)]).transpose(2,0,1)
    # Spectral cross-power regularizer is a tiny fraction of local trace.
    regularizer=np.maximum(np.trace(suu,axis1=1,axis2=2).real*ridge_fraction/2,1e-30)
    suu[:,0,0]+=regularizer;suu[:,1,1]+=regularizer
    h=[];cohs=[]
    for yi in y:
        suy=np.column_stack([cs(u[i],yi) for i in range(2)])
        sol=np.linalg.solve(suu,suy[...,None])[...,0]
        h.append(sol[:,0]/rms[0])
        syy=welch(yi,fs=fs,nperseg=nperseg,noverlap=nperseg//2,detrend='constant')[1]
        explained=np.sum(np.conj(suy)*sol,axis=1).real
        cohs.append(np.clip(explained/np.maximum(syy,1e-30),0,1))
    return f,np.asarray(h),np.asarray(cohs)

def load_piezo(zippath,test,nperseg=8192):
    if test not in TEST_META:raise ValueError('tests 11 through 17 only')
    with zipfile.ZipFile(zippath) as z:
        mat=loadmat(BytesIO(z.read(f'Piezoelectric Accelerometers/Test-{test}.mat')),simplify_cells=True)
    layout=PIEZO_DOFS[TEST_META[test][1]]
    y=np.asarray([mat['Data1_'+c].ravel()*sgn for c,(dof,sgn) in layout.items()])
    fs=float(mat['Sample_rate']); x=mat['Data1_Gx'].ravel()
    f,h,c=mimo_h1_x(y,x,mat['Data1_Gy'].ravel(),fs,nperseg)
    return FRFRecord(test,'piezo',f,tuple(d for d,_ in layout.values()),h,c,'conditional_base_Gx_given_Gy',fs,len(x)/fs)


def load_dmm(zippath,test,nperseg=4096):
    if test not in TEST_META:raise ValueError('tests 11 through 17 only')
    try:
        import h5py  # optional: only needed for the MATLAB v7.3 (HDF5) DMM files
    except ImportError as e:
        raise ImportError('Reading DMM files requires the optional dependency h5py; pip install modalbridge[external]') from e
    with zipfile.ZipFile(zippath) as z:
        blob=z.read(f'DMM/Test-{test}_DMM.mat')
    with h5py.File(BytesIO(blob),'r') as h:
        d=h['data']; channels={}
        for i in range(96):
            group=h[d[0,i]]
            if isinstance(group,h5py.Group) and 'disp_raw' in group:
                channels[i+1]=np.asarray(group['disp_raw'][()]).ravel()
        ground=h[d[0,0]]
        fs=float(np.asarray(ground['fsamp'][()]).item())
    if 1 not in channels: raise ValueError(f'test {test}: ground x DOF1 missing')
    # Both base and output DMM channels are simultaneous, within one 200 Hz device.
    # Vertical z DOFs excluded: experimental range is primarily lateral 0-20 Hz.
    ids=tuple(i for i in sorted(channels) if i>3 and i%3!=0)
    y=np.stack([channels[i] for i in ids]); x=channels[1]
    f,hs,coh=mimo_h1_x(y,x,channels[2],fs,nperseg)
    return FRFRecord(test,'dmm',f,ids,hs,coh,'conditional_base_dof1_x_given_dof2_y',fs,len(x)/fs)


def peak_candidates(record,windows=RESONANCE_WINDOWS,dofs=None):
    """Narrowband spectral-peak locations on ||H||_2; quadratic log peak.

    These are *resonance-frequency estimates*, not complex poles or independently
    identified modal natural frequencies; window selection is exploratory.
    """
    idx=np.arange(len(record.dofs)) if dofs is None else np.array([record.dofs.index(i) for i in dofs])
    metric=np.linalg.norm(record.h[idx,:],axis=0)
    freq=record.frequencies; out=[]
    for lo,hi in windows:
        ii=np.flatnonzero((freq>=lo)&(freq<=hi))
        k=int(ii[np.argmax(metric[ii])]); best=float(freq[k])
        if 0<k<len(freq)-1:
            ym,ymid,yp=np.log(np.maximum(metric[k-1:k+2],1e-30))
            denom=(ym-2*ymid+yp)
            off=0.5*(ym-yp)/denom if denom < -1e-9 else 0
            if abs(off)<=1:best=float(freq[k]+off*(freq[1]-freq[0]))
        mean_coh=float(np.median(record.coherence[idx,k]))
        out.append({'band':f'{lo:g}-{hi:g} Hz','frequency_hz':best,'metric_at_peak':float(metric[k]),
                    'median_coherence':mean_coh,'bin_frequency_hz':float(freq[k])})
    return out


def sample_complex_shape(record,frequency,dofs):
    f=record.frequencies
    return np.asarray([np.interp(frequency,f,record.h[record.dofs.index(d)].real)
                      +1j*np.interp(frequency,f,record.h[record.dofs.index(d)].imag)
                       for d in dofs],complex)


def impact_accelerance(zippath,test,output='C',pre=82,length=4096):
    """H1 from distinct detected impact events, aligned on hammer-force peak.

    Use unwindowed per-impact FFT of response/force with a mean detrend;
    event windows are 40.96s at 100Hz and nonoverlapping. Broad-band
    hammer frequency-response estimation assumes sufficiently decayed response.
    """
    with zipfile.ZipFile(zippath) as z:
        m=loadmat(BytesIO(z.read(f'Phase1of2_Impacts/Test-{test}.mat')),simplify_cells=True)
    force=np.asarray(m['Data1_HAMMER'],float).ravel()
    response=np.asarray(m['Data1_'+output],float).ravel()
    fs=float(m['Sample_rate']); n=int(length)
    impulses,_=find_peaks(abs(force),distance=int(35*fs),prominence=np.max(abs(force))*.2)
    impulses=impulses[(impulses>=pre)&(impulses+n-pre<len(force))]
    if len(impulses)<4:raise ValueError(f'not enough usable impact events: {len(impulses)} for test {test}')
    F=[];Y=[]
    for p in impulses:
        sl=slice(p-pre,p-pre+n)
        x=force[sl]-np.mean(force[sl]); y=response[sl]-np.mean(response[sl])
        F.append(np.fft.rfft(x));Y.append(np.fft.rfft(y))
    F=np.asarray(F);Y=np.asarray(Y)
    sxy=np.mean(np.conj(F)*Y,axis=0);sxx=np.mean(abs(F)**2,axis=0)
    syy=np.mean(abs(Y)**2,axis=0)
    freq=np.fft.rfftfreq(n,1/fs)
    return freq,sxy/np.maximum(sxx,1e-30),np.clip(abs(sxy)**2/np.maximum(sxx*syy,1e-30),0,1),len(impulses)
