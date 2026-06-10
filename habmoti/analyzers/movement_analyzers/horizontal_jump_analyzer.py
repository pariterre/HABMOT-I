from dataclasses import dataclass
from typing import override, TYPE_CHECKING

from ..analyzer import Analyzer

if TYPE_CHECKING:
    from ..analyzer import Habmoti, FrameData


@dataclass
class JumpEvent:
    start_frame: int
    end_frame: int

class HorizontalJumpAnalyzer(Analyzer):
    def __init__(self):
        super().__init__()

        self.jump_start_frames: list[int] | None = None
        self.jump_end_frames: list[int] | None = None

    @override
    def start(self, habmoti: Habmoti) -> None:
        pass

    @override
    def perform(self, frame_data: FrameData) -> None:
        pass

    @override
    def stop(self) -> None:
        pass