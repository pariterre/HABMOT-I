from abc import ABC, abstractmethod

from .body_kinematics import BodyKinematics, JointCenter


class BodyKinematicsDevice(ABC):
    @property
    @abstractmethod
    def joint_center_type(self) -> JointCenter:
        """
        The type of joint centers provided by this device (this must be the same declared in BodyKinematics)
        """

    @abstractmethod
    def start(self) -> None:
        """
        Start the device. This method should be called before calling get_current_body_kinematics.
        """

    @abstractmethod
    def get_current_body_kinematics(self) -> BodyKinematics:
        """
        Get the current body kinematics from the device.
        """

    @abstractmethod
    def stop(self) -> None:
        """
        Stop the device. This method should be called to release any resources used by the device.
        """
