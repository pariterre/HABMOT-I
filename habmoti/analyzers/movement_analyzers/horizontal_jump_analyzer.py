from dataclasses import dataclass
import logging
from typing import override

import numpy as np

from .data_movement_analyzer import DataMovementAnalyzer
from .utils.jump_utils import JumpIndices, compute_jump_indices

_logger = logging.getLogger(__name__)


@dataclass
class HabmotCriteriaHorizontalJump:
    feet_are_together: bool = False


class HorizontalJumpAnalyzer(DataMovementAnalyzer):
    def __init__(self):
        super().__init__()
        self._criteria: HabmotCriteriaHorizontalJump | None = None

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
        self._perform_post_trial_analysis(show_debug_graphs=True)

    @override
    def _perform_post_trial_analysis(self, show_debug_graphs: bool = False) -> None:
        # Find the peaks in the mean feet y position to find the mid-jump frames
        jump_indices = compute_jump_indices(body_model=self._habmoti.device.body_model, frames=self._data_centered)

        # Proceed to the analyses
        is_success = self._compute_feet_are_together(jump_indices)
        self._criteria.feet_are_together = is_success

        # Print the results to the console
        _logger.info("#####################")
        _logger.info("Horizontal jump analysis results:")
        _logger.info(f"Feet are together: {self._criteria.feet_are_together}")
        _logger.info("#####################")
        if show_debug_graphs:
            self._show_data(blocking=False, jump_indices=jump_indices)

    @override
    def dispose(self) -> None:
        self._criteria = None
        super().dispose()

    def _compute_feet_are_together(self, jump_indices: tuple[JumpIndices]) -> bool:
        joint_centers = np.array([data.body_kinematics.joint_centers for data in self._data_centered])

        left_foot_height = joint_centers[:, self._habmoti.device.body_model.from_name("left_ankle"), 1]
        right_foot_height = joint_centers[:, self._habmoti.device.body_model.from_name("right_ankle"), 1]

        start_index = 0
        end_index = 2
        indices = [jump[start_index] for jump in jump_indices] + [jump[end_index] for jump in jump_indices]
        feet_distance = np.abs(left_foot_height[indices] - right_foot_height[indices])
        return max(feet_distance) < 0.1  # Threshold of 10 cm between the feet at mid-jump

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

        plt.title("Horizontal Jump Analysis")
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
