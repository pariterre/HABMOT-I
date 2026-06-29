from dataclasses import dataclass
import logging
from typing import override

import numpy as np
import numpy.typing as npt

from .data_movement_analyzer import Axes, DataMovementAnalyzer, HabmotCriteria
from .utils.body_model_utils import joint_angle
from .utils.jump_utils import JumpIndices, compute_jump_indices

_logger = logging.getLogger(__name__)


@dataclass
class HabmotCriteriaHorizontalJump(HabmotCriteria):
    knees_are_flexed_and_arms_are_back_prior_to_takeoff: bool = False
    hands_are_extended_and_above_head: bool = False
    feet_are_together: bool = False
    hands_are_forced_downward_at_landing: bool = False

    def __str__(self) -> str:
        return f"""#####################
Horizontal jump analysis results:
  1. Knees are flexed and arms are back prior to takeoff: {self.knees_are_flexed_and_arms_are_back_prior_to_takeoff}
  2. Hands are extended and above head: {self.hands_are_extended_and_above_head}
  3. Feet are together: {self.feet_are_together}
  4. Hands are forced downward at landing: {self.hands_are_forced_downward_at_landing}
#####################"""

    def to_dict(self) -> dict:
        return {
            "knees_are_flexed_and_arms_are_back_prior_to_takeoff": self.knees_are_flexed_and_arms_are_back_prior_to_takeoff,
            "hands_are_extended_and_above_head": self.hands_are_extended_and_above_head,
            "feet_are_together": self.feet_are_together,
            "hands_are_forced_downward_at_landing": self.hands_are_forced_downward_at_landing,
        }


class HorizontalJumpAnalyzer(DataMovementAnalyzer):
    def __init__(self, show_debug_graphs: bool = False) -> None:
        super().__init__()
        self._criteria: HabmotCriteriaHorizontalJump | None = None
        self._show_debug_graphs = show_debug_graphs

    @property
    @override
    def name(self) -> str:
        return "Horizontal jump"

    @property
    @override
    def criteria(self) -> HabmotCriteria | None:
        return self._criteria

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
        jump_indices = compute_jump_indices(
            body_model=self._habmoti.device.body_model, frames=self._data_centered, threshold=0.1
        )

        # Proceed to the analyses
        is_success = self._compute_knees_are_flexed_and_arms_are_back_prior_to_takeoff(jump_indices)
        self._criteria.knees_are_flexed_and_arms_are_back_prior_to_takeoff = is_success

        is_success = self._compute_hands_are_extended_and_above_head(jump_indices)
        self._criteria.hands_are_extended_and_above_head = is_success

        is_success = self._compute_feet_are_together(jump_indices)
        self._criteria.feet_are_together = is_success

        is_success = self._compute_hands_are_forced_downward_at_landing(jump_indices)
        self._criteria.hands_are_forced_downward_at_landing = is_success

        # Print the results to the console
        _logger.info(f"\n{self._criteria}")

        if self._show_debug_graphs:
            self.show_data(blocking=False, jump_indices=jump_indices)

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
            target = 90 * np.pi / 180  # 90 degrees
            tolerance = 10 * np.pi / 180  # 10 degrees
            angles = joint_angle(data[instant, :, :], pivot_index=knee, p0_index=hip, p1_index=ankle)
            return (angles > target - tolerance) & (angles < target + tolerance)

        def arm_is_extended(data: np.ndarray, instant: int) -> npt.NDArray[np.bool_]:
            target = 180 * np.pi / 180  # 180 degrees
            tolerance = 10 * np.pi / 180  # 10 degrees in radians
            angles = joint_angle(data[instant, :, :], pivot_index=shoulder, p0_index=elbow, p1_index=hip)
            return (angles > target - tolerance) & (angles < target + tolerance)

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
        jump_successful = left_is_success & right_is_success

        return sum(jump_successful) == len(jump_indices)

    def _compute_hands_are_extended_and_above_head(self, jump_indices: tuple[JumpIndices]) -> bool:
        joint_centers = np.array([data.body_kinematics.joint_centers for data in self._data_centered])
        mid_jump = [jump[1] - 1 for jump in jump_indices]

        index_of = lambda name: self._habmoti.device.body_model.from_name(name)
        shoulder, elbow, wrist, hip = 0, 1, 2, 3
        joints = ["shoulder", "elbow", "wrist", "hip"]
        left_arm = joint_centers[:, [index_of(f"left_{name}") for name in joints], :]
        right_arm = joint_centers[:, [index_of(f"right_{name}") for name in joints], :]
        neck_data = joint_centers[:, index_of("neck"), :]

        def arm_is_extended(arm_data: np.ndarray, instant: int) -> npt.NDArray[np.bool_]:
            target = 0 * np.pi / 180  # 0 degrees
            tolerance = 10 * np.pi / 180  # 10 degrees in radians
            angles = joint_angle(arm_data[instant, :, :], pivot_index=shoulder, p0_index=elbow, p1_index=hip)
            is_extended = (angles > target - tolerance) & (angles < target + tolerance)
            return is_extended

        def arm_is_above_head(arm_data: np.ndarray, instant: int) -> npt.NDArray[np.bool_]:
            is_above_head = arm_data[instant, wrist, Axes.VERTICAL.value] > neck_data[instant, Axes.VERTICAL.value]
            return is_above_head

        def arm_task_is_successful(arm_data: np.ndarray) -> npt.NDArray[np.bool_]:
            return arm_is_extended(arm_data, instant=mid_jump) & arm_is_above_head(arm_data, instant=mid_jump)

        left_is_success = arm_task_is_successful(left_arm)
        right_is_success = arm_task_is_successful(right_arm)
        jump_successful = left_is_success & right_is_success

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

    def _compute_hands_are_forced_downward_at_landing(self, jump_indices: tuple[JumpIndices]) -> bool:
        joint_centers = np.array([data.body_kinematics.joint_centers for data in self._data_centered])

        end = [jump[2] - 1 for jump in jump_indices]
        index_of = lambda name: self._habmoti.device.body_model.from_name(name)
        hands_height = joint_centers[:, [index_of("left_wrist"), index_of("right_wrist")], Axes.VERTICAL.value]

        hands_velocity = np.gradient(hands_height, axis=0)
        hands_height_are_forced_downward = hands_velocity[end, :] < 0
        return hands_height_are_forced_downward.all()

    @override
    def show_data(self, blocking: bool = False, jump_indices: tuple[JumpIndices] = None) -> None:
        from matplotlib import pyplot as plt

        if jump_indices is None:
            jump_indices = compute_jump_indices(
                body_model=self._habmoti.device.body_model, frames=self._data_centered, threshold=0.1
            )

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
        super().show_data(blocking=blocking, fig=fig, t=t, line=line)

    @override
    def _update_extra_show_data(self, index: int, fig, t: np.ndarray, line) -> bool:
        from matplotlib import pyplot as plt

        if not plt.fignum_exists(fig.number):
            return False

        x = t[index]
        line.set_xdata([x, x])

        plt.pause((t[index] - t[index - 1]) if index > 0 else 1.0)
        return True
