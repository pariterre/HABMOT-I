from abc import ABC, abstractmethod
from typing import override, TYPE_CHECKING

if TYPE_CHECKING:
    from ..data.frame_data import FrameData
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
