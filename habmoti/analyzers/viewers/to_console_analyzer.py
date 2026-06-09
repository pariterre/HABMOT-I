from datetime import datetime
from typing import override, TYPE_CHECKING

from ..analyzer import Analyzer

if TYPE_CHECKING:
    from ...data.body_kinematics import BodyModel
    from ...habmoti import Habmoti, FrameData


class ToConsoleAnalyzer(Analyzer):
    def __init__(self, joint_center: BodyModel):
        self._joint_center = joint_center

        super().__init__()

    @override
    def start(self, habmoti: Habmoti) -> None:
        pass

    @override
    def perform(self, frame_data: FrameData) -> None:
        timestamp = datetime.fromtimestamp(frame_data.timestamp / 1000.0)
        print(f"At {timestamp}, received: {frame_data.body_kinematics.joint_centers[self._joint_center]}")

    @override
    def stop(self) -> None:
        pass
