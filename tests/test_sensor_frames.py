"""Numerical contract tests for explicit sensor-frame transformations."""
import numpy as np
import pytest
from modalbridge.sensor_frames import (
    rotate_vector_responses, project_line_of_sight, validate_line_of_sight_pair
)


def test_correct_rotation_and_round_trip():
    local = np.array([[[1+1j, 2], [2-1j, 3], [4, 5]]], complex)
    rotation = np.array([[0., 1., 0.], [-1., 0., 0.], [0., 0., 1.]])
    global_values = rotate_vector_responses(local, rotation)
    np.testing.assert_allclose(global_values[0, :, 0], [-(2-1j), 1+1j, 4])
    np.testing.assert_allclose(rotate_vector_responses(global_values, rotation.T), local)


def test_point_specific_rotations():
    local = np.zeros((2, 3, 1), complex)
    local[:, 0, 0] = 1
    r = np.stack([np.eye(3), [[0, 1, 0], [-1, 0, 0], [0, 0, 1]]])
    result = rotate_vector_responses(local, r)
    np.testing.assert_allclose(result[:, :, 0], [[1, 0, 0], [0, 1, 0]])


def test_line_of_sight_projection_and_direction_check():
    field = np.array([[[1+2j], [2], [3]], [[4], [5], [6]]])
    directions = np.array([[1., 0, 0], [0, 0, 1.]])
    np.testing.assert_allclose(project_line_of_sight(field, directions)[:, 0], [1+2j, 6])
    result = validate_line_of_sight_pair(directions, directions)
    assert result["maximum_angle_degrees"] < 1e-10


def test_reject_reflection_and_shear():
    x = np.ones((1, 3, 1))
    with pytest.raises(ValueError, match="proper"):
        rotate_vector_responses(x, np.diag([-1, 1, 1]))
    with pytest.raises(ValueError, match="orthonormal"):
        rotate_vector_responses(x, np.diag([2., 1., 1.]))


def test_reject_non_unit_and_misaligned_beams():
    x = np.ones((1, 3, 1))
    with pytest.raises(ValueError, match="unit length"):
        project_line_of_sight(x, np.array([[2., 0, 0]]))
    with pytest.raises(ValueError, match="incompatible"):
        validate_line_of_sight_pair([[1., 0, 0]], [[0., 1, 0]])


def test_reject_nonfinite_and_invalid_shapes():
    with pytest.raises(ValueError):
        rotate_vector_responses(np.ones((3, 3)), np.eye(3))
    with pytest.raises(ValueError):
        rotate_vector_responses(np.ones((2, 3, 1)), np.full((3, 3), np.nan))
