from typing import override, TYPE_CHECKING

from .data_movement_analyzer import DataMovementAnalyzer

if TYPE_CHECKING:
    from ..analyzer import Habmoti, FrameData


class HopAnalyzer(DataMovementAnalyzer):
    def __init__(self):
        super().__init__()

        self._is_analyzing = False
        self._jump_start_frames: list[int] | None = None
        self._jump_end_frames: list[int] | None = None

    @property
    @override
    def name(self) -> str:
        return "Hop"

    @override
    def initialize(self, habmoti: Habmoti) -> None:
        print("Initializing Hop")
        self._jump_start_frames = []
        self._jump_end_frames = []

    @override
    def start_trial(self) -> None:
        self._is_analyzing = True
        print("Starting to analyze hop")

    @override
    def perform(self, frame_data: FrameData | None) -> None:
        if self._is_analyzing:
            print("Analyzing hop frame")
        pass
        
    @override
    def stop_trial(self) -> None:
        self._is_analyzing = False
        print("Stopping hop analysis")

    @override
    def dispose(self) -> None:
        self._jump_start_frames = None
        self._jump_end_frames = None