"""Explicit physical coordinate and global assignment ambiguity diagnostics."""
import numpy as np
from scipy.optimize import linear_sum_assignment
from .core import match_modes


def coordinate_overlap_audit(ids_a,coordinates_a,ids_b,coordinates_b,tolerance=1e-6):
    """Audit common named points; never assume equal labels imply equal locations.

    Units must agree and be explicitly documented by the caller.
    This is translation/rotation *agnostic*: coordinates must already be registered.
    Returns a table-like list with distances in the supplied coordinate units.
    """
    ia=list(ids_a);ib=list(ids_b)
    a=np.asarray(coordinates_a,float);b=np.asarray(coordinates_b,float)
    if (len(set(ia))!=len(ia) or len(set(ib))!=len(ib) or a.ndim!=2 or b.ndim!=2
        or a.shape[0]!=len(ia) or b.shape[0]!=len(ib) or a.shape[1]!=b.shape[1]
        or not np.isfinite(a).all() or not np.isfinite(b).all() or tolerance<0):
        raise ValueError("unique labels, finite aligned coordinates and nonnegative tolerance required")
    da={k:i for i,k in enumerate(ia)};db={k:i for i,k in enumerate(ib)}
    out=[]
    for key in sorted(set(ia)&set(ib),key=str):
        distance=float(np.linalg.norm(a[da[key]]-b[db[key]]))
        out.append({"id":key,"coordinate_distance":distance,"accepted":bool(distance<=tolerance)})
    return out


def global_assignment_margins(reference,candidate,**match_kwargs):
    """Increase in globally optimal assignment cost when each used edge is forbidden.

    Global margins measure assignment uniqueness *under chosen costs/gates*, not
    probability of mode identity. Only one unmatched dummy per reference is allowed.
    """
    r=match_modes(reference,candidate,**match_kwargs)
    unmatched_cost=float(match_kwargs.get("unmatched_cost",.6))
    min_mac=float(match_kwargs.get("min_mac",.6))
    max_shift=float(match_kwargs.get("max_relative_shift",.2))
    raw=np.asarray(r["cost"],float)
    n,m=raw.shape
    big=1e9
    valid=(r["mac"]>=min_mac)&(r["relative_shift"]<=max_shift)&(raw<unmatched_cost)
    matrix=np.full((n,m+n),big)
    matrix[:,:m]=np.where(valid,raw,big)
    matrix[np.arange(n),m+np.arange(n)]=unmatched_cost
    rows,cols=linear_sum_assignment(matrix)
    total=float(np.sum(matrix[rows,cols]))
    if np.any(matrix[rows,cols]>=big):raise ValueError("no feasible baseline assignment")
    edges={int(i):int(j) for i,j in zip(rows,cols)}
    output=[]
    for i in range(n):
        tmp=matrix.copy(); tmp[i,edges[i]]=big
        rr,cc=linear_sum_assignment(tmp)
        new=float(np.sum(tmp[rr,cc]))
        gap=float("inf") if np.any(tmp[rr,cc]>=big) else max(0.,new-total)
        output.append({"reference":i,"candidate":None if edges[i]>=m else edges[i],
                       "global_gap":gap})
    return output
