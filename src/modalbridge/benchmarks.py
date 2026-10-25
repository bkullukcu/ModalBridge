"""Reference correspondences and physical coordinate registration diagnostics.

This module does not identify physical modes from single-record response shapes.
External pyOMA comparison is deliberately not claimed unless actually executed.
"""
from __future__ import annotations
import numpy as np
from scipy.optimize import linear_sum_assignment
from .core import ModeSet, match_modes


def rigid_transform_from_fiducials(reference, moving):
    """Estimate proper rigid R,t mapping moving coordinates to reference.

    Call only on trusted, independently corresponding fiducials in equal units.
    This does not infer that similarly named experimental scan IDs are identical.
    No reflection or uniform scaling is allowed.
    """
    a=np.asarray(reference,float);b=np.asarray(moving,float)
    if a.ndim!=2 or b.shape!=a.shape or a.shape[1]!=3 or len(a)<3 or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('equal finite (n>=3,3) trusted fiducial coordinates required')
    ac=a-a.mean(axis=0);bc=b-b.mean(axis=0)
    if np.linalg.matrix_rank(ac)<2 or np.linalg.matrix_rank(bc)<2:
        raise ValueError('fiducials must include non-collinear points')
    u,_,vt=np.linalg.svd(bc.T@ac)
    d=np.eye(3);d[-1,-1]=np.linalg.det(u@vt)
    rotation=u@d@vt # row vector: b @ rotation + t = a
    translation=a.mean(axis=0)-b.mean(axis=0)@rotation
    residual=np.linalg.norm(b@rotation+translation-a,axis=1)
    return {'rotation':rotation,'translation':translation,
            'rms_residual':float(np.sqrt(np.mean(residual**2))),
            'max_residual':float(residual.max()),'proper_rotation':bool(np.linalg.det(rotation)>0)}


def apply_rigid_transform(points,transform):
    p=np.asarray(points,float)
    if p.ndim!=2 or p.shape[1]!=3 or not np.isfinite(p).all():
        raise ValueError('finite Nx3 coordinates required')
    return p @ np.asarray(transform['rotation']) + np.asarray(transform['translation'])


def frequency_only_assignment(reference:ModeSet,candidate:ModeSet,max_relative_shift=.2,
                              unmatched_cost=.3):
    """Naive frequency-only Hungarian matching with explicit dummy reject slots.

    Scientific baseline only: frequency agreement is insufficient for mode identity.
    """
    if max_relative_shift<0 or unmatched_cost<=0:raise ValueError('invalid thresholds')
    a,b=reference.frequency,candidate.frequency
    shift=np.abs(a[:,None]-b[None,:])/a[:,None]
    n,m=shift.shape
    big=1e6
    cost=np.full((n,m+n),big)
    cost[:,:m]=np.where(shift<=max_relative_shift,shift,big)
    cost[np.arange(n),m+np.arange(n)]=unmatched_cost
    rr,cc=linear_sum_assignment(cost)
    return [{'reference':int(i),'candidate':None if j>=m or cost[i,j]>=unmatched_cost else int(j),
             'relative_shift':None if j>=m else float(shift[i,j])} for i,j in zip(rr,cc)]


def compare_to_frequency_only(reference:ModeSet,candidate:ModeSet,**kwargs):
    """Report disagreements but *not* false-mode rates without independently known truth."""
    ml=match_modes(reference,candidate,**kwargs)['pairs']
    fo=frequency_only_assignment(reference,candidate,
             max_relative_shift=kwargs.get('max_relative_shift',.2))
    by_freq={p['reference']:p['candidate'] for p in fo}
    return [{'reference':p['reference'],'mac_candidate':p['candidate'],
             'mac_status':p['status'],'frequency_candidate':by_freq[p['reference']],
             'disagrees':p['candidate']!=by_freq[p['reference']]} for p in ml]
