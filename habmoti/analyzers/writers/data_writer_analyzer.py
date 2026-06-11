from abc import abstractmethod
from ..analyzer import Analyzer


class DataWriterAnalyzer(Analyzer):
    def __init__(self):
        super().__init__()

        self._is_writing = False

    @property
    def is_writing(self) -> bool:
        """
        Returns whether the analyzer is currently writing data.
        """
        return self._is_writing

    def start_writing(self) -> None:
        """
        Starts writing data.
        """
        self._is_writing = True

    def stop_writing(self) -> None:
        """
        Stops writing data.
        """
        self._is_writing = False
