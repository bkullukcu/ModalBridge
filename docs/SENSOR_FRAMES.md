# Sensor frames and physical DOFs

ModalBridge compares complex vectors only after their measurement locations **and directions** have been brought into a common physical frame. Identical point labels are not proof of identical coordinates. A coordinate-only rigid registration does not automatically rotate measured vector components.

The optional numerical helpers in `modalbridge.sensor_frames` implement explicitly provided transformations:

```python
import numpy as np
from modalbridge.sensor_frames import (
    rotate_vector_responses, project_line_of_sight,
    validate_line_of_sight_pair,
)

# x_local: (points, 3, responses) from a calibrated triaxial sensor.
# R: a proper rotation, mapping local row vectors into global row vectors.
x_global = rotate_vector_responses(x_local, R)

# LOS unit directions: (points, 3) expressed in the global frame.
# Projection predicts what a 1D scanning vibrometer measures.
v_los_predicted = project_line_of_sight(x_global, beam_unit_vectors)

# Direct comparison of two measured LOS datasets is allowed only if the
# physical scan points, frequency/reference conventions and beam directions
# agree. The check rejects incompatible directions.
audit = validate_line_of_sight_pair(ref_los_dirs, cand_los_dirs,
                                    maximum_angle_degrees=1.0)
```

## Measurement limitations

- A single scalar laser line-of-sight velocity cannot be converted into an arbitrary 3D velocity. `project_line_of_sight` maps *known 3D* fields to predicted 1D observations; it does not perform an inverse reconstruction.
- A triaxial accelerometer in a local frame needs a calibrated **proper rotation** to the global frame. Per-point rotations are supported for different sensor mounts.
- An oblique uniaxial accelerometer should be treated as a projection on its calibrated sensitivity axis. Unless suitable geometric models or three independent projections are available, its measurement must not be fabricated as an X, Y or Z component.
- Translational velocity/displacement and acceleration are **different physical quantities**. Converting one to another requires an appropriate frequency-domain model, numerical treatment and consistent calibration; this module does not assume interchangeability.
- A fitted rigid coordinate registration from matched fiducial locations can provide a geometric rotation. It is usable for response components only when the sensor axes are *known* to follow the same rigid transform; this cannot be inferred from high MAC.
- An input audit tolerance such as 1 degree or 1 micrometre is a declared laboratory criterion, not a universal physical accuracy threshold.
- Polytec imports that lack calibrated beam directions, sensor axes or frame metadata should remain marked as unresolved. Do not silently transform line-of-sight scalars into 3D global components.
