from dataclasses import dataclass
import logging
from typing import override

import numpy as np

from .utils.jump_utils import JumpIndices, compute_jump_indices
from .data_movement_analyzer import DataMovementAnalyzer

_logger = logging.getLogger(__name__)


@dataclass
class HabmotCriteriaHop:
    can_do_four_consecutive_jumps: bool = False
    non_hopping_leg_remains_behind: bool = False


class HopAnalyzer(DataMovementAnalyzer):
    def __init__(self):
        super().__init__()
        self._criteria: HabmotCriteriaHop | None = None

    @property
    @override
    def name(self) -> str:
        return "Hop"

    @override
    def start_trial(self) -> None:
        self._criteria = HabmotCriteriaHop()
        super().start_trial()

    @override
    def stop_trial(self) -> None:
        super().stop_trial()
        self._perform_post_trial_analysis(show_debug_graphs=True)

    @override
    def _perform_post_trial_analysis(self, show_debug_graphs: bool = False) -> None:
        # Find the peaks in the mean feet y position to find the mid-jump frames
        jump_indices = compute_jump_indices(body_model=self._habmoti.device.body_model, frames=self._data_centered)
        prefered_ground_foot = self._compute_prefered_ground_foot(jump_indices)

        # Proceed to the analyses
        best_consecutive_jumps = self._compute_consecutive_jumps(prefered_ground_foot, jump_indices)
        self._criteria.can_do_four_consecutive_jumps = best_consecutive_jumps >= 4

        is_success = self._compute_non_hopping_leg_remains_behind(prefered_ground_foot, jump_indices)
        self._criteria.non_hopping_leg_remains_behind = is_success

        # Print the results to the console
        _logger.info("#####################")
        _logger.info("Hop analysis results:")
        _logger.info(f"Prefered jumper foot: {prefered_ground_foot}")
        _logger.info(
            f"Can do four consecutive jumps: {self._criteria.can_do_four_consecutive_jumps} (achieved {best_consecutive_jumps} consecutive jumps)"
        )
        _logger.info(f"Non-hopping leg remains behind: {self._criteria.non_hopping_leg_remains_behind}")
        _logger.info("#####################")

        if show_debug_graphs:
            self._show_data(blocking=False, jump_indices=jump_indices)

    @override
    def dispose(self) -> None:
        self._criteria = None
        super().dispose()

    def _compute_prefered_ground_foot(self, jump_indices: tuple[JumpIndices]) -> str:
        joint_centers = np.array([data.body_kinematics.joint_centers for data in self._data_centered])
        mid_jump_indices = [jump[1] for jump in jump_indices]

        left_foot_height = joint_centers[:, self._habmoti.device.body_model.from_name("left_ankle"), 1]
        right_foot_height = joint_centers[:, self._habmoti.device.body_model.from_name("right_ankle"), 1]
        prefered_ground_foot = (
            "left"
            if sum(left_foot_height[mid_jump_indices] < right_foot_height[mid_jump_indices]) > len(mid_jump_indices) / 2
            else "right"
        )
        return prefered_ground_foot

    def _compute_consecutive_jumps(
        self,
        prefered_ground_foot: str,
        jump_indices: list[JumpIndices],
    ) -> None:
        joint_centers = np.array([data.body_kinematics.joint_centers for data in self._data_centered])

        left_foot_height = joint_centers[:, self._habmoti.device.body_model.from_name("left_ankle"), 1]
        right_foot_height = joint_centers[:, self._habmoti.device.body_model.from_name("right_ankle"), 1]
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

    def _compute_non_hopping_leg_remains_behind(
        self,
        prefered_ground_foot: str,
        jump_indices: tuple[JumpIndices],
    ) -> bool:
        joint_centers = np.array([data.body_kinematics.joint_centers for data in self._data_centered])

        left_foot = joint_centers[:, self._habmoti.device.body_model.from_name("left_ankle"), 2]
        left_leg = joint_centers[:, self._habmoti.device.body_model.from_name("left_knee"), 2]
        right_foot = joint_centers[:, self._habmoti.device.body_model.from_name("right_ankle"), 2]
        right_leg = joint_centers[:, self._habmoti.device.body_model.from_name("right_knee"), 2]
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

    def _show_data(self, blocking: bool, jump_indices: tuple[JumpIndices]) -> None:
        from matplotlib import pyplot as plt

        t0 = self._data_centered[0].timestamp if self._data_centered else 0
        t = np.array([data.timestamp - t0 for data in self._data_centered]) / 1000.0

        joint_centers = np.array([data.body_kinematics.joint_centers for data in self._data_centered])
        left_foot_height = joint_centers[:, self._habmoti.device.body_model.from_name("left_ankle"), 1]
        right_foot_height = joint_centers[:, self._habmoti.device.body_model.from_name("right_ankle"), 1]
        mean_feet_height = (left_foot_height + right_foot_height) / 2

        mid_jump_indices = [jump[1] for jump in jump_indices]

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
        super()._show_data(blocking=blocking, t=t, line=line)

    def _update_extra_show_data(self, index: int, t: np.ndarray, line) -> None:
        from matplotlib import pyplot as plt

        x = t[index]
        line.set_xdata([x, x])

        plt.pause((t[index] - t[index - 1]) if index > 0 else 1.0)
