from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..habmoti import Habmoti
    from ..data.body_kinematics import BodyModel
    from ..data.frame_data import FrameData


class Device(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """
        The name of the device. This is used to identify the device in the CLI and in the logs.
        """

    @property
    @abstractmethod
    def body_model(self) -> type[BodyModel]:
        """
        The type of body model provided by this device (this must be the same declared in BodyKinematics)
        """

    @abstractmethod
    def start(self, habmoti: Habmoti) -> None:
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
