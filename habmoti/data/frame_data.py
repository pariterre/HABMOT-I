from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .analysis import Analysis

if TYPE_CHECKING:
    from .body_kinematics import BodyKinematics


@dataclass(frozen=True)
class FrameData:
    timestamp: float
    body_kinematics: BodyKinematics
    analysis: Analysis = field(default_factory=Analysis)
