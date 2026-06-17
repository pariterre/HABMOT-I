from dataclasses import dataclass
import logging
from typing import override

import numpy as np
import numpy.typing as npt

from .utils.body_model_utils import joint_angle
from .utils.jump_utils import JumpIndices, compute_jump_indices
from .data_movement_analyzer import DataMovementAnalyzer, Axes

_logger = logging.getLogger(__name__)


@dataclass
class HabmotCriteriaGallop:
    arms_flex_and_swing_forward: bool = False
    lagging_foot_is_behind_on_landing: bool = False
    is_jumping: bool = False
    can_do_four_consecutive_gallops: bool = False

    def __str__(self) -> str:
        return f"""#####################
Gallop analysis results:
  1. Arms flex and swing forward: {self.arms_flex_and_swing_forward}
  2. Lagging foot is behind on landing: {self.lagging_foot_is_behind_on_landing}
  3. Both feed come off the surface: {self.is_jumping}
  4. Can maintain a rhythmic pattern four consecutive gallops: {self.can_do_four_consecutive_gallops}
#####################"""


class GallopAnalyzer(DataMovementAnalyzer):
    def __init__(self, show_debug_graphs: bool = False) -> None:
        super().__init__()
        self._criteria: HabmotCriteriaGallop | None = None
        self._show_debug_graphs = show_debug_graphs

    @property
    @override
    def name(self) -> str:
        return "Hop"

    @override
    def start_trial(self) -> None:
        self._criteria = HabmotCriteriaGallop()
        super().start_trial()

    @override
    def stop_trial(self) -> None:
        super().stop_trial()
        self._perform_post_trial_analysis()

    @override
    def _perform_post_trial_analysis(self) -> None:
        # Find the peaks in the mean feet y position to find the mid-jump frames
        jump_indices = compute_jump_indices(body_model=self._habmoti.device.body_model, frames=self._data_centered)
        leading_foot = self._compute_leading_foot(jump_indices)

        # Proceed to the analyses
        is_success = self._compute_arms_flex_and_swing_forward(jump_indices)
        self._criteria.arms_flex_and_swing_forward = is_success

        is_success = self._compute_lagging_foot_is_behind_on_landing(jump_indices, leading_foot)
        self._criteria.lagging_foot_is_behind_on_landing = is_success

        is_success = self._compute_is_jumping(jump_indices)
        self._criteria.is_jumping = is_success

        is_success = self._compute_can_do_four_consecutive_gallops(jump_indices)
        self._criteria.can_do_four_consecutive_gallops = is_success

        # Print the results to the console
        _logger.info(f"\n{self._criteria}")

        if self._show_debug_graphs:
            self._show_data(blocking=False, jump_indices=jump_indices)

    @override
    def dispose(self) -> None:
        self._criteria = None
        super().dispose()

    def _compute_leading_foot(self, jump_indices: tuple[JumpIndices]) -> str:
        joint_centers = np.array([data.body_kinematics.joint_centers for data in self._data_centered])
        mid_jump = [jump[1] for jump in jump_indices]

        frontward = Axes.FRONTAL.value
        left_foot = joint_centers[:, self._habmoti.device.body_model.from_name("left_ankle"), frontward]
        right_foot = joint_centers[:, self._habmoti.device.body_model.from_name("right_ankle"), frontward]
        prefered_ground_foot = (
            "left" if sum(left_foot[mid_jump] > right_foot[mid_jump]) > len(mid_jump) / 2 else "right"
        )
        return prefered_ground_foot

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

    def _compute_lagging_foot_is_behind_on_landing(self, jump_indices: tuple[JumpIndices], leading_foot: str) -> bool:
        joint_centers = np.array([data.body_kinematics.joint_centers for data in self._data_centered])
        end_jump = [jump[2] for jump in jump_indices]
        frontward = Axes.FRONTAL.value
        left_foot = joint_centers[:, self._habmoti.device.body_model.from_name("left_ankle"), frontward]
        right_foot = joint_centers[:, self._habmoti.device.body_model.from_name("right_ankle"), frontward]

        if leading_foot == "left":
            return (left_foot[end_jump] > right_foot[end_jump]).all()
        else:
            return (right_foot[end_jump] > left_foot[end_jump]).all()

    def _compute_is_jumping(self, jump_indices: tuple[JumpIndices]) -> bool:
        joint_centers = np.array([data.body_kinematics.joint_centers for data in self._data_centered])
        mid_jump = [jump[1] for jump in jump_indices]
        left_foot = joint_centers[:, self._habmoti.device.body_model.from_name("left_ankle"), Axes.VERTICAL.value]
        right_foot = joint_centers[:, self._habmoti.device.body_model.from_name("right_ankle"), Axes.VERTICAL.value]

        threshold = 0.1  # 10 cm
        left_foot_is_off_ground = left_foot[mid_jump] > threshold
        right_foot_is_off_ground = right_foot[mid_jump] > threshold

        return (left_foot_is_off_ground & right_foot_is_off_ground).all()

    def _compute_can_do_four_consecutive_gallops(self, jump_indices: tuple[JumpIndices]) -> bool:
        if len(jump_indices) < 4:
            return False

        # Check if the time between each jump is consistent (not too long, not too short)
        mid_jump_times = [self._data_centered[jump[1]].timestamp for jump in jump_indices]
        time_differences = np.diff(mid_jump_times)
        mean_time_diff = np.mean(time_differences)
        time_diff_threshold = 200  # ms
        consistent_timing = np.abs(time_differences - mean_time_diff) < time_diff_threshold

        best_consecutive_count = 1
        current_consecutive_count = 0
        for i in range(len(consistent_timing)):
            if consistent_timing[i]:
                current_consecutive_count += 1
                best_consecutive_count = max(best_consecutive_count, current_consecutive_count)
            else:
                current_consecutive_count = 0

        return best_consecutive_count >= 4

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
        super()._show_data(blocking=blocking, fig=fig, t=t, line=line)

    def _update_extra_show_data(self, index: int, fig, t: np.ndarray, line) -> bool:
        from matplotlib import pyplot as plt

        if not plt.fignum_exists(fig.number):
            return False

        x = t[index]
        line.set_xdata([x, x])

        plt.pause((t[index] - t[index - 1]) if index > 0 else 1.0)
        return True
