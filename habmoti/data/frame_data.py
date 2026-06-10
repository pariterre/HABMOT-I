from dataclasses import dataclass, field
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from .body_kinematics import BodyKinematics


@dataclass(frozen=True)
class FrameData:
    """
    Data for a single frame of motion capture data.

    Attributes:
        timestamp: The timestamp to epoch of the frame in milliseconds.
        body_kinematics: The kinematics of the body for this frame.
        analysis: The analysis results for this frame, which can be populated after processing the kinematics
    """

    timestamp: int
    body_kinematics: BodyKinematics
