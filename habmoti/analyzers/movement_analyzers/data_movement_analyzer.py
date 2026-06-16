import logging
from typing import TYPE_CHECKING, override

import numpy as np

from ..analyzer import Analyzer
from ..viewers.to_matplotlib_analyzer import ToMatplotlibAnalyzer
from ...data.body_kinematics import BodyKinematics
from ...data.frame_data import FrameData
from ...utils.maths import transpose_axes, AxisName, create_system_of_axes

if TYPE_CHECKING:
    from ..analyzer import Habmoti

_logger = logging.getLogger(__name__)


class DataMovementAnalyzer(Analyzer):
    def __init__(self):
        super().__init__()
        self._habmoti: Habmoti | None = None
        self._is_analyzing = False

        self._are_data_initialized = False
        self._data: list[FrameData] | None = None
        self._data_centered: list[FrameData] | None = None

    @override
    def initialize(self, habmoti: Habmoti) -> None:
        _logger.info(f"Initializing {self.name}")
        self._habmoti = habmoti
        self._data = []
        self._data_centered = []

    @override
    def start_trial(self) -> None:
        self._is_analyzing = True
        self._data_centered.clear()
        self._data.clear()
        _logger.info(f"Starting to analyze {self.name}")

    @override
    def perform(self, frame_data: FrameData | None) -> None:
        if self._is_analyzing and frame_data is not None:
            if not self._are_data_initialized:
                # Wait until the feet are above a certain threshold to start the analysis (to discard initialization frames
                # where the feet are below the ground)
                threshold = -0.2  # 20 cm below the ground
                left_foot_index = self._habmoti.device.body_model.from_name("left_ankle")
                right_foot_index = self._habmoti.device.body_model.from_name("right_ankle")

                feet_height = frame_data.body_kinematics.joint_centers[[left_foot_index, right_foot_index], 1].mean()
                if feet_height > threshold:
                    self._are_data_initialized = True
                    _logger.info("Feet are above the threshold, starting to save data")
                else:
                    return

            self._data.append(frame_data)
            self._data_centered.append(_frame_data_in_local_coordinate_system(frame_data, keep_real_height=True))

    @override
    def stop_trial(self) -> None:
        if not self._is_analyzing:
            return
        self._is_analyzing = False
        _logger.info(f"Stopping {self.name} analysis")

    @override
    def dispose(self) -> None:
        self._habmoti = None
        self._is_analyzing = False

        self._are_data_initialized = False
        self._data = None
        self._data_centered = None

    def _show_data(self, *args, blocking: bool = False, **kwargs) -> None:
        from matplotlib import pyplot as plt

        viewer_global = ToMatplotlibAnalyzer(show_body_coordinate_systems=True)
        viewer_global.initialize(self._habmoti)
        viewer_global.start_trial()

        viewer_local = ToMatplotlibAnalyzer(show_body_coordinate_systems=True)
        viewer_local.initialize(self._habmoti)
        viewer_local.start_trial()

        t0 = self._data_centered[0].timestamp if self._data_centered else 0
        t = np.array([data.timestamp - t0 for data in self._data_centered]) / 1000.0
        index = 0
        frames_in_global = self._data
        frames_in_local = self._data_centered
        while self._habmoti.is_trial_started:
            viewer_global.perform(frame_data=frames_in_global[index])
            viewer_local.perform(frame_data=frames_in_local[index])
            self._update_extra_show_data(index, *args, **kwargs)
            if blocking:
                input(f"Showing frame {index}. Press Enter to continue to the next frame...")
            else:
                plt.pause((t[index] - t[index - 1]) if index > 0 else 1.0)
            index = (index + 1) % len(frames_in_global)

    def _update_extra_show_data(self, index: int, *args, **kwargs) -> None:
        """
        Update additional data visualization elements during the show data process.
        This method can be overridden by subclasses to provide custom behavior.

        Args:
            index (int): The current frame index.
            *args: Additional positional arguments (passed from an overridden _show_data method).
            **kwargs: Additional keyword arguments (passed from an overridden _show_data method).
        """

        pass


def _frame_data_in_local_coordinate_system(frame: FrameData, keep_real_height: bool) -> FrameData:
    joint_centers = np.concatenate(
        (frame.body_kinematics.joint_centers.T, np.ones((1, frame.body_kinematics.joint_centers.shape[0]))),
        axis=0,
    )
    coordinate_systems = frame.body_kinematics.body_coordinate_system[0]
    if keep_real_height:
        origin = coordinate_systems[:3, 3]
        coordinate_systems = create_system_of_axes(
            origin=np.array((origin[0], 0.0, origin[2])),
            first_axis=coordinate_systems[:3, 0],
            second_axis=np.array([0.0, 1.0, 0.0]),
            first_axis_name=AxisName.X,
            second_axis_name=AxisName.Y,
            keep_axis=AxisName.Y,
        )

    tranposed = (transpose_axes(coordinate_systems) @ joint_centers).T[:, :3]
    return FrameData(
        timestamp=frame.timestamp,
        body_kinematics=BodyKinematics(body_model=frame.body_kinematics.body_model, values=tranposed),
    )
