from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..data.body_kinematics import BodyModel
    from ..data.frame_data import FrameData


class Device(ABC):
    @property
    @abstractmethod
    def body_model(self) -> type[BodyModel]:
        """
        The type of body model provided by this device (this must be the same declared in BodyKinematics)
        """

    @abstractmethod
    def start(self) -> None:
        """
        Start the device. This method should be called before calling get_current_frame_data.
        """

    @abstractmethod
    def get_current_frame_data(self) -> FrameData | None:
        """
        Get the current frame data from the device.
        """

    @abstractmethod
    def stop(self) -> None:
        """
        Stop the device. This method should be called to release any resources used by the device.
        """
