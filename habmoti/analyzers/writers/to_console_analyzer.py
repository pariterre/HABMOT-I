from datetime import datetime
from typing import override, TYPE_CHECKING

from .data_writer_analyzer import DataWriterAnalyzer

if TYPE_CHECKING:
    from ...data.body_kinematics import BodyModel
    from ...habmoti import Habmoti, FrameData


class ToConsoleAnalyzer(DataWriterAnalyzer):
    def __init__(self, joint_center: str):
        """
        Analyzer that writes the value of a specific joint center to the console.

        Args:
            joint_center: The name of the joint center to write to the console. Must be a valid joint center name for the
            body model used by the device.
        """
        self._joint_center_name = joint_center
        self._joint_center = None

        super().__init__()

    @property
    @override
    def name(self) -> str:
        return f"Console Writer ({self._joint_center_name})"

    @override
    def initialize(self, habmoti: Habmoti) -> None:
        self._joint_center = habmoti._device.body_model.from_name(self._joint_center_name)

    @override
    def perform(self, frame_data: FrameData | None) -> None:
        timestamp = datetime.fromtimestamp(frame_data.timestamp / 1000.0)
        print(f"At {timestamp}, received: {frame_data.body_kinematics.joint_centers[self._joint_center]}")

    @override
    def dispose(self) -> None:
        self._joint_center = None
