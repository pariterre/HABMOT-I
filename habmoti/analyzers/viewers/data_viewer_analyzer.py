from typing import override

from ..analyzer import Analyzer


class DataViewerAnalyzer(Analyzer):
    @override
    def start_trial(self) -> None:
        pass

    @override
    def stop_trial(self) -> None:
        pass
