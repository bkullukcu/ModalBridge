# Frequently asked questions

**Can measurements use different channel orders?**

Yes. Each channel is identified by a physical point and measurement direction. ModalBridge aligns the two matrices using these DOF identifiers.

**How should I interpret a high MAC value?**

MAC measures spatial similarity between complex vectors on aligned DOFs. Review it alongside candidate frequencies, mode-identification results and the structural test configuration.

**What should I do when the coordinate frame has changed?**

Transform both measurements into a common physical frame before importing them. The input audit then checks declared frame labels and any available point coordinates.

**Why does the matcher leave some responses unmatched?**

The assignment includes an unmatched option. It is selected when candidate pairs fall outside the specified MAC or frequency thresholds, or when the combined assignment favours leaving a reference free.

**How were the README figures generated?**

`python examples/make_readme_figures.py` builds complex synthetic response vectors with a known permutation and one deliberately unmatched reference. The example exercises the same matching functions used for imported measurements.
