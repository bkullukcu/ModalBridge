"""Explicit vector-frame and laser line-of-sight operations.

Every transform must be derived from measured sensor/beam geometry. A fitted
point-cloud registration is not evidence of a correct sensor-axis mapping.
"""
from __future__ import annotations
import numpy as np

__all__ = ["rotate_vector_responses", "project_line_of_sight", "validate_line_of_sight_pair"]


def _rotations(rotation, n_points, tolerance):
    r = np.asarray(rotation, dtype=float)
    if r.shape == (3, 3):
        r = np.broadcast_to(r, (n_points, 3, 3))
    if r.shape != (n_points, 3, 3) or not np.isfinite(r).all():
        raise ValueError("rotation must be finite (3,3) or (points,3,3)")
    if not np.isfinite(tolerance) or tolerance <= 0:
        raise ValueError("rotation tolerance must be finite and positive")
    identity = r @ np.swapaxes(r, -2, -1)
    if not np.allclose(identity, np.eye(3), atol=tolerance, rtol=0):
        raise ValueError("rotation must be orthonormal")
    if not np.allclose(np.linalg.det(r), 1.0, atol=tolerance, rtol=0):
        raise ValueError("rotation must be proper (determinant +1)")
    return r


def _vectors(response):
    v = np.asarray(response, dtype=complex)
    if v.ndim != 3 or v.shape[1] != 3 or min(v.shape) == 0 or not np.isfinite(v).all():
        raise ValueError("finite complex (points,3,shapes) vectors required")
    return v


def _unit_directions(direction, n_points, tolerance):
    d = np.asarray(direction, dtype=float)
    if d.shape != (n_points, 3) or not np.isfinite(d).all():
        raise ValueError("finite (points,3) beam direction vectors required")
    norms = np.linalg.norm(d, axis=1)
    if not np.isfinite(tolerance) or tolerance < 0 or not np.allclose(norms, 1.0, atol=tolerance, rtol=0):
        raise ValueError("beam directions must be unit length within tolerance")
    return d


def rotate_vector_responses(local_response, rotation, tolerance=1e-8):
    """Convert local 3D complex response components to the common global frame.

    Input shape: (points,3,shapes). Rotation maps local row vectors to
    global row vectors, v_global[p] = v_local[p] @ R[p]. Geometry/axes
    are not inferred from the signals. Coordinate registration from
    point-cloud fiducials does not by itself validate R as a sensor
    orientation. Returns an array of the same shape.
    """
    v = _vectors(local_response)
    r = _rotations(rotation, v.shape[0], tolerance)
    return np.einsum("pim,pij->pjm", v, r)


def project_line_of_sight(global_response, beam_direction, tolerance=1e-6):
    """Predict signed 1D LDV observations from known 3D global responses.

    Requires calibrated beam orientations for every point and known
    global 3D vectors. A single measured LOS scalar *cannot* be inverted
    to reconstruct an arbitrary 3D vector.
    """
    v = _vectors(global_response)
    d = _unit_directions(beam_direction, v.shape[0], tolerance)
    return np.einsum("pim,pi->pm", v, d)


def validate_line_of_sight_pair(reference_directions, candidate_directions,
                                maximum_angle_degrees=1.0, unit_tolerance=1e-6):
    """Reject incompatible scan beams rather than silently comparing LOS shapes.

    Assumes reference and candidate points are already physically aligned and
    both directions use one shared coordinate system. The default 1-degree
    angle is an *input-audit tolerance*, not a universal calibration limit.
    """
    a = np.asarray(reference_directions, float)
    b = np.asarray(candidate_directions, float)
    if a.ndim != 2 or a.shape[1] != 3 or a.shape != b.shape:
        raise ValueError("equal (points,3) direction arrays required")
    if not np.isfinite(maximum_angle_degrees) or not (0 <= maximum_angle_degrees <= 180):
        raise ValueError("angle tolerance must be between 0 and 180 degrees")
    a = _unit_directions(a, len(a), unit_tolerance)
    b = _unit_directions(b, len(b), unit_tolerance)
    angles = np.rad2deg(np.arccos(np.clip(np.sum(a*b, axis=1), -1.0, 1.0)))
    if np.any(angles > maximum_angle_degrees):
        raise ValueError("incompatible line-of-sight beam orientations")
    return {"maximum_angle_degrees": float(np.max(angles)),
            "per_point_angle_degrees": angles}
