from dataclasses import dataclass
import logging
from typing import override

import numpy as np
import numpy.typing as npt

from .data_movement_analyzer import Axes, DataMovementAnalyzer
from .utils.body_model_utils import joint_angle
from .utils.jump_utils import JumpIndices, compute_jump_indices

_logger = logging.getLogger(__name__)


@dataclass
class HabmotCriteriaHorizontalJump:
    knees_are_flexed_and_arms_are_back_prior_to_takeoff: bool = False
    feet_are_together: bool = False

    def __str__(self) -> str:
        return f"""#####################
Horizontal jump analysis results:
  1. Knees are flexed and arms are back prior to takeoff: {self.knees_are_flexed_and_arms_are_back_prior_to_takeoff}
  3. Feet are together: {self.feet_are_together}
#####################"""


class HorizontalJumpAnalyzer(DataMovementAnalyzer):
    def __init__(self, show_debug_graphs: bool = False) -> None:
        super().__init__()
        self._criteria: HabmotCriteriaHorizontalJump | None = None
        self._show_debug_graphs = show_debug_graphs

    @property
    @override
    def name(self) -> str:
        return "Horizontal jump"

    @override
    def start_trial(self) -> None:
        self._criteria = HabmotCriteriaHorizontalJump()
        super().start_trial()

    @override
    def stop_trial(self) -> None:
        super().stop_trial()
        self._perform_post_trial_analysis()

    @override
    def _perform_post_trial_analysis(self) -> None:
        # Find the peaks in the mean feet y position to find the mid-jump frames
        jump_indices = compute_jump_indices(body_model=self._habmoti.device.body_model, frames=self._data_centered)

        # Proceed to the analyses
        is_success = self._compute_knees_are_flexed_and_arms_are_back_prior_to_takeoff(jump_indices)
        self._criteria.knees_are_flexed_and_arms_are_back_prior_to_takeoff = is_success

        is_success = self._compute_feet_are_together(jump_indices)
        self._criteria.feet_are_together = is_success

        # Print the results to the console
        _logger.info(f"\n{self._criteria}")

        if self._show_debug_graphs:
            self._show_data(blocking=False, jump_indices=jump_indices)

    @override
    def dispose(self) -> None:
        self._criteria = None
        super().dispose()

    def _compute_knees_are_flexed_and_arms_are_back_prior_to_takeoff(self, jump_indices: tuple[JumpIndices]) -> bool:
        joint_centers = np.array([data.body_kinematics.joint_centers for data in self._data_centered])
        prior_to_jump = [jump[0] - 1 for jump in jump_indices]

        index_of = lambda name: self._habmoti.device.body_model.from_name(name)
        hip, knee, ankle, shoulder, elbow, wrist = 0, 1, 2, 3, 4, 5
        points = ["hip", "knee", "ankle", "shoulder", "elbow", "wrist"]
        left_data = joint_centers[:, [index_of(f"left_{name}") for name in points], :]
        right_data = joint_centers[:, [index_of(f"right_{name}") for name in points], :]
        neck_data = joint_centers[:, index_of("neck"), :]

        def leg_is_flexed(data: np.ndarray, instant: int) -> npt.NDArray[np.bool_]:
            threshold_angle = 10 * np.pi / 180  # 10 degrees in radians
            angles = joint_angle(data[instant, :, :], pivot_index=knee, p0_index=hip, p1_index=ankle)
            return (angles > np.pi / 2 - threshold_angle) & (angles < np.pi / 2 + threshold_angle)

        def arm_is_extended(data: np.ndarray, instant: int) -> npt.NDArray[np.bool_]:
            threshold_angle = 10 * np.pi / 180  # 10 degrees in radians
            angles = joint_angle(data[instant, :, :], pivot_index=shoulder, p0_index=elbow, p1_index=hip)
            return (angles > np.pi - threshold_angle) & (angles < np.pi + threshold_angle)

        def arm_is_behind_back(data: np.ndarray, instant: int) -> npt.NDArray[np.bool_]:
            frontward = Axes.FRONTAL.value
            return data[instant, wrist, frontward] < neck_data[instant, frontward]

        def task_is_successful(leg_data: np.ndarray) -> bool:
            return (
                leg_is_flexed(leg_data, instant=prior_to_jump)
                & arm_is_extended(leg_data, instant=prior_to_jump)
                & arm_is_behind_back(leg_data, instant=prior_to_jump)
            )

        left_is_success = task_is_successful(left_data)
        right_is_success = task_is_successful(right_data)
        jump_successful = left_is_success | right_is_success

        return sum(jump_successful) == len(jump_indices)

    def _compute_feet_are_together(self, jump_indices: tuple[JumpIndices]) -> bool:
        joint_centers = np.array([data.body_kinematics.joint_centers for data in self._data_centered])

        axis_index = Axes.VERTICAL.value
        index_of = lambda name: self._habmoti.device.body_model.from_name(name)
        left_foot_height = joint_centers[:, index_of("left_ankle"), axis_index]
        right_foot_height = joint_centers[:, index_of("right_ankle"), axis_index]

        start = [jump[0] for jump in jump_indices]
        end = [jump[2] for jump in jump_indices]
        indices = start + end
        feet_distance = np.abs(left_foot_height[indices] - right_foot_height[indices])
        return max(feet_distance) < 0.1  # Threshold of 10 cm between the feet at mid-jump

    def _show_data(self, blocking: bool, jump_indices: tuple[JumpIndices]) -> None:
        from matplotlib import pyplot as plt

        t0 = self._data_centered[0].timestamp if self._data_centered else 0
        t = np.array([data.timestamp - t0 for data in self._data_centered]) / 1000.0

        axis_index = Axes.VERTICAL.value
        joint_centers = np.array([data.body_kinematics.joint_centers for data in self._data_centered])
        left_foot_height = joint_centers[:, self._habmoti.device.body_model.from_name("left_ankle"), axis_index]
        right_foot_height = joint_centers[:, self._habmoti.device.body_model.from_name("right_ankle"), axis_index]
        mean_feet_height = (left_foot_height + right_foot_height) / 2

        mid_jump_indices = [jump[1] for jump in jump_indices]

        fig = plt.figure("Horizontal Jump Analysis")
        plt.plot(t, left_foot_height, label="Left Foot Y")
        plt.plot(t, right_foot_height, label="Right Foot Y")
        plt.plot(t, mean_feet_height, label="Mean Feet Y", linestyle="--")
        [plt.axvline(x=t[index], color="g") for index in mid_jump_indices]
        plt.legend()

        plt.title("Horizontal Jump Analysis")
        plt.xlabel("Time (s)")
        plt.ylabel("Height Position")
        plt.pause(0.1)

        # Plot a vertical line a index to show where we are in the data
        line = plt.axvline(x=0, color="r", linestyle="--")
        super()._show_data(blocking=blocking, fig=fig, t=t, line=line)

    def _update_extra_show_data(self, index: int, fig, t: np.ndarray, line) -> bool:
        from matplotlib import pyplot as plt

        if not plt.fignum_exists(fig.number):
            return False

        x = t[index]
        line.set_xdata([x, x])

        plt.pause((t[index] - t[index - 1]) if index > 0 else 1.0)
        return True
