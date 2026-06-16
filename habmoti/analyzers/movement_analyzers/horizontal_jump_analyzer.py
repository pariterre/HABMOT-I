from typing import override, TYPE_CHECKING

from .data_movement_analyzer import DataMovementAnalyzer
from ...data.frame_data import FrameData

if TYPE_CHECKING:
    from ..analyzer import Habmoti


class HorizontalJumpAnalyzer(DataMovementAnalyzer):
    def __init__(self):
        super().__init__()

        self._is_analyzing = False
        self._jump_start_frames: list[int] | None = None
        self._jump_end_frames: list[int] | None = None

    @property
    @override
    def name(self) -> str:
        return "Horizontal jump"

    @override
    def initialize(self, habmoti: Habmoti) -> None:
        print("Initializing Horizontal jump")
        self._jump_start_frames = []
        self._jump_end_frames = []

    @override
    def start_trial(self) -> None:
        self._is_analyzing = True
        print("Starting to analyze horizontal jump")

    @override
    def perform(self, frame_data: FrameData | None) -> None:
        if self._is_analyzing:
            print("Analyzing horizontal jump frame")
        pass

    @override
    def stop_trial(self) -> None:
        self._is_analyzing = False
        print("Stopping horizontal jump analysis")

    @override
    def dispose(self) -> None:
        self._jump_start_frames = None
        self._jump_end_frames = None
