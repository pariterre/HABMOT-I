from enum import Enum

import numpy as np


class AxisName(Enum):
    X = "x"
    Y = "y"
    Z = "z"


def create_system_of_axes(
    origin: np.ndarray,
    first_axis: np.ndarray,
    second_axis: np.ndarray,
    first_axis_name: AxisName,
    second_axis_name: AxisName,
    keep_axis: AxisName,
) -> np.ndarray:
    """
    Create a new array with only the specified axes, and the origin axis if it is not already included.
    The new array will have the same number of frames as the original array, but only the specified axes.
    The order of the axes in the new array will be: origin axis (if not already included), first_axis, second_axis, and then any remaining axes up to keep_axes.

    :param origin: The origin joint positions array of shape (num_frames, num_dimensions).
    :param first_axis: The first axis vector array of shape (num_frames, num_dimensions).
    :param second_axis: The second axis vector array of shape (num_frames, num_dimensions).
    :param keep_axis: The axis to keep (AxisName.X, AxisName.Y, AxisName.Z).
    :return: A new array of shape (num_frames, keep_axes) containing only the specified axes.
    """

    if first_axis_name == second_axis_name:
        raise ValueError("First axis and second axis cannot have the same name.")
    if keep_axis not in (first_axis_name, second_axis_name):
        raise ValueError("Keep axis must be either the first axis or second axis.")

    if first_axis_name == AxisName.X and second_axis_name == AxisName.Y:
        x_axis = first_axis
        y_axis = second_axis
        z_axis = np.cross(x_axis, y_axis)
        axis_to_recompute = AxisName.Y if keep_axis == AxisName.X else AxisName.X
    elif first_axis_name == AxisName.X and second_axis_name == AxisName.Z:
        x_axis = first_axis
        z_axis = second_axis
        y_axis = np.cross(z_axis, x_axis)
        axis_to_recompute = AxisName.Z if keep_axis == AxisName.X else AxisName.X
    elif first_axis_name == AxisName.Y and second_axis_name == AxisName.X:
        y_axis = first_axis
        x_axis = second_axis
        z_axis = np.cross(x_axis, y_axis)
        axis_to_recompute = AxisName.X if keep_axis == AxisName.Y else AxisName.Y
    elif first_axis_name == AxisName.Y and second_axis_name == AxisName.Z:
        y_axis = first_axis
        z_axis = second_axis
        x_axis = np.cross(y_axis, z_axis)
        axis_to_recompute = AxisName.Z if keep_axis == AxisName.Y else AxisName.Y
    elif first_axis_name == AxisName.Z and second_axis_name == AxisName.X:
        z_axis = first_axis
        x_axis = second_axis
        y_axis = np.cross(z_axis, x_axis)
        axis_to_recompute = AxisName.X if keep_axis == AxisName.Z else AxisName.Z
    elif first_axis_name == AxisName.Z and second_axis_name == AxisName.Y:
        z_axis = first_axis
        y_axis = second_axis
        x_axis = np.cross(y_axis, z_axis)
        axis_to_recompute = AxisName.Y if keep_axis == AxisName.Z else AxisName.Z
    else:
        raise ValueError("Invalid axis names.")

    if axis_to_recompute == AxisName.X:
        x_axis = np.cross(y_axis, z_axis)
    elif axis_to_recompute == AxisName.Y:
        y_axis = np.cross(z_axis, x_axis)
    elif axis_to_recompute == AxisName.Z:
        z_axis = np.cross(x_axis, y_axis)

    x_axis /= np.linalg.norm(x_axis)
    y_axis /= np.linalg.norm(y_axis)
    z_axis /= np.linalg.norm(z_axis)

    axes = np.eye(4)
    axes[:3, :] = np.array([x_axis, y_axis, z_axis, origin]).T

    return axes


def transpose_axes(axes: np.ndarray) -> np.ndarray:
    """
    Transpose the axes of the given array. This is useful for converting between different coordinate systems.

    :param axes: A 4x4 array representing the axes to transpose.
    :return: A new 4x4 array with the axes transposed.
    """
    rotation = axes[:3, :3]
    translation = axes[:3, 3]

    out = np.eye(4)
    out[:3, :3] = rotation.T
    out[:3, 3] = -rotation.T @ translation
    return out
