from abc import ABC, abstractmethod

from ..data.frame_data import FrameData


class Viewer(ABC):
    @abstractmethod
    def start(self) -> None:
        """
        Start the viewer. This method is called before the first call to update.
        """

    @abstractmethod
    def update(self, frame_data: FrameData) -> None:
        """
        Update the viewer with a new frame of data.

        Args:
            frame_data: The data to display.
        """

    def stop(self) -> None:
        """
        Stop the viewer. This method is called after the last call to update.
        """
