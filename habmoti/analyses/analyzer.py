from abc import ABC, abstractmethod
import io
from pathlib import Path
from typing import override

from ..data.frame_data import FrameData
from ..kinematics.body_kinematics import JointCenter
from ..kinematics.body_kinematics_device import BodyKinematicsDevice


class Analyzer(ABC):
    @abstractmethod
    def start(self, device: BodyKinematicsDevice) -> None:
        """
        Start the analyzer. This is called before the first frame is analyzed.
        """
        pass

    @abstractmethod
    def perform(self, frame_data: FrameData) -> None:
        """
        Analyze a frame of data.

        Args:
            frame_data: The data to analyze. The analysis is stored in the frame_data itself
        """

    @abstractmethod
    def stop(self) -> None:
        """
        Stop the analyzer. This is called when the analyzer is no longer needed.
        """
        pass


class AnalyzerList(Analyzer):
    def __init__(self, analyzers: list[Analyzer]):
        self.analyzers = analyzers

    @override
    def start(self, device: BodyKinematicsDevice) -> None:
        for analyzer in self.analyzers:
            analyzer.start(device=device)

    @override
    def perform(self, frame_data: FrameData) -> None:
        for analyzer in self.analyzers:
            analyzer.perform(frame_data)

    @override
    def stop(self) -> None:
        for analyzer in self.analyzers:
            analyzer.stop()


class EmptyAnalyzer(Analyzer):
    @override
    def start(self, device: BodyKinematicsDevice) -> None:
        pass

    @override
    def perform(self, frame_data: FrameData) -> None:
        pass

    @override
    def stop(self) -> None:
        pass


class ToConsoleAnalyzer(Analyzer):
    def __init__(self, joint_center: JointCenter):
        self._joint_center = joint_center

        super().__init__()

    @override
    def start(self, device: BodyKinematicsDevice) -> None:
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


class ToCsvAnalyzer(Analyzer):
    def __init__(self, filepath: Path):
        self._filepath = filepath
        self._filepath.parent.mkdir(parents=True, exist_ok=True)

        self._file: io.TextIOWrapper = None

        super().__init__()

    @override
    def start(self, device: BodyKinematicsDevice) -> None:
        self._file = open(self._filepath, "w")

        header = "timestamp, " + ", ".join(
            [
                f"{joint_center.name}_x, {joint_center.name}_y, {joint_center.name}_z"
                for joint_center in device.joint_center_type
            ]
        )
        self._file.write(header + "\n")

    @override
    def perform(self, frame_data: FrameData) -> None:
        timestamp = frame_data.timestamp
        data = f"{frame_data.body_kinematics.joint_centers.flatten().tolist()}"
        self._file.write(f"{timestamp}, {data[1:-1]}\n")

    @override
    def stop(self) -> None:
        self._file.close()
        self._file = None
