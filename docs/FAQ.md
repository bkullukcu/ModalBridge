# FAQ

**Can two files be compared if their sensor order differs?**

Yes, if each row has a unique physical DOF ID and the same ID means the same physical point *and* measurement direction. The library aligns by identifiers rather than row positions.

**Does a large MAC mean the structure is healthy?**

No. MAC describes similarity between spatial vectors on comparable DOFs. It does not by itself identify damage or establish that two response vectors are the same eigenmode.

**What if the measuring coordinate systems have changed?**

The input audit checks declared frames and coordinates. Resolve physical registration and sensor-direction differences before matching. The command-line input audit does not transform one coordinate system into the other.

**Why can a reference remain unmatched?**

Assignment includes a rejection alternative. A candidate may fail the MAC threshold, exceed the frequency shift bound or be less defensible than leaving the reference unmatched.

**Are the README figures measured modal results?**

No. The example constructs complex orthogonal response vectors and deliberately omits one correspondence. It is a deterministic software demonstration only.
