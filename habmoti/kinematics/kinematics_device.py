from abc import ABC, abstractmethod
from typing import Any

from .body_kinematics import BodyKinematics


class KinematicsDevice(ABC):
    @abstractmethod
    def get_current_body_kinematics(self) -> BodyKinematics:
        """
        Get the current body kinematics from the device.
        """

    @abstractmethod
    def get_raw_data(self) -> Any:
        """
        Get the raw data from the device. The data are expected to be serializable
        """
