"""Standalone known-correspondence complex mode/response matching demo."""
import numpy as np
from modalbridge import ModeSet, match_modes

ids=("p1_x","p2_x","p3_x","p4_x")
reference=ModeSet([40., 75.], np.eye(4,2, dtype=complex), ids)
candidate=ModeSet([76., 41.], np.eye(4,2, dtype=complex)[:,[1,0]] * (1j), ids)
r=match_modes(reference,candidate)
assert [p["candidate"] for p in r["pairs"]]==[1,0]
print("ModalBridge synthetic correspondence OK: candidate order [1, 0]")
