from dataclasses import dataclass
import logging
from typing import override

import numpy as np

from .utils.jump_utils import JumpIndices, compute_jump_indices
from .data_movement_analyzer import DataMovementAnalyzer, Axes, HabmotCriteria

_logger = logging.getLogger(__name__)


@dataclass
class HabmotCriteriaSlide(HabmotCriteria):
    leading_foot_is_off_ground: bool = False
    four_slides_on_preferred_foot: bool = False
    four_slides_on_non_preferred_foot: bool = False

    def __str__(self) -> str:
        return f"""#####################
Slide analysis results:
  1. Body is sideways and aligned with the line on the flool: IMPOSSIBLE TO DETECT WITH THE CURRENT DATA
  2. Leading foot is off the ground: {self.leading_foot_is_off_ground}
  3. Four slides on preferred foot: {self.four_slides_on_preferred_foot}
  4. Four slides on non-preferred foot: {self.four_slides_on_non_preferred_foot}
#####################"""

    def to_dict(self) -> dict:
        return {
            "leading_foot_is_off_ground": self.leading_foot_is_off_ground,
            "four_slides_on_preferred_foot": self.four_slides_on_preferred_foot,
            "four_slides_on_non_preferred_foot": self.four_slides_on_non_preferred_foot,
        }


class SlideAnalyzer(DataMovementAnalyzer):
    def __init__(self, show_debug_graphs: bool = False) -> None:
        super().__init__()
        self._criteria: HabmotCriteriaSlide | None = None
        self._show_debug_graphs = show_debug_graphs

    @property
    @override
    def name(self) -> str:
        return "Slide"

    @property
    @override
    def criteria(self) -> HabmotCriteria | None:
        return self._criteria

    @override
    def start_trial(self) -> None:
        self._criteria = HabmotCriteriaSlide()
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
        jump_leading_foot = self._compute_leading_foot(jump_indices)
        preferred_foot = "left" if jump_leading_foot.count("left") >= jump_leading_foot.count("right") else "right"
        non_preferred_foot = "right" if preferred_foot == "left" else "left"

        # Proceed to the analyses
        is_success = self._compute_is_leading_foot_off_ground(jump_indices, jump_leading_foot)
        self._criteria.leading_foot_is_off_ground = is_success

        is_success = self._compute_consecutive_slides_on_foot(jump_indices, jump_leading_foot, preferred_foot)
        self._criteria.four_slides_on_preferred_foot = is_success

        is_success = self._compute_consecutive_slides_on_foot(jump_indices, jump_leading_foot, non_preferred_foot)
        self._criteria.four_slides_on_non_preferred_foot = is_success

        # Print the results to the console
        _logger.info(f"\n{self._criteria}")

        if self._show_debug_graphs:
            self.show_data(blocking=False, jump_indices=jump_indices)

    @override
    def dispose(self) -> None:
        self._criteria = None
        super().dispose()

    def _compute_leading_foot(self, jump_indices: tuple[JumpIndices]) -> list[str]:
        # The leading foot is the furthest of the body line at the peak of the jump
        joint_centers = np.array([data.body_kinematics.joint_centers for data in self._data_centered])
        mid_jump = [jump[1] for jump in jump_indices]

        index_of = lambda name: self._habmoti.device.body_model.from_name(name)
        left_foot = joint_centers[mid_jump, index_of("left_ankle"), Axes.SAGITTAL.value]
        right_foot = joint_centers[mid_jump, index_of("right_ankle"), Axes.SAGITTAL.value]

        return ["left" if value else "right" for value in np.abs(left_foot) > np.abs(right_foot)]

    def _compute_is_leading_foot_off_ground(self, jump_indices: tuple[JumpIndices], leading_foot: list[str]) -> bool:
        joint_centers = np.array([data.body_kinematics.joint_centers for data in self._data_centered])
        mid_jump = [jump[1] for jump in jump_indices]

        index_of = lambda name: self._habmoti.device.body_model.from_name(name)
        left_foot_height = joint_centers[mid_jump, index_of("left_ankle"), Axes.VERTICAL.value]
        right_foot_height = joint_centers[mid_jump, index_of("right_ankle"), Axes.VERTICAL.value]

        threshold = 0.05  # 5 cm off the ground is considered off the ground
        foot_is_off_ground = []
        for foot, left_height, right_height in zip(leading_foot, left_foot_height, right_foot_height):
            if foot == "left":
                foot_is_off_ground.append(left_height > threshold)
            elif foot == "right":
                foot_is_off_ground.append(right_height > threshold)
            else:
                raise ValueError(f"Unexpected foot value: {foot}")

        return all(foot_is_off_ground)

    def _compute_consecutive_slides_on_foot(
        self, jump_indices: tuple[JumpIndices], leading_foot: list[str], foot_to_check: str
    ) -> bool:
        # Take the shortest amount of time between slides and find if there are 4 consecutive slides that are within that time threshold
        mid_jump = [self._data[jump[1]].timestamp for jump in jump_indices]
        time_between_slides = np.diff(mid_jump)
        if len(time_between_slides) == 0:
            return False
        tolerance = 300  # 300 ms slower than the fastest time between slides is considered a slide
        time_threshold = np.min(time_between_slides) + tolerance

        consecutive_slides = 0
        for foot, time in zip(leading_foot[:-1], time_between_slides):
            if foot != foot_to_check or time > time_threshold:
                consecutive_slides = 0
                continue
            consecutive_slides += 1
            if consecutive_slides >= 4:
                return True
        return False

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

        fig = plt.figure("Slide Analysis")
        plt.plot(t, left_foot_height, label="Left Foot Y")
        plt.plot(t, right_foot_height, label="Right Foot Y")
        plt.plot(t, mean_feet_height, label="Mean Feet Y", linestyle="--")
        [plt.axvline(x=t[index], color="g") for index in mid_jump_indices]
        plt.legend()

        plt.title("Slide Analysis")
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
