from enum import IntEnum
from typing import Generic, TypeVar, override

import numpy as np
from numpy.typing import NDArray

from ..utils.maths import create_system_of_axes, AxisName

type point_type = list[int]
type axis_type = tuple[point_type, point_type]
type coordinate_system_type = tuple[axis_type, tuple[axis_type, AxisName], tuple[axis_type, AxisName], AxisName]


class BodyModel(IntEnum):
    @property
    def label(self) -> str:
        return self.name.lower()

    @staticmethod
    def from_name(name: str) -> "BodyModel":
        raise NotImplementedError("This method should be implemented in subclasses of BodyModel")

    @staticmethod
    def segment_links() -> list[tuple["BodyModel", "BodyModel"]]:
        raise NotImplementedError("This method should be implemented in subclasses of BodyModel")

    @staticmethod
    def body_coordinate_systems_indices() -> coordinate_system_type:
        raise NotImplementedError("This method should be implemented in subclasses of BodyModel")


class BodyModel18Joints(BodyModel):
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

    @staticmethod
    def from_name(name: str) -> "BodyModel":
        return BodyModel18Joints[name.upper()]

    @staticmethod
    def segment_links() -> list[tuple["BodyModel", "BodyModel"]]:
        # Define the segment links for the 18-joint model
        return [
            (BodyModel18Joints.NOSE, BodyModel18Joints.NECK),
            (BodyModel18Joints.NECK, BodyModel18Joints.RIGHT_SHOULDER),
            (BodyModel18Joints.NECK, BodyModel18Joints.LEFT_SHOULDER),
            (BodyModel18Joints.RIGHT_SHOULDER, BodyModel18Joints.RIGHT_ELBOW),
            (BodyModel18Joints.LEFT_SHOULDER, BodyModel18Joints.LEFT_ELBOW),
            (BodyModel18Joints.RIGHT_ELBOW, BodyModel18Joints.RIGHT_WRIST),
            (BodyModel18Joints.LEFT_ELBOW, BodyModel18Joints.LEFT_WRIST),
            (BodyModel18Joints.NECK, BodyModel18Joints.RIGHT_HIP),
            (BodyModel18Joints.NECK, BodyModel18Joints.LEFT_HIP),
            (BodyModel18Joints.RIGHT_HIP, BodyModel18Joints.RIGHT_KNEE),
            (BodyModel18Joints.LEFT_HIP, BodyModel18Joints.LEFT_KNEE),
            (BodyModel18Joints.RIGHT_KNEE, BodyModel18Joints.RIGHT_ANKLE),
            (BodyModel18Joints.LEFT_KNEE, BodyModel18Joints.LEFT_ANKLE),
        ]

    @staticmethod
    def body_coordinate_systems_indices() -> coordinate_system_type:
        origin = [BodyModel18Joints.NECK, BodyModel18Joints.RIGHT_HIP, BodyModel18Joints.LEFT_HIP]
        first_axis = [[BodyModel18Joints.RIGHT_HIP], [BodyModel18Joints.LEFT_HIP]]
        second_axis = [origin, [BodyModel18Joints.NECK]]
        return [origin, [first_axis, AxisName.X], [second_axis, AxisName.Y], AxisName.X]


BodyModelType = TypeVar("BodyModelType", bound=BodyModel)


class BodyKinematics(Generic[BodyModelType]):

    def __init__(self, body_model: type[BodyModelType], values: NDArray[np.float64]) -> None:
        self._body_model = body_model
        self._values = values

        if self._values.ndim != 2 or self._values.shape[1] != 3:
            raise ValueError("Expected shape (n_joints, 3)")

    @property
    def body_model(self) -> type[BodyModelType]:
        return self._body_model

    def values(self) -> NDArray[np.float64]:
        return self._values

    @property
    def joint_centers(self) -> NDArray[np.float64]:
        return self._values

    @property
    def body_list(self) -> list[NDArray[np.float64]]:
        return [self._values]

    @property
    def body_coordinate_system(self) -> list[coordinate_system_type]:
        origin_indices, first_axis, second_axis, keep_axis = self._body_model.body_coordinate_systems_indices()
        first_axis_indices, first_axis_name = first_axis
        second_axis_indices, second_axis_name = second_axis

        origin = np.mean(self._values[origin_indices, :], axis=0)
        first_axis_start = np.mean(self._values[first_axis_indices[0], :], axis=0)
        first_axis_end = np.mean(self._values[first_axis_indices[1], :], axis=0)
        second_axis_start = np.mean(self._values[second_axis_indices[0], :], axis=0)
        second_axis_end = np.mean(self._values[second_axis_indices[1], :], axis=0)
        axis_to_keep = keep_axis

        return [
            create_system_of_axes(
                origin=origin,
                first_axis=first_axis_end - first_axis_start,
                first_axis_name=first_axis_name,
                second_axis=second_axis_end - second_axis_start,
                second_axis_name=second_axis_name,
                keep_axis=axis_to_keep,
            )
        ]


class MultiBodyKinematics(BodyKinematics[BodyModelType]):

    def __init__(self, body_model: type[BodyModelType], values: list[NDArray[np.float64]]) -> None:
        self._body_model = body_model
        self._values = values

        for value in self._values:
            if value.ndim != 2 or value.shape[1] != 3:
                raise ValueError("Expected shape (n_joints, 3)")

    @property
    def body_model(self) -> type[BodyModelType]:
        return self._body_model

    def values(self) -> list[NDArray[np.float64]]:
        return self._values

    @property
    def joint_centers(self) -> NDArray[np.float64]:
        return np.mean(self._values, axis=0)

    @override
    @property
    def body_list(self) -> list[NDArray[np.float64]]:
        return self._values

    @property
    def body_coordinate_system(self) -> list[coordinate_system_type]:
        raise NotImplementedError("Body coordinate systems are not implemented for MultiBodyKinematics yet")
