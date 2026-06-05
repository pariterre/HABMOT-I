from dataclasses import dataclass
from enum import Enum, auto


class JointCenter(Enum):
    LEFT_SHOULDER = auto()
    RIGHT_SHOULDER = auto()
    LEFT_ELBOW = auto()
    RIGHT_ELBOW = auto()
    LEFT_WRIST = auto()
    RIGHT_WRIST = auto()


@dataclass(frozen=True)
class BodyKinematics:
    joint_centers: dict[JointCenter, tuple[float, float, float]]
