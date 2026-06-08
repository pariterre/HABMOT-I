from typing import override, TYPE_CHECKING

from ..analyzer import Analyzer, FrameData
from ...kinematics.body_kinematics import JointCenter

if TYPE_CHECKING:
    from ...habmoti import Habmoti


class ToConsoleAnalyzer(Analyzer):
    def __init__(self, joint_center: JointCenter):
        self._joint_center = joint_center

        super().__init__()

    @override
    def start(self, habmoti: Habmoti) -> None:
        pass

    @override
    def perform(self, frame_data: FrameData) -> None:
        import datetime

        timestamp = frame_data.timestamp
        timestamp_as_date = datetime.datetime.fromtimestamp(timestamp / 1000.0)

        print(f"At {timestamp_as_date}, received: {frame_data.body_kinematics.joint_centers[self._joint_center]}")

    @override
    def stop(self) -> None:
        pass
