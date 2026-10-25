"""Synthetic numerical checks; does not redistribute original ETH raw recordings."""
import numpy as np
import pytest
from modalbridge.ethzurich import mimo_h1_x, h1, sample_complex_shape, FRFRecord, TEST_META,PIEZO_DOFS,peak_candidates
from modalbridge.core import complex_mac


def test_mimo_x_channel_recovers_truth_and_is_gy_scale_invariant():
    rng=np.random.default_rng(92)
    fs=128.; n=131072
    gx=rng.normal(size=n)
    gy=rng.normal(size=n)
    y=1.8*gx + .55*gy + .03*rng.normal(size=n)
    f,h,coh=mimo_h1_x(y,gx,gy,fs,nperseg=4096)
    region=(f>2)&(f<30)
    assert abs(np.median(h[0,region].real)-1.8)<.03
    assert np.median(abs(h[0,region].imag))<.04
    assert np.median(coh[0,region])>.995
    _,rescaled,_=mimo_h1_x(y,gx,gy*100.,fs,nperseg=4096)
    np.testing.assert_allclose(h,rescaled,rtol=1e-10,atol=1e-10)


def test_single_reference_h1_is_complex_and_causal_phase():
    rng=np.random.default_rng(0);x=rng.normal(size=65536)
    y=np.roll(x,3); y[:3]=0
    f,h,c=h1(y,x,fs=64,nperseg=4096)
    # A causal three-sample time delay produces exp(-j*2*pi*f*3/fs).
    ix=np.argmin(abs(f-4.0)); expected=np.exp(-2j*np.pi*f[ix]*3/64)
    assert abs(h[0,ix]-expected)<.03
    assert c[0,ix]>.97


def test_physical_signs_and_state_labels():
    assert all(TEST_META[t][0]=='baseline' for t in (11,12,13,14))
    assert all(TEST_META[t][0]=='damaged' for t in (15,16,17))
    assert PIEZO_DOFS['2.1']['C']==(73,-1)
    assert PIEZO_DOFS['2.2']['E']==(82,1)


def test_complex_mac_gauge_invariance_on_interpolated_shapes():
    f=np.array([1.,2.,3.]);shapes=np.array([[1+1j,2+2j,1], [2,1j,2], [3j,2+0j,1]],complex)
    r=FRFRecord(11,'test',f,(73,74,76),shapes,np.ones_like(shapes).real,'ref',100,20)
    a=sample_complex_shape(r,2.,(73,74,76));b=sample_complex_shape(r,2.,(76,73,74))
    np.testing.assert_allclose(b,a[[2,0,1]])
    val=complex_mac(a[:,None],(a*np.exp(1j*1.72))[:,None])[0,0]
    assert np.isclose(val,1.)


def test_peak_candidates_windows_and_coherence():
    f=np.linspace(.1,12,5000)
    h=np.zeros((3,len(f)),complex)
    for i,center in enumerate((1.68,4.18,7.27,10.02)):
        h[0]+=1/(center**2-f**2+1j*.06*f)
    h[1]=h[0]*.7j;h[2]=h[0]*.3
    r=FRFRecord(11,'synthetic',f,(5,7,9),h,np.ones_like(h).real,'synthetic',200,80)
    vals=peak_candidates(r)
    for p,cen in zip(vals,(1.68,4.18,7.27,10.02)):
        assert abs(p['frequency_hz']-cen)<.055
        assert p['median_coherence']==1.
