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
class HabmotCriteriaRun(HabmotCriteria):
    are_arms_legs_opposition: bool = False
    is_jumping: bool = False
    non_support_leg_is_flexed: bool = False

    def __str__(self) -> str:
        return f"""#####################
Run analysis results:
  1. Arms and legs are in opposition: {self.are_arms_legs_opposition}
  2. Both feet come off the surface: {self.is_jumping}
  3. Narrow foot placement: IMPOSSIBLE TO ASSESS WITH CURRENT DATA
  4. Non-support leg is flexed: {self.non_support_leg_is_flexed}
#####################"""

    def to_dict(self) -> dict:
        return {
            "are_arms_legs_opposition": self.are_arms_legs_opposition,
            "is_jumping": self.is_jumping,
            "non_support_leg_is_flexed": self.non_support_leg_is_flexed,
        }


class RunAnalyzer(DataMovementAnalyzer):
    def __init__(self, show_debug_graphs: bool = False) -> None:
        super().__init__()
        self._criteria: HabmotCriteriaRun | None = None
        self._show_debug_graphs = show_debug_graphs

    @property
    @override
    def name(self) -> str:
        return "Run"

    @property
    @override
    def criteria(self) -> HabmotCriteria | None:
        return self._criteria

    @override
    def start_trial(self) -> None:
        self._criteria = HabmotCriteriaRun()
        super().start_trial()

    @override
    def stop_trial(self) -> None:
        super().stop_trial()
        self._perform_post_trial_analysis()

    @override
    def _perform_post_trial_analysis(self) -> None:
        # Find the peaks in the mean feet y position to find the mid-jump frames
        jump_indices = compute_jump_indices(
            body_model=self._habmoti.device.body_model, frames=self._data_centered, threshold=0.05
        )

        # Proceed to the analyses
        is_success = self._compute_are_arms_legs_opposition(jump_indices)
        self._criteria.are_arms_legs_opposition = is_success

        is_success = self._compute_is_jumping(jump_indices)
        self._criteria.is_jumping = is_success

        is_success = self._compute_is_non_support_leg_flexed(jump_indices)
        self._criteria.non_support_leg_is_flexed = is_success

        # Print the results to the console
        _logger.info(f"\n{self._criteria}")

        if self._show_debug_graphs:
            self.show_data(blocking=False, jump_indices=jump_indices)

    @override
    def dispose(self) -> None:
        self._criteria = None
        super().dispose()

    def _compute_are_arms_legs_opposition(self, jump_indices: tuple[JumpIndices]) -> bool:
        joint_centers = np.array([data.body_kinematics.joint_centers for data in self._data_centered])
        mid_jump = [jump[1] for jump in jump_indices]

        index_of = lambda name: self._habmoti.device.body_model.from_name(name)
        wrist, knee = 0, 1
        joints = ["wrist", "knee"]
        left_data = joint_centers[:, [index_of(f"left_{name}") for name in joints], :]
        right_data = joint_centers[:, [index_of(f"right_{name}") for name in joints], :]

        is_left_arm_front = (
            left_data[mid_jump, wrist, Axes.FRONTAL.value] < right_data[mid_jump, wrist, Axes.FRONTAL.value]
        )
        is_left_leg_front = (
            left_data[mid_jump, knee, Axes.FRONTAL.value] < right_data[mid_jump, knee, Axes.FRONTAL.value]
        )
        arms_are_opposite_to_legs = is_left_arm_front != is_left_leg_front

        return arms_are_opposite_to_legs.all()

    def _compute_is_jumping(self, jump_indices: tuple[JumpIndices]) -> bool:
        joint_centers = np.array([data.body_kinematics.joint_centers for data in self._data_centered])
        mid_jump = [jump[1] for jump in jump_indices]
        left_foot = joint_centers[:, self._habmoti.device.body_model.from_name("left_ankle"), Axes.VERTICAL.value]
        right_foot = joint_centers[:, self._habmoti.device.body_model.from_name("right_ankle"), Axes.VERTICAL.value]

        threshold = 0.1  # 10 cm
        left_foot_is_off_ground = left_foot[mid_jump] > threshold
        right_foot_is_off_ground = right_foot[mid_jump] > threshold

        return (left_foot_is_off_ground & right_foot_is_off_ground).all()

    def _compute_is_non_support_leg_flexed(self, jump_indices: tuple[JumpIndices]) -> bool:
        joint_centers = np.array([data.body_kinematics.joint_centers for data in self._data_centered])
        mid_jump = np.array([jump[1] for jump in jump_indices])

        index_of = lambda name: self._habmoti.device.body_model.from_name(name)
        knee, hip, ankle = 0, 1, 2
        joints = ["knee", "hip", "ankle"]
        left_data = joint_centers[:, [index_of(f"left_{name}") for name in joints], :]
        right_data = joint_centers[:, [index_of(f"right_{name}") for name in joints], :]

        def leg_is_flexed(data: np.ndarray, instant: list[int]) -> npt.NDArray[np.bool_]:
            target = 90 * np.pi / 180  # 90 degrees
            tolerance = 20 * np.pi / 180  # 20 degrees
            angles = joint_angle(data[instant, :, :], pivot_index=knee, p0_index=hip, p1_index=ankle)
            return (angles > target - tolerance) & (angles < target + tolerance)

        left_foot_is_off_ground = (
            left_data[mid_jump, ankle, Axes.VERTICAL.value] > right_data[mid_jump, ankle, Axes.VERTICAL.value]
        )
        right_foot_is_off_ground = (
            right_data[mid_jump, ankle, Axes.VERTICAL.value] > left_data[mid_jump, ankle, Axes.VERTICAL.value]
        )
        left_leg_is_flexed = leg_is_flexed(left_data, mid_jump[left_foot_is_off_ground])
        right_leg_is_flexed = leg_is_flexed(right_data, mid_jump[right_foot_is_off_ground])

        return left_leg_is_flexed.all() and right_leg_is_flexed.all()

    @override
    def show_data(self, blocking: bool = False, jump_indices: tuple[JumpIndices] = None) -> None:
        from matplotlib import pyplot as plt

        if jump_indices is None:
            jump_indices = compute_jump_indices(
                body_model=self._habmoti.device.body_model, frames=self._data_centered, threshold=0.05
            )

        t0 = self._data_centered[0].timestamp if self._data_centered else 0
        t = np.array([data.timestamp - t0 for data in self._data_centered]) / 1000.0

        axis_index = Axes.VERTICAL.value
        joint_centers = np.array([data.body_kinematics.joint_centers for data in self._data_centered])
        left_foot_height = joint_centers[:, self._habmoti.device.body_model.from_name("left_ankle"), axis_index]
        right_foot_height = joint_centers[:, self._habmoti.device.body_model.from_name("right_ankle"), axis_index]
        mean_feet_height = (left_foot_height + right_foot_height) / 2

        mid_jump_indices = [jump[1] for jump in jump_indices]

        fig = plt.figure("Run Analysis")
        plt.plot(t, left_foot_height, label="Left Foot Y")
        plt.plot(t, right_foot_height, label="Right Foot Y")
        plt.plot(t, mean_feet_height, label="Mean Feet Y", linestyle="--")
        [plt.axvline(x=t[index], color="g") for index in mid_jump_indices]
        plt.legend()

        plt.title("Run Analysis")
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
