from abc import ABC, abstractmethod
from typing import override, TYPE_CHECKING

if TYPE_CHECKING:
    from ..data.frame_data import FrameData
    from ..habmoti import Habmoti


class Analyzer(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """
        The name of the analyzer. This is used for display purposes and should be unique among analyzers.
        """

    @abstractmethod
    def initialize(self, habmoti: Habmoti) -> None:
        """
        Initialize the analyzer. This is called before the first frame is analyzed.
        """

    @abstractmethod
    def start_trial(self) -> None:
        """
        Start a trial. This is called when a trial is started. The perform method may be called after this method is called.
        """

    @abstractmethod
    def perform(self, frame_data: FrameData) -> None:
        """
        Analyze a frame of data.

        Args:
            frame_data: The data to analyze. The analysis is stored in the frame_data itself
        """

    @abstractmethod
    def stop_trial(self) -> None:
        """
        Stop a trial. This is called when a trial is stopped. The perform method should not be called after this method is called.
        """

    @abstractmethod
    def dispose(self) -> None:
        """
        Dispose the analyzer. This is called when the analyzer is no longer needed.
        The perform should not be called after this method is called. However, the initialize method may be called
        again to re-initialize the analyzer.
        """


class AnalyzerList(Analyzer):
    def __init__(self, analyzers: list[Analyzer] = None):
        self._analyzers = analyzers if analyzers is not None else []
        self._is_locked = False

    @property
    @override
    def name(self):
        return "List of analyzers"

    def append(self, analyzer: Analyzer) -> None:
        if self._is_locked:
            raise RuntimeError("Cannot append an analyzer to a locked AnalyzerList")
        self._analyzers.append(analyzer)

    @override
    def initialize(self, habmoti: Habmoti) -> None:
        self._is_locked = True
        for analyzer in self._analyzers:
            analyzer.initialize(habmoti=habmoti)

    @override
    def start_trial(self) -> None:
        for analyzer in self._analyzers:
            analyzer.start_trial()

    @override
    def perform(self, frame_data: FrameData) -> None:
        for analyzer in self._analyzers:
            analyzer.perform(frame_data)

    @override
    def stop_trial(self) -> None:
        for analyzer in self._analyzers:
            analyzer.stop_trial()

    @override
    def dispose(self) -> None:
        for analyzer in self._analyzers:
            analyzer.dispose()
        self._is_locked = False

    def __len__(self):
        return len(self._analyzers)

    def __getitem__(self, index):
        return self._analyzers[index]

    def __delitem__(self, key):
        if self._is_locked:
            raise RuntimeError("Cannot delete an analyzer from a locked AnalyzerList")
        del self._analyzers[key]

    def __iter__(self):
        return iter(self._analyzers)
