import numpy as np,pytest
from modalbridge.benchmarks import rigid_transform_from_fiducials,apply_rigid_transform,frequency_only_assignment,compare_to_frequency_only
from modalbridge import ModeSet

def test_known_rigid_transform():
    p=np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,1]],float)
    r=np.array([[0,-1,0],[1,0,0],[0,0,1]],float)
    q=p@r+np.array([4,3,-2])
    tr=rigid_transform_from_fiducials(p,q)
    assert tr['proper_rotation'] and tr['rms_residual']<1e-10
    assert np.allclose(apply_rigid_transform(q,tr),p,atol=1e-10)

def test_collinear_rejected():
    with pytest.raises(ValueError):rigid_transform_from_fiducials(np.zeros((3,3)),np.zeros((3,3)))

def test_mac_baseline_distinction():
    rng=np.random.default_rng(42)
    q,_=np.linalg.qr(rng.normal(size=(30,5)))
    a=ModeSet([50,70,95],q[:,:3],tuple(range(30)))
    b=ModeSet([51,60,74,98],np.column_stack([q[:,4],q[:,0],q[:,1],q[:,2]]),tuple(range(30)))
    out=compare_to_frequency_only(a,b)
    assert out[0]['mac_candidate']==1 and out[0]['frequency_candidate']==0
    assert out[0]['disagrees']
