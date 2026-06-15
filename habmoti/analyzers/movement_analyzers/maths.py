import numpy as np

def create_system_of_axes(origin: np.ndarray, first_axis: np.ndarray, second_axis: np.ndarray, keep_axis: int) -> np.ndarray:
    """
    Create a new array with only the specified axes, and the origin axis if it is not already included.
    The new array will have the same number of frames as the original array, but only the specified axes.
    The order of the axes in the new array will be: origin axis (if not already included), first_axis, second_axis, and then any remaining axes up to keep_axes.

    :param origin: The origin joint positions array of shape (num_frames, num_dimensions).
    :param first_axis: The first axis vector array of shape (num_frames, num_dimensions).
    :param second_axis: The second axis vector array of shape (num_frames, num_dimensions).
    :param keep_axis: The index of the axis to keep (0 for first axis, 1 for second axis).
    :return: A new array of shape (num_frames, keep_axes) containing only the specified axes.
    """
    
    third_axis = np.cross(first_axis, second_axis)

    if keep_axis == 0:
        second_axis = np.cross(third_axis, first_axis)
    else:
        first_axis = np.cross(second_axis, third_axis)

    first_axis /= np.linalg.norm(first_axis, axis=1, keepdims=True)
    second_axis /= np.linalg.norm(second_axis, axis=1, keepdims=True)
    third_axis /= np.linalg.norm(third_axis, axis=1, keepdims=True)

    axes = np.ndarray((origin.shape[0], 4, 4))
    for i in range(origin.shape[0]):
        axes[i] = np.eye(4)
        axes[i, :3, :3] = [first_axis[i, :], second_axis[i, :], third_axis[i, :]]
        axes[i, :3, 3] = origin[i, :]

    return axes