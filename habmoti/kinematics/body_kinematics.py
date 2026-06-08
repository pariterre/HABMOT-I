from dataclasses import dataclass
from enum import IntEnum
from typing import Generic, TypeVar

import numpy as np
from numpy.typing import NDArray


class JointCenter(IntEnum):
    @property
    def label(self) -> str:
        return self.name.lower()


class JointCenter18Joints(JointCenter):
    NOSE = 0
    RIGHT_KNEE = 9
    NECK = 1
    RIGHT_ANKLE = 10
    RIGHT_SHOULDER = 2
    LEFT_HIP = 11
    RIGHT_ELBOW = 3
    LEFT_KNEE = 12
    RIGHT_WRIST = 4
    LEFT_ANKLE = 13
    LEFT_SHOULDER = 5
    RIGHT_EYE = 14
    LEFT_ELBOW = 6
    LEFT_EYE = 15
    LEFT_WRIST = 7
    RIGHT_EAR = 16
    RIGHT_HIP = 8
    LEFT_EAR = 17


JC = TypeVar("JC", bound=JointCenter)


@dataclass(frozen=True)
class BodyKinematics(Generic[JC]):
    joint_center_type: type[JC]
    values: NDArray[np.float64]

    def __post_init__(self) -> None:
        if self.values.ndim != 2 or self.values.shape[1] != 3:
            raise ValueError("Expected shape (n_joints, 3)")

    @property
    def joint_centers(self) -> NDArray[np.float64]:
        return self.values


@dataclass(frozen=True)
class MultiBodyKinematics(BodyKinematics[JC]):
    joint_center_type: type[JC]
    values: list[NDArray[np.float64]]

    def __post_init__(self) -> None:
        for value in self.values:
            if value.ndim != 2 or value.shape[1] != 3:
                raise ValueError("Expected shape (n_joints, 3)")

    @property
    def joint_centers(self) -> NDArray[np.float64]:
        return np.mean(self.values, axis=0)
