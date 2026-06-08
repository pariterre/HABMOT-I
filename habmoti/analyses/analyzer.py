from abc import ABC, abstractmethod
import io
from pathlib import Path
from typing import override, TYPE_CHECKING

from ..data.frame_data import FrameData

if TYPE_CHECKING:
    from ..habmoti import Habmoti


class Analyzer(ABC):
    @abstractmethod
    def start(self, habmoti: Habmoti) -> None:
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
    def __init__(self, analyzers: list[Analyzer] = None):
        self._analyzers = analyzers if analyzers is not None else []
        self._is_locked = False

    def append(self, analyzer: Analyzer) -> None:
        if self._is_locked:
            raise RuntimeError("Cannot append an analyzer to a locked AnalyzerList")
        self._analyzers.append(analyzer)

    @override
    def start(self, habmoti: Habmoti) -> None:
        self._is_locked = True
        for analyzer in self._analyzers:
            analyzer.start(habmoti=habmoti)

    @override
    def perform(self, frame_data: FrameData) -> None:
        for analyzer in self._analyzers:
            analyzer.perform(frame_data)

    @override
    def stop(self) -> None:
        for analyzer in self._analyzers:
            analyzer.stop()
        self._is_locked = False


class ToCsvAnalyzer(Analyzer):
    def __init__(self, filepath: Path):
        self._filepath = filepath
        self._filepath.parent.mkdir(parents=True, exist_ok=True)

        self._file: io.TextIOWrapper = None

        super().__init__()

    @override
    def start(self, habmoti: Habmoti) -> None:
        self._file = open(self._filepath, "w")

        header = "timestamp, " + ", ".join(
            [
                f"{joint_center.name}_x, {joint_center.name}_y, {joint_center.name}_z"
                for joint_center in habmoti.device.joint_center_type
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
