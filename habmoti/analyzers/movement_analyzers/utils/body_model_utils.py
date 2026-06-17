import numpy as np


def segment_angle(arm_data: np.ndarray, pivot_index: int, p0_index: int, p1_index: int) -> bool:
    upper_arm = arm_data[:, p0_index, :] - arm_data[:, pivot_index, :]
    lower_arm = arm_data[:, p1_index, :] - arm_data[:, pivot_index, :]
    upper_arm_length = np.linalg.norm(upper_arm, axis=1)
    lower_arm_length = np.linalg.norm(lower_arm, axis=1)
    dot_product = np.einsum("ij,ij->i", upper_arm, lower_arm)
    cos_angle = dot_product / (upper_arm_length * lower_arm_length + 1e-8)
    angle = np.arccos(np.clip(cos_angle, -1.0, 1.0))
    return angle
