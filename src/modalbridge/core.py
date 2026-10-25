"""Auditable complex response-shape matching with explicit abstention."""
from dataclasses import dataclass
import numpy as np
from scipy.optimize import linear_sum_assignment

__all__=['ModeSet','complex_mac','align_dofs','match_modes','assignment_stability','cmif']

@dataclass
class ModeSet:
    """Frequencies (mode,), complex shapes (DOF, mode), unique physical DOF IDs.

    Equal IDs must denote the same physical point AND direction in a common frame.
    These may be resonance response vectors, but then must not be called identified
    eigenmodes. Coordinate registration is the caller's responsibility.
    """
    frequency: np.ndarray
    shapes: np.ndarray
    dof_ids: tuple
    label: str = 'configuration'
    def __post_init__(self):
        self.frequency=np.asarray(self.frequency,float);self.shapes=np.asarray(self.shapes,complex);self.dof_ids=tuple(self.dof_ids)
        if self.frequency.ndim!=1 or self.shapes.shape!=(len(self.dof_ids),len(self.frequency)) or len(self.frequency)==0:
            raise ValueError('shape/frequency/DOF mismatch')
        if len(set(self.dof_ids))!=len(self.dof_ids) or not np.isfinite(self.shapes).all() or not np.isfinite(self.frequency).all() or np.any(self.frequency<=0):
            raise ValueError('unique DOFs and finite positive frequencies required')
        if np.any(np.linalg.norm(self.shapes,axis=0)==0):raise ValueError('zero-energy shape')


def align_dofs(a,b,min_common=3):
    """Align by explicit physical identifiers, never by array row position."""
    common=sorted(set(a.dof_ids)&set(b.dof_ids),key=str)
    if len(common)<min_common:raise ValueError('insufficient common physical DOFs')
    ai={k:i for i,k in enumerate(a.dof_ids)};bi={k:i for i,k in enumerate(b.dof_ids)}
    return a.shapes[[ai[k] for k in common]],b.shapes[[bi[k] for k in common]],tuple(common)


def complex_mac(a,b,weights=None):
    """All-pairs weighted complex MAC; columns are shapes."""
    a=np.asarray(a,complex);b=np.asarray(b,complex)
    if a.ndim!=2 or b.ndim!=2 or a.shape[0]!=b.shape[0] or not np.isfinite(a).all() or not np.isfinite(b).all():raise ValueError('finite shape matrices with common DOFs required')
    w=np.ones(len(a)) if weights is None else np.asarray(weights,float)
    if w.shape!=(len(a),) or not np.isfinite(w).all() or np.any(w<0) or np.count_nonzero(w)<1:raise ValueError('invalid weights')
    na=np.sum(w[:,None]*abs(a)**2,axis=0);nb=np.sum(w[:,None]*abs(b)**2,axis=0)
    if np.any(na<=0) or np.any(nb<=0):raise ValueError('zero weighted shape energy')
    return np.clip(abs(a.conj().T@(w[:,None]*b))**2/(na[:,None]*nb[None,:]),0,1)


def match_modes(a,b,weights=None,min_mac=.6,max_relative_shift=.2,frequency_weight=.2,unmatched_cost=.6,ambiguity_margin=.05):
    """Global one-to-one assignment with row-specific dummy alternatives.

    Cost = 1-MAC + frequency_weight*relative_frequency_difference.
    Pairs must satisfy both gates and beat unmatched_cost. A small row-local
    alternative-cost margin flags ambiguity; it is not a posterior probability.
    weights follow the sorted common DOF order returned by align_dofs.
    """
    if not 0<=min_mac<=1 or max_relative_shift<0 or frequency_weight<0 or unmatched_cost<=0 or ambiguity_margin<0:raise ValueError('invalid matching parameters')
    x,y,ids=align_dofs(a,b);mac=complex_mac(x,y,weights)
    delta=abs(a.frequency[:,None]-b.frequency[None,:])/a.frequency[:,None]
    cost=1-mac+frequency_weight*delta;valid=(mac>=min_mac)&(delta<=max_relative_shift)
    n,m=cost.shape;big=1e6
    c=np.full((n,m+n),big);c[:,:m]=np.where(valid,cost,big)
    c[np.arange(n),m+np.arange(n)]=unmatched_cost
    rows,cols=linear_sum_assignment(c);out=[]
    for i,j in zip(rows,cols):
        if j>=m or not valid[i,j] or cost[i,j]>=unmatched_cost:
            out.append({'reference':int(i),'candidate':None,'status':'unmatched','mac':None,'cost':float(unmatched_cost),'margin':None})
        else:
            options=np.r_[cost[i,valid[i]& (np.arange(m)!=j)],unmatched_cost]
            margin=float(np.min(options)-cost[i,j])
            out.append({'reference':int(i),'candidate':int(j),'status':'ambiguous' if margin<ambiguity_margin else 'matched','mac':float(mac[i,j]),'cost':float(cost[i,j]),'margin':margin})
    return {'pairs':out,'mac':mac,'relative_shift':delta,'cost':cost,'common_dofs':ids}


def assignment_stability(a,b,n_boot=200,seed=2026,**kwargs):
    """DOF-resampling assignment frequencies (sensitivity, not confidence).

    Resampling individual DOFs ignores spatial correlation: report as a diagnostic.
    Supply no fixed weights; multiplicities provide bootstrap weights.
    """
    if n_boot<2 or 'weights' in kwargs:raise ValueError('n_boot >=2 and no explicit weights required')
    x,y,ids=align_dofs(a,b);aa=ModeSet(a.frequency,x,ids);bb=ModeSet(b.frequency,y,ids)
    rng=np.random.default_rng(seed);counts=np.zeros((len(a.frequency),len(b.frequency)+1))
    successful=0
    for _ in range(n_boot):
        w=np.bincount(rng.integers(len(ids),size=len(ids)),minlength=len(ids))
        try:r=match_modes(aa,bb,weights=w,**kwargs)
        except ValueError:continue
        successful+=1
        for p in r['pairs']:counts[p['reference'], -1 if p['candidate'] is None else p['candidate']]+=1
    if successful==0:raise ValueError('all resamples degenerate')
    return {'frequency':counts/successful,'successful_resamples':successful,'requested_resamples':n_boot}


def cmif(frf):
    """Singular values of (frequency, output_DOF, input_reference) FRF matrices.

    A single-reference CMIF has only one singular-value curve and does not
    resolve mode multiplicity by itself.
    """
    h=np.asarray(frf,complex)
    if h.ndim!=3 or min(h.shape)==0 or not np.isfinite(h).all():raise ValueError('finite 3D FRF array required')
    return np.linalg.svd(h,compute_uv=False)
