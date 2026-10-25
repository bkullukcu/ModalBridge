"""Explicit physical registration and subspace diagnostics (no automatic ID mapping)."""
import numpy as np
from scipy.linalg import subspace_angles

def rigid_registration(source, target):
    """Fit target = source @ rotation + translation from paired 3D fiducials.

    No scaling or reflection is fitted. Points must already correspond physically.
    Residuals use the input coordinate unit; they do not define a matching tolerance.
    """
    from .benchmarks import rigid_transform_from_fiducials
    result=rigid_transform_from_fiducials(target, source)
    residual=np.linalg.norm(np.asarray(source)@result['rotation']+result['translation']-target,axis=1)
    return dict(result,residuals=residual)

def subspace_similarity(a,b):
    """Principal angles for full-rank, equal-dimensional complex mode groups.

    DOFs must already be physically aligned. This is a group diagnostic, not
    an extension of one-to-one assignment or proof of physical mode identity.
    """
    a,b=np.asarray(a,complex),np.asarray(b,complex)
    if a.ndim!=2 or b.shape!=a.shape or min(a.shape)==0 or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('equal finite DOF-by-mode matrices required')
    if np.linalg.matrix_rank(a)<a.shape[1] or np.linalg.matrix_rank(b)<b.shape[1]:
        raise ValueError('full column rank required')
    angles=subspace_angles(a,b)
    return {'angles_rad':angles,'minimum_squared_cosine':float(np.cos(angles).min()**2)}

def selective_metrics(predicted, truth):
    """Coverage and false-match fraction; None denotes absence/rejection.

    Truth must be independently supplied, including genuinely absent counterparts.
    Wrong rejections and correct rejections are reported separately.
    """
    if len(predicted)!=len(truth) or not len(truth):raise ValueError('nonempty aligned labels required')
    accepted=sum(p is not None for p in predicted)
    wrong=sum(p is not None and p!=t for p,t in zip(predicted,truth))
    return {'coverage':accepted/len(truth),'false_match_fraction':wrong/accepted if accepted else float('nan'),
            'accepted':accepted,'wrong_matches':wrong,
            'correct_rejections':sum(p is None and t is None for p,t in zip(predicted,truth)),
            'missed_counterparts':sum(p is None and t is not None for p,t in zip(predicted,truth))}
