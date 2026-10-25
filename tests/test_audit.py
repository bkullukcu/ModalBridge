import unittest
import numpy as np
from modalbridge import ModeSet
from modalbridge.audit import coordinate_overlap_audit,global_assignment_margins

class AuditTests(unittest.TestCase):
    def test_same_label_wrong_coordinate_rejected(self):
        a=coordinate_overlap_audit(["p1","p2"],[[0,0],[.02,0]],
                                   ["p2","p1"],[[.021,0],[0,0]],tolerance=1e-5)
        self.assertTrue(next(x for x in a if x["id"]=="p1")["accepted"])
        self.assertFalse(next(x for x in a if x["id"]=="p2")["accepted"])
    def test_invalid_coordinate_alignment(self):
        with self.assertRaises(ValueError):coordinate_overlap_audit(["p","p"],[[0],[1]],["p"],[[0]])
    def test_global_assignment_positive(self):
        a=ModeSet([100,200],np.array([[1,0],[0,1],[0,0]],complex),["a","b","c"])
        b=ModeSet([100,200],np.array([[1,0],[0,1],[0,0]],complex),["a","b","c"])
        margins=global_assignment_margins(a,b)
        self.assertEqual(len(margins),2)
        self.assertTrue(all(x["global_gap"]>0 for x in margins))
    def test_unmatched_forced_unmatched(self):
        a=ModeSet([100.],np.array([[1],[0],[0]],complex),["a","b","c"])
        b=ModeSet([1000.],np.array([[0],[1],[0]],complex),["a","b","c"])
        m=global_assignment_margins(a,b)
        self.assertEqual(m[0]["candidate"],None)
        self.assertTrue(np.isinf(m[0]["global_gap"]))
