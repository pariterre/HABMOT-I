from dataclasses import dataclass
from typing import override, TYPE_CHECKING

import numpy as np
from scipy.signal import find_peaks

from habmoti.analyzers.viewers.to_matplotlib_analyzer import ToMatplotlibAnalyzer

from .data_movement_analyzer import DataMovementAnalyzer
from ...data.body_kinematics import BodyKinematics
from ...data.frame_data import FrameData
from ...utils.maths import transpose_axes

if TYPE_CHECKING:
    from ..analyzer import Habmoti


@dataclass
class HabmotCriteria:
    can_do_four_consecutive_jumps: bool = False
    non_hopping_leg_remains_behind: bool = False


class HopAnalyzer(DataMovementAnalyzer):
    def __init__(self):
        super().__init__()

        self._habmoti: Habmoti | None = None
        self._is_analyzing = False

        self._are_data_initialized = False
        self._data: list[FrameData] | None = None
        self._criteria: HabmotCriteria | None = None

    @property
    @override
    def name(self) -> str:
        return "Hop"

    @override
    def initialize(self, habmoti: Habmoti) -> None:
        print("Initializing Hop")
        self._habmoti = habmoti
        self._data = []
        self._criteria = HabmotCriteria()

    @override
    def start_trial(self) -> None:
        self._is_analyzing = True
        self._data.clear()
        print("Starting to analyze hop")

    @override
    def perform(self, frame_data: FrameData | None) -> None:
        if self._is_analyzing and frame_data is not None:
            if not self._are_data_initialized:
                # Wait until the feet are above a certain threshold to start the analysis (to discard initialization frames
                # where the feet are below the ground)
                threshold = -0.2
                left_foot_y = frame_data.body_kinematics.joint_centers[
                    self._habmoti.device.body_model.from_name("left_ankle"), 1
                ]
                right_foot_y = frame_data.body_kinematics.joint_centers[
                    self._habmoti.device.body_model.from_name("right_ankle"), 1
                ]
                mean_foot_y = (left_foot_y + right_foot_y) / 2
                if mean_foot_y > threshold:
                    self._are_data_initialized = True
                    print("Feet are above the threshold, starting the analysis")
                else:
                    return

            print("Saving hop frame")
            self._data.append(frame_data)
        pass

    @override
    def stop_trial(self) -> None:
        if not self._is_analyzing:
            return
        self._is_analyzing = False
        print("Stopping hop analysis")

        # Discard any initialization frames (feet are way below the ground)
        data_in_global = self._data
        data_in_local = self._frame_data_in_local_coordinate_system(self._data)
        joint_centers = _joint_centers_as_array(self._data)
        # TODO Rotate data

        # Find the peaks in the mean feet y position to find the mid-jump frames
        start_jump_indices, mid_jump_indices, end_jump_indices = self._compute_jump_indices(joint_centers)
        prefered_ground_foot = self._compute_prefered_ground_foot(mid_jump_indices, joint_centers)

        # Proceed to the analyses
        best_consecutive_jumps = self._compute_consecutive_jumps(
            prefered_ground_foot, mid_jump_indices, data_in_global, data_in_local
        )
        self._criteria.can_do_four_consecutive_jumps = best_consecutive_jumps >= 4

        is_success = self._compute_non_hopping_leg_remains_behind(
            prefered_ground_foot, mid_jump_indices, data_in_global, data_in_local
        )
        self._criteria.non_hopping_leg_remains_behind = is_success

        # Print the results to the console
        print(f"Prefered jumper foot: {prefered_ground_foot}")
        print(
            f"Can do four consecutive jumps: {self._criteria.can_do_four_consecutive_jumps} (achieved {best_consecutive_jumps} consecutive jumps)"
        )
        print(f"Non-hopping leg remains behind: {self._criteria.non_hopping_leg_remains_behind}")
        self._show_data(mid_jump_indices, data_in_global, data_in_local)

    @override
    def dispose(self) -> None:
        self._habmoti = None
        self._data = None
        self._criteria = None

    def _compute_jump_indices(self, data: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        mean_feet_height = np.mean(
            data[
                :,
                [
                    self._habmoti.device.body_model.from_name("left_ankle"),
                    self._habmoti.device.body_model.from_name("right_ankle"),
                ],
                1,
            ],
            axis=1,
        )
        mid_jump_indices, _ = find_peaks(mean_feet_height, height=0.1)

        # Find the valleys in between the first and last peaks of max_peaks to determine the landings/take-offs
        min_peaks, _ = find_peaks(-mean_feet_height, height=-0.1)
        min_peaks = [peak for peak in min_peaks if peak > mid_jump_indices[0] and peak < mid_jump_indices[-1]]
        start_jump_indices = min_peaks[:-1]
        end_jump_indices = min_peaks[1:]

        # Remove back the mid jumps which are not between a start and end jump
        mid_jump_indices = [
            mid
            for mid in mid_jump_indices
            if any(start < mid < end for start, end in zip(start_jump_indices, end_jump_indices))
        ]

        return start_jump_indices, mid_jump_indices, end_jump_indices

    def _compute_prefered_ground_foot(self, mid_jump_indices: np.ndarray, data: np.ndarray) -> str:
        left_foot_height = data[:, self._habmoti.device.body_model.from_name("left_ankle"), 1]
        right_foot_height = data[:, self._habmoti.device.body_model.from_name("right_ankle"), 1]
        prefered_ground_foot = (
            "left"
            if sum(left_foot_height[mid_jump_indices] < right_foot_height[mid_jump_indices]) > len(mid_jump_indices) / 2
            else "right"
        )
        return prefered_ground_foot

    def _compute_consecutive_jumps(
        self,
        prefered_ground_foot: str,
        mid_jump_indices: np.ndarray,
        data_in_global: FrameData,
        _: FrameData,
    ) -> None:
        joint_centers = _joint_centers_as_array(data_in_global)
        left_foot_height = joint_centers[:, self._habmoti.device.body_model.from_name("left_ankle"), 1]
        right_foot_height = joint_centers[:, self._habmoti.device.body_model.from_name("right_ankle"), 1]

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
        mid_jump_indices: np.ndarray,
        _: FrameData,
        data_in_local: FrameData,
    ) -> bool:
        joint_centers = _joint_centers_as_array(data_in_local)
        left_foot = joint_centers[:, self._habmoti.device.body_model.from_name("left_ankle"), 2]
        left_leg = joint_centers[:, self._habmoti.device.body_model.from_name("left_knee"), 2]
        right_foot = joint_centers[:, self._habmoti.device.body_model.from_name("right_ankle"), 2]
        right_leg = joint_centers[:, self._habmoti.device.body_model.from_name("right_knee"), 2]

        non_hopping_leg_remains_behind = True
        for mid in mid_jump_indices:
            if prefered_ground_foot == "left" and right_foot[mid] >= left_leg[mid]:
                non_hopping_leg_remains_behind = False
                break
            elif prefered_ground_foot == "right" and left_foot[mid] >= right_leg[mid]:
                non_hopping_leg_remains_behind = False
                break
        return non_hopping_leg_remains_behind

    def _frame_data_in_local_coordinate_system(self, frame_data: FrameData) -> list[FrameData]:
        out = []
        for frame in frame_data:
            joint_centers = np.concatenate(
                (frame.body_kinematics.joint_centers.T, np.ones((1, frame.body_kinematics.joint_centers.shape[0]))),
                axis=0,
            )
            coordinate_systems = frame.body_kinematics.body_coordinate_system[0]
            tranposed = (transpose_axes(coordinate_systems) @ joint_centers).T[:, :3]
            out.append(
                FrameData(
                    timestamp=frame.timestamp,
                    body_kinematics=BodyKinematics(body_model=frame.body_kinematics.body_model, values=tranposed),
                )
            )
        return out

    def _show_data(self, mid_jump_indices: np.ndarray, frames_in_global: FrameData, frames_in_local: FrameData) -> None:
        from matplotlib import pyplot as plt

        t0 = self._data[0].timestamp if self._data else 0
        t = np.array([data.timestamp - t0 for data in self._data]) / 1000.0

        joint_centers = _joint_centers_as_array(self._data)
        left_foot_height = joint_centers[:, self._habmoti.device.body_model.from_name("left_ankle"), 1]
        right_foot_height = joint_centers[:, self._habmoti.device.body_model.from_name("right_ankle"), 1]
        mean_feet_height = (left_foot_height + right_foot_height) / 2

        plt.plot(t, left_foot_height, label="Left Foot Y")
        plt.plot(t, right_foot_height, label="Right Foot Y")
        plt.plot(t, mean_feet_height, label="Mean Feet Y", linestyle="--")
        [plt.axvline(x=t[index], color="g") for index in mid_jump_indices]
        plt.legend()

        plt.title("Hop Analysis")
        plt.xlabel("Time (s)")
        plt.ylabel("Height Position")
        plt.pause(0.1)

        from ..viewers.to_matplotlib_analyzer import ToMatplotlibAnalyzer

        viewer_global = ToMatplotlibAnalyzer(show_body_coordinate_systems=True)
        viewer_global.initialize(self._habmoti)
        viewer_global.start_trial()

        viewer_local = ToMatplotlibAnalyzer(show_body_coordinate_systems=True)
        viewer_local.initialize(self._habmoti)
        viewer_local.start_trial()

        index = 0
        # Plot a vertical line a index to show where we are in the data
        line = plt.axvline(x=index, color="r", linestyle="--")

        while self._habmoti.is_trial_started:
            viewer_global.perform(frame_data=frames_in_global[index])
            viewer_local.perform(frame_data=frames_in_local[index])
            x = (frames_in_global[index].timestamp - t0) / 1000.0
            line.set_xdata([x, x])
            plt.pause(
                (frames_in_global[index].timestamp - frames_in_global[index - 1].timestamp) / 1000.0
                if index > 0
                else 1.0
            )
            input(f"Showing frame {index}. Press Enter to continue to the next frame...")
            index = (index + 1) % len(frames_in_global)


def _joint_centers_as_array(frame_data: list[FrameData]) -> np.ndarray:
    if frame_data is None:
        return np.array([])
    return np.array([data.body_kinematics.joint_centers for data in frame_data])
