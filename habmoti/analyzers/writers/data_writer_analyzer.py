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

    def start_trial(self) -> None:
        """
        Starts a trial.
        """
        self._is_writing = True

    def stop_trial(self) -> None:
        """
        Stops a trial.
        """
        self._is_writing = False
