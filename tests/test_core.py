import unittest
import numpy as np
from modalbridge import *
from modalbridge.io import parse_polytec

class TestMatching(unittest.TestCase):
 def setUp(self):
  self.a=ModeSet([40,70,100],np.eye(6,3),tuple('abcdef'))
 def test_phase_invariance(self):np.testing.assert_allclose(complex_mac(self.a.shapes,self.a.shapes*3j),np.eye(3),atol=1e-12)
 def test_permuted_dof_alignment(self):
  b=ModeSet([40,70,100],self.a.shapes[::-1],self.a.dof_ids[::-1]);r=match_modes(self.a,b);self.assertEqual([p['candidate'] for p in r['pairs']],[0,1,2])
 def test_frequency_crossing(self):
  b=ModeSet([71,41,101],self.a.shapes[:,[1,0,2]],self.a.dof_ids);r=match_modes(self.a,b);self.assertEqual([p['candidate'] for p in r['pairs']],[1,0,2])
 def test_unmatched(self):
  b=ModeSet([400],self.a.shapes[:,[0]],self.a.dof_ids);self.assertTrue(all(p['status']=='unmatched' for p in match_modes(self.a,b)['pairs']))
 def test_competing_reference(self):
  b=ModeSet([40],np.ones((6,1)),self.a.dof_ids);r=match_modes(self.a,b,min_mac=0,max_relative_shift=3,unmatched_cost=2);self.assertEqual(sum(p['candidate'] is not None for p in r['pairs']),1)
 def test_ambiguous_duplicate_candidates(self):
  b=ModeSet([40,40],self.a.shapes[:,[0,0]],self.a.dof_ids);self.assertEqual(match_modes(self.a,b)['pairs'][0]['status'],'ambiguous')
 def test_cmif_single_reference(self):
  h=np.ones((10,6,1),complex);s=cmif(h);self.assertEqual(s.shape,(10,1));np.testing.assert_allclose(s,np.sqrt(6))
 def test_duplicate_ids(self):
  with self.assertRaises(ValueError):ModeSet([1],np.ones((3,1)),('a','a','b'))
 def test_stability(self):
  rng=np.random.default_rng(1);q=np.linalg.qr(rng.normal(size=(20,3)))[0];a=ModeSet([40,70,100],q,tuple(map(str,range(20))));r=assignment_stability(a,a,n_boot=20);np.testing.assert_allclose(r['frequency'].sum(1),1);np.testing.assert_allclose(np.diag(r['frequency'][:,:3]),1)
 def test_bad_export(self):
  with self.assertRaises(ValueError):parse_polytec('not a measurement')
 def test_zero_shape(self):
  with self.assertRaises(ValueError):ModeSet([1],np.zeros((3,1)),('a','b','c'))
if __name__=='__main__':unittest.main()
