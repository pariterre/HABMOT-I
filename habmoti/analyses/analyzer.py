from abc import ABC, abstractmethod
from typing import override

from ..data.frame_data import FrameData


class Analyzer(ABC):
    @abstractmethod
    def perform(self, frame_data: FrameData) -> None:
        """
        Analyze a frame of data.

        Args:
            frame_data: The data to analyze. The analysis is stored in the frame_data itself
        """


class AnalyzerList(Analyzer):
    def __init__(self, analyzers: list[Analyzer]):
        self.analyzers = analyzers

    @override
    def perform(self, frame_data: FrameData) -> None:
        for analyzer in self.analyzers:
            analyzer.perform(frame_data)


class EmptyAnalyzer(Analyzer):
    @override
    def perform(self, frame_data: FrameData) -> None:
        pass
