from dataclasses import dataclass
import logging
from typing import override

import numpy as np
import numpy.typing as npt

from .utils.body_model_utils import joint_angle
from .utils.jump_utils import JumpIndices, compute_jump_indices
from .data_movement_analyzer import DataMovementAnalyzer, Axes, HabmotCriteria

_logger = logging.getLogger(__name__)


@dataclass
class HabmotCriteriaHop(HabmotCriteria):
    non_hopping_leg_swings_forward_in_pendular_fashion: bool = False
    non_hopping_leg_remains_behind: bool = False
    arms_flex_and_swing_forward: bool = False
    can_do_four_consecutive_jumps: bool = False

    def __str__(self) -> str:
        return f"""#####################
Hop analysis results:
  1. Non-hopping leg swings forward in pendular fashion: {self.non_hopping_leg_swings_forward_in_pendular_fashion}
  2. Non-hopping leg remains behind: {self.non_hopping_leg_remains_behind}
  3. Arms flex and swing forward: {self.arms_flex_and_swing_forward}
  4. Can do four consecutive jumps: {self.can_do_four_consecutive_jumps}
#####################"""

    def to_dict(self) -> dict:
        return {
            "non_hopping_leg_swings_forward_in_pendular_fashion": self.non_hopping_leg_swings_forward_in_pendular_fashion,
            "non_hopping_leg_remains_behind": self.non_hopping_leg_remains_behind,
            "arms_flex_and_swing_forward": self.arms_flex_and_swing_forward,
            "can_do_four_consecutive_jumps": self.can_do_four_consecutive_jumps,
        }


class HopAnalyzer(DataMovementAnalyzer):
    def __init__(self, show_debug_graphs: bool = False) -> None:
        super().__init__()
        self._criteria: HabmotCriteriaHop | None = None
        self._show_debug_graphs = show_debug_graphs

    @property
    @override
    def name(self) -> str:
        return "Hop"

    @property
    @override
    def criteria(self) -> HabmotCriteria | None:
        return self._criteria

    @override
    def start_trial(self) -> None:
        self._criteria = HabmotCriteriaHop()
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
        prefered_ground_foot = self._compute_prefered_ground_foot(jump_indices)

        # Proceed to the analyses
        is_success = self._compute_non_hopping_leg_swings_forward_in_pendular_fashion(jump_indices)
        self._criteria.non_hopping_leg_swings_forward_in_pendular_fashion = is_success

        is_success = self._compute_non_hopping_leg_remains_behind(prefered_ground_foot, jump_indices)
        self._criteria.non_hopping_leg_remains_behind = is_success

        is_success = self._compute_arms_flex_and_swing_forward(jump_indices)
        self._criteria.arms_flex_and_swing_forward = is_success

        best_consecutive_jumps = self._compute_consecutive_jumps(prefered_ground_foot, jump_indices)
        self._criteria.can_do_four_consecutive_jumps = best_consecutive_jumps >= 4

        # Print the results to the console
        _logger.info(f"\n{self._criteria}")

        if self._show_debug_graphs:
            self.show_data(blocking=False, jump_indices=jump_indices)

    @override
    def dispose(self) -> None:
        self._criteria = None
        super().dispose()

    def _compute_prefered_ground_foot(self, jump_indices: tuple[JumpIndices]) -> str:
        joint_centers = np.array([data.body_kinematics.joint_centers for data in self._data_centered])
        mid_jump_indices = [jump[1] for jump in jump_indices]

        axis_index = Axes.VERTICAL.value
        left_foot_height = joint_centers[:, self._habmoti.device.body_model.from_name("left_ankle"), axis_index]
        right_foot_height = joint_centers[:, self._habmoti.device.body_model.from_name("right_ankle"), axis_index]
        prefered_ground_foot = (
            "left"
            if sum(left_foot_height[mid_jump_indices] < right_foot_height[mid_jump_indices]) > len(mid_jump_indices) / 2
            else "right"
        )
        return prefered_ground_foot

    def _compute_non_hopping_leg_swings_forward_in_pendular_fashion(self, jump_indices: tuple[JumpIndices]) -> bool:
        joint_centers = np.array([data.body_kinematics.joint_centers for data in self._data_centered])
        start_jump = [jump[0] for jump in jump_indices]
        mid_jump = [jump[1] for jump in jump_indices]

        index_of = lambda name: self._habmoti.device.body_model.from_name(name)
        left_leg = joint_centers[:, [index_of("left_knee")], :]
        right_leg = joint_centers[:, [index_of("right_knee")], :]
        knee = 0

        def leg_is_moving_forward(leg_data: np.ndarray) -> npt.NDArray[np.bool_]:
            frontward = Axes.FRONTAL.value
            return leg_data[start_jump, knee, frontward] < leg_data[mid_jump, knee, frontward]

        def leg_swings_forward_in_pendular_fasion(leg_data: np.ndarray) -> npt.NDArray[np.bool_]:
            return leg_is_moving_forward(leg_data)

        left_leg_is_success = leg_swings_forward_in_pendular_fasion(left_leg)
        right_leg_is_success = leg_swings_forward_in_pendular_fasion(right_leg)
        legs_are_success = left_leg_is_success & right_leg_is_success

        return sum(legs_are_success) == len(jump_indices)

    def _compute_non_hopping_leg_remains_behind(
        self,
        prefered_ground_foot: str,
        jump_indices: tuple[JumpIndices],
    ) -> bool:
        joint_centers = np.array([data.body_kinematics.joint_centers for data in self._data_centered])

        axis_index = Axes.FRONTAL.value
        left_foot = joint_centers[:, self._habmoti.device.body_model.from_name("left_ankle"), axis_index]
        left_leg = joint_centers[:, self._habmoti.device.body_model.from_name("left_knee"), axis_index]
        right_foot = joint_centers[:, self._habmoti.device.body_model.from_name("right_ankle"), axis_index]
        right_leg = joint_centers[:, self._habmoti.device.body_model.from_name("right_knee"), axis_index]
        mid_jump_indices = [jump[1] for jump in jump_indices]

        non_hopping_leg_remains_behind = True
        for mid in mid_jump_indices:
            if prefered_ground_foot == "left" and right_foot[mid] >= left_leg[mid]:
                non_hopping_leg_remains_behind = False
                break
            elif prefered_ground_foot == "right" and left_foot[mid] >= right_leg[mid]:
                non_hopping_leg_remains_behind = False
                break
        return non_hopping_leg_remains_behind

    def _compute_arms_flex_and_swing_forward(
        self,
        jump_indices: tuple[JumpIndices],
    ) -> bool:
        joint_centers = np.array([data.body_kinematics.joint_centers for data in self._data_centered])
        start_jump = [jump[0] for jump in jump_indices]
        mid_jump = [jump[1] for jump in jump_indices]

        index_of = lambda name: self._habmoti.device.body_model.from_name(name)

        left_arm = joint_centers[:, [index_of("left_shoulder"), index_of("left_elbow"), index_of("left_wrist")], :]
        right_arm = joint_centers[:, [index_of("right_shoulder"), index_of("right_elbow"), index_of("right_wrist")], :]
        shoulder, elbow, wrist = 0, 1, 2

        def arm_is_moving_forward(arm_data: np.ndarray) -> npt.NDArray[np.bool_]:
            frontward = Axes.FRONTAL.value
            return arm_data[start_jump, elbow, frontward] < arm_data[mid_jump, elbow, frontward]

        def arm_is_flexed(arm_data: np.ndarray, instant: int) -> npt.NDArray[np.bool_]:
            target = 90 * np.pi / 180  # 90 degrees
            tolerance = 10 * np.pi / 180  # 10 degrees
            angles = joint_angle(arm_data[instant, :, :], pivot_index=elbow, p0_index=shoulder, p1_index=wrist)
            return (angles > target - tolerance) & (angles < target + tolerance)

        def arm_is_swinging_forward(arm_data: np.ndarray) -> npt.NDArray[np.bool_]:
            return arm_is_moving_forward(arm_data) & arm_is_flexed(arm_data, mid_jump)

        left_arm_is_success = arm_is_swinging_forward(left_arm)
        right_arm_is_success = arm_is_swinging_forward(right_arm)
        arms_are_success = left_arm_is_success & right_arm_is_success

        return sum(arms_are_success) == len(jump_indices)

    def _compute_consecutive_jumps(
        self,
        prefered_ground_foot: str,
        jump_indices: list[JumpIndices],
    ) -> None:
        joint_centers = np.array([data.body_kinematics.joint_centers for data in self._data_centered])

        axis_index = Axes.VERTICAL.value
        left_foot_height = joint_centers[:, self._habmoti.device.body_model.from_name("left_ankle"), axis_index]
        right_foot_height = joint_centers[:, self._habmoti.device.body_model.from_name("right_ankle"), axis_index]
        mid_jump_indices = [jump[1] for jump in jump_indices]

        consecutive_jumps = 0
        best_consecutive_jumps_so_far = 0
        for mid in mid_jump_indices:
            if prefered_ground_foot == "left" and left_foot_height[mid] < right_foot_height[mid]:
                consecutive_jumps += 1
            elif prefered_ground_foot == "right" and right_foot_height[mid] < left_foot_height[mid]:
                consecutive_jumps += 1
            else:
                best_consecutive_jumps_so_far = max(best_consecutive_jumps_so_far, consecutive_jumps)
                consecutive_jumps = 0
        best_consecutive_jumps_so_far = max(best_consecutive_jumps_so_far, consecutive_jumps)
        return best_consecutive_jumps_so_far

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

        fig = plt.figure("Hop Analysis")
        plt.plot(t, left_foot_height, label="Left Foot Y")
        plt.plot(t, right_foot_height, label="Right Foot Y")
        plt.plot(t, mean_feet_height, label="Mean Feet Y", linestyle="--")
        [plt.axvline(x=t[index], color="g") for index in mid_jump_indices]
        plt.legend()

        plt.title("Hop Analysis")
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
