"""Read explicit NPZ mode sets and Polytec-style tab-separated time exports."""
import io
import re
import numpy as np
from .core import ModeSet


def load_modes(path):
    with np.load(path,allow_pickle=False) as z:
        return ModeSet(z['frequency'],z['shapes'],tuple(z['dof_ids'].astype(str)))


def parse_polytec(text):
    """Return metadata and numerical samples; reject absent/unknown headers."""
    lines=text.splitlines()
    point=re.search(r'Point Index:\s*(\d+).*?x\s*=\s*([^\s\]]+)\s+y\s*=\s*([^\s\]]+)\s+z\s*=\s*([^\s\]]+)',text)
    signal=next((x.split('\t',1)[1].strip() for x in lines if x.startswith('Signal:') and '\t' in x),None)
    source=next((x.split('\t',1)[1].strip() for x in lines if x.startswith('Source File Name:') and '\t' in x),None)
    units=next((i for i,x in enumerate(lines) if x.strip().startswith('[ s ]')),None)
    if point is None or units is None or signal is None or source is None:raise ValueError('unrecognised Polytec time export')
    data=np.loadtxt(io.StringIO('\n'.join(lines[units+1:])))
    if data.ndim!=2 or data.shape[1] not in (2,4) or len(data)<8 or not np.isfinite(data).all():raise ValueError('invalid samples')
    dt=np.diff(data[:,0])
    if np.any(dt<=0) or not np.allclose(dt,np.median(dt),rtol=1e-3,atol=1e-9):raise ValueError('nonuniform time base')
    return {'source':source,'point':int(point[1]),'xyz':np.array([float(point[i]) for i in (2,3,4)]),'signal':signal,'fs':float(1/np.median(dt)),'time':data[:,0],'values':data[:,1:]}


def single_record_frf(force,velocity,max_frequency=150.,relative_force_floor=1e-6,
                      response_end_fraction=.05,force_window_s=.04):
    """Single synchronous impact V/F, not averaged H1 or coherence.

    Subtract a 3 ms pretrigger baseline. Gate force to the first 40 ms and
    exponentially taper response from the force peak to 5% at record end.
    This changes apparent damping; no damping correction or identification is
    performed. Repeated impacts and late response artifacts require separate QC.
    """
    if force['point']!=velocity['point'] or force['source'].lower()!=velocity['source'].lower() or force['values'].shape[1]!=1 or velocity['values'].shape[1]!=3 or not np.allclose(force['xyz'],velocity['xyz'],atol=1e-6) or not np.array_equal(force['time'],velocity['time']):raise ValueError('force and velocity are not aligned records')
    if max_frequency<=0 or not 0<relative_force_floor<1 or not 0<response_end_fraction<1 or force_window_s<=0:raise ValueError('invalid window or frequency parameters')
    t=force['time']-force['time'][0];n=len(t);pre=max(1,int(.003*force['fs']))
    ff=force['values'][:,0]-np.median(force['values'][:pre,0])
    vv=velocity['values']-np.mean(velocity['values'][:pre],axis=0)
    gate=t<=force_window_s
    if gate.sum()<2:raise ValueError('force window too short')
    ip=int(np.argmax(np.where(gate,abs(ff),-np.inf)));duration=t[-1]-t[ip]
    if duration<=0:raise ValueError('force peak at final sample')
    w=np.zeros(n);w[ip:]=np.exp(np.log(response_end_fraction)*(t[ip:]-t[ip])/duration)
    f=np.fft.rfft(ff*gate)
    v=np.fft.rfft(vv*w[:,None],axis=0)
    hz=np.fft.rfftfreq(n,1/force['fs']);mask=(hz>0)&(hz<=max_frequency)&(abs(f)>relative_force_floor*max(abs(f)))
    if not mask.any():raise ValueError('no excited frequency bins')
    return hz[mask],v[mask]/f[mask,None]
