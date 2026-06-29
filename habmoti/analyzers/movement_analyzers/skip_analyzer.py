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
class HabmotCriteriaSkip(HabmotCriteria):
    arms_are_flexed_and_opposite_to_legs: bool = False
    can_do_four_consecutive_skips: bool = False

    def __str__(self) -> str:
        return f"""#####################
Skip analysis results:
  1. A step forward followed by a hop on the same foot: NOT DETECTABLE WITH THE CURRENT DATA?
  2. Arms are flexed and move in opposition to the legs to produce force: {self.arms_are_flexed_and_opposite_to_legs}
  3. Completes four continuous rhythmical alternating skips: {self.can_do_four_consecutive_skips}
#####################"""

    def to_dict(self) -> dict:
        return {
            "arms_are_flexed_and_opposite_to_legs": self.arms_are_flexed_and_opposite_to_legs,
            "can_do_four_consecutive_skips": self.can_do_four_consecutive_skips,
        }


class SkipAnalyzer(DataMovementAnalyzer):
    def __init__(self, show_debug_graphs: bool = False) -> None:
        super().__init__()
        self._criteria: HabmotCriteriaSkip | None = None
        self._show_debug_graphs = show_debug_graphs

    @property
    @override
    def name(self) -> str:
        return "Skip"

    @property
    @override
    def criteria(self) -> HabmotCriteria | None:
        return self._criteria

    @override
    def start_trial(self) -> None:
        self._criteria = HabmotCriteriaSkip()
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
        left_skip_patterns, right_skip_patterns = self._detect_skip_patterns(jump_indices)

        # Proceed to the analyses
        is_success = self._compute_arms_flex_and_controlateral(left_skip_patterns, right_skip_patterns)
        self._criteria.arms_flex_and_swing_forward = is_success

        best_consecutive_skips = self._compute_consecutive_skips(left_skip_patterns, right_skip_patterns)
        self._criteria.can_do_four_consecutive_skips = best_consecutive_skips >= 4

        # Print the results to the console
        _logger.info(f"\n{self._criteria}")

        if self._show_debug_graphs:
            self.show_data(blocking=False, skip_patterns=(left_skip_patterns, right_skip_patterns))

    @override
    def dispose(self) -> None:
        self._criteria = None
        super().dispose()

    def _detect_skip_patterns(
        self,
        jump_indices: list[JumpIndices],
    ) -> tuple[list[JumpIndices], list[JumpIndices]]:
        joint_centers = np.array([data.body_kinematics.joint_centers for data in self._data_centered])
        axis_index = Axes.VERTICAL.value
        left_foot_height = joint_centers[:, self._habmoti.device.body_model.from_name("left_ankle"), axis_index]
        right_foot_height = joint_centers[:, self._habmoti.device.body_model.from_name("right_ankle"), axis_index]

        left_skip_patterns: list[JumpIndices] = []
        right_skip_patterns: list[JumpIndices] = []
        for jump_index in range(len(jump_indices) - 1):
            current_jump = jump_indices[jump_index]
            next_jump = jump_indices[jump_index + 1]

            current_left_foot_height = left_foot_height[current_jump[1]]
            current_right_foot_height = right_foot_height[current_jump[1]]
            next_left_foot_height = left_foot_height[next_jump[1]]
            next_right_foot_height = right_foot_height[next_jump[1]]

            # A valid skip is when a foot first performs a step, then a hop. So first time, the foot is lower than the other
            # and during the next "step" the foot is higher as it is performing a hop.
            # The hop must be at least 1.5 times the height of the step to be considered a valid skip.
            if current_left_foot_height < current_right_foot_height:
                if next_left_foot_height > next_right_foot_height:
                    if next_left_foot_height > current_left_foot_height * 1.5:
                        left_skip_patterns.append(current_jump)
            elif current_right_foot_height < current_left_foot_height:
                if next_right_foot_height > next_left_foot_height:
                    if next_right_foot_height > current_right_foot_height * 1.5:
                        right_skip_patterns.append(current_jump)
            else:
                # Feet are at the same height, cannot determine which foot is leading, so we ignore this jump
                pass

        return left_skip_patterns, right_skip_patterns

    def _compute_arms_flex_and_controlateral(
        self,
        left_skip_patterns: list[JumpIndices],
        right_skip_patterns: list[JumpIndices],
    ) -> bool:
        joint_centers = np.array([data.body_kinematics.joint_centers for data in self._data_centered])
        left_mid_jump = [jump[1] for jump in left_skip_patterns]
        right_mid_jump = [jump[1] for jump in right_skip_patterns]
        frontal_index = Axes.FRONTAL.value

        of = lambda name: self._habmoti.device.body_model.from_name(name)

        left = joint_centers[:, [of("left_shoulder"), of("left_elbow"), of("left_wrist"), of("left_ankle")], :]
        right = joint_centers[:, [of("right_shoulder"), of("right_elbow"), of("right_wrist"), of("right_ankle")], :]
        shoulder, elbow, wrist, ankle = 0, 1, 2, 3

        def arm_is_flexed(data: np.ndarray, instant: int) -> npt.NDArray[np.bool_]:
            target = 90 * np.pi / 180  # 90 degrees
            tolerance = 10 * np.pi / 180  # 10 degrees
            angles = joint_angle(data[instant, :, :], pivot_index=elbow, p0_index=shoulder, p1_index=wrist)
            return (angles > target - tolerance) & (angles < target + tolerance)

        def arm_is_opposite_to_leg(data: np.ndarray, instant: int) -> npt.NDArray[np.bool_]:
            # The arm is opposite to the leg if the arm is flexed and the leg is extended (not flexed)
            hand_position = data[instant, wrist, frontal_index]
            foot_position = data[instant, ankle, frontal_index]
            return hand_position * foot_position < 0  # Same side of the body should be opposite signs

        def arm_is_success(data: np.ndarray, instant: int) -> npt.NDArray[np.bool_]:
            return arm_is_flexed(data, instant) & arm_is_opposite_to_leg(data, instant)

        left_arm_is_success = arm_is_success(left, left_mid_jump)
        right_arm_is_success = arm_is_success(right, right_mid_jump)
        arms_are_success = left_arm_is_success & right_arm_is_success

        return sum(arms_are_success) == (len(left_skip_patterns) + len(right_skip_patterns))

    def _compute_consecutive_skips(
        self,
        left_skip_patterns: list[JumpIndices],
        right_skip_patterns: list[JumpIndices],
    ) -> None:
        if len(left_skip_patterns) < 2 or len(right_skip_patterns) < 2:
            return False

        # Keep alternating skips only
        alternating_skips = []
        left_index = 0
        right_index = 0
        previous = None
        while left_index < len(left_skip_patterns) and right_index < len(right_skip_patterns):
            left_jump = left_skip_patterns[left_index]
            right_jump = right_skip_patterns[right_index]

            if left_jump[0] < right_jump[0]:
                if previous != "left":
                    alternating_skips.append(left_jump)
                    previous = "left"
                left_index += 1
            else:
                if previous != "right":
                    alternating_skips.append(right_jump)
                    previous = "right"
                right_index += 1

        if len(alternating_skips) < 4:
            return False

        # Check if the time between each jump is consistent (not too long, not too short)
        mid_jump_times = sorted([self._data_centered[jump[1]].timestamp for jump in alternating_skips])
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

    @override
    def show_data(
        self, blocking: bool = False, skip_patterns: tuple[list[JumpIndices], list[JumpIndices]] = None
    ) -> None:
        from matplotlib import pyplot as plt

        if skip_patterns is None:
            jump_indices = compute_jump_indices(
                body_model=self._habmoti.device.body_model, frames=self._data_centered, threshold=0.1
            )
            left_skip_patterns, right_skip_patterns = self._detect_skip_patterns(jump_indices)
        else:
            left_skip_patterns, right_skip_patterns = skip_patterns

        t0 = self._data_centered[0].timestamp if self._data_centered else 0
        t = np.array([data.timestamp - t0 for data in self._data_centered]) / 1000.0

        axis_index = Axes.VERTICAL.value
        joint_centers = np.array([data.body_kinematics.joint_centers for data in self._data_centered])
        left_foot_height = joint_centers[:, self._habmoti.device.body_model.from_name("left_ankle"), axis_index]
        right_foot_height = joint_centers[:, self._habmoti.device.body_model.from_name("right_ankle"), axis_index]
        mean_feet_height = (left_foot_height + right_foot_height) / 2

        left_start_skip_indices = [jump[0] for jump in left_skip_patterns]
        right_start_skip_indices = [jump[0] for jump in right_skip_patterns]

        fig = plt.figure("Skip Analysis")
        plt.plot(t, left_foot_height, label="Left Foot Y")
        plt.plot(t, right_foot_height, label="Right Foot Y")
        plt.plot(t, mean_feet_height, label="Mean Feet Y", linestyle="--")
        [plt.axvline(x=t[index], color="g") for index in left_start_skip_indices]
        [plt.axvline(x=t[index], color="b") for index in right_start_skip_indices]
        plt.legend()

        plt.title("Skip Analysis")
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
