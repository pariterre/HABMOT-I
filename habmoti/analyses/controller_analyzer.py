from time import time
from typing import override, TYPE_CHECKING

from .analysis import AnalysesType
from .analyzer import Analyzer, FrameData

if TYPE_CHECKING:
    from ..habmoti import Habmoti


class ControllerAnalyzer(Analyzer):
    def __init__(self, max_runtime: float = None):
        super().__init__()
        self._habmoti: Habmoti | None = None
        self._is_stopped = True

        self._max_runtime = max_runtime
        self._start_time = None

    @override
    def start(self, habmoti: Habmoti) -> None:
        """
        Start the analyzer. This is called before the first frame is analyzed.
        """
        self._habmoti = habmoti
        self._is_stopped = False
        self._start_time = time()

    @override
    def perform(self, frame_data: FrameData) -> None:
        """
        Analyze a frame of data.

        Args:
            frame_data: The data to analyze. The analysis is stored in the frame_data itself
        """
        if not self._is_stopped:
            stop_requested = (
                AnalysesType.STOP_RECORDING in frame_data.analysis.current
                and frame_data.analysis.current[AnalysesType.STOP_RECORDING]
            )
            has_timed_out = self._max_runtime is not None and (time() - self._start_time) > self._max_runtime
            if stop_requested or has_timed_out:
                self._habmoti.stop()
                self._is_stopped = True

    @override
    def stop(self) -> None:
        """
        Stop the analyzer. This is called when the analyzer is no longer needed.
        """
        self._habmoti = None
        self._is_stopped = True
