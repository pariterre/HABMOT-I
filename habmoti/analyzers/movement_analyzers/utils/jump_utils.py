from scipy.signal import find_peaks

import numpy as np

from ....data.body_kinematics import BodyModel
from ....data.frame_data import FrameData

type JumpIndices = tuple[float, float, float]


def compute_jump_indices(body_model: BodyModel, frames: list[FrameData]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    data = np.array([data.body_kinematics.joint_centers for data in frames])
    left_foot_index = body_model.from_name("left_ankle")
    right_foot_index = body_model.from_name("right_ankle")

    mean_feet_height = np.mean(data[:, [left_foot_index, right_foot_index], 1], axis=1)
    mid_jump_indices, _ = find_peaks(mean_feet_height, height=0.1)

    # Compute the velocity of the feet
    mean_foot_velocity = np.gradient(mean_feet_height)

    # Find the first time the derivative become positive before (start) and after (end) of each mid jump indices
    start_jump_indices = []
    end_jump_indices = []
    for mid in mid_jump_indices:
        start = mid - 1
        while start > 0 and mean_foot_velocity[start] > 0:
            start -= 1
        start_jump_indices.append(start)

        end = mid + 1
        while end < len(mean_foot_velocity) - 1 and mean_foot_velocity[end] < 0:
            end += 1
        end_jump_indices.append(end)

    # Make sure all jumps has a start, mid and end, and these are not edges of the recording
    valid_jump_indices = []
    for start, mid, end in zip(start_jump_indices, mid_jump_indices, end_jump_indices):
        if start < mid < end and start > 0 and end < len(frames) - 1:
            valid_jump_indices.append((start, mid, end))

    return valid_jump_indices
