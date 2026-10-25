import numpy as np
import pytest
from modalbridge import rigid_registration,subspace_similarity,selective_metrics

def test_rigid_rotation_and_translation():
    x=np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,1.]])
    R=np.array([[0,-1,0],[1,0,0],[0,0,1]])
    y=x@R+[2,3,4]
    t=rigid_registration(x,y)
    np.testing.assert_allclose(x@t['rotation']+t['translation'],y,atol=1e-12)
    with pytest.raises(ValueError):rigid_registration(x[:2],y[:2])

def test_group_rotation_vs_single_mac():
    a=np.eye(4,dtype=complex)[:,:2];b=a@np.array([[1,1],[-1,1]])/np.sqrt(2)
    assert subspace_similarity(a,b)['minimum_squared_cosine']>1-1e-12
    with pytest.raises(ValueError):subspace_similarity(a,np.zeros_like(a))

def test_selective_errors_and_rejections():
    m=selective_metrics([0,2,None,None],[0,1,None,3])
    assert m['coverage']==.5 and m['false_match_fraction']==.5
    assert m['correct_rejections']==1 and m['missed_counterparts']==1
    assert np.isnan(selective_metrics([None],[0])['false_match_fraction'])
