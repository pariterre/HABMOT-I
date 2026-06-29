import json
import logging
import os
from pathlib import Path

from habmoti import (
    Habmoti,
    CsvReaderDevice,
    GallopAnalyzer,
    HopAnalyzer,
    HorizontalJumpAnalyzer,
    RunAnalyzer,
    SkipAnalyzer,
    SlideAnalyzer,
)


def main():
    logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(filename)s - %(levelname)s - %(message)s")

    files = json.loads(os.getenv("FILES_TO_PROCESS", "[]"))
    analyzers = json.loads(os.getenv("ANALYZER_TO_USE", "[]"))
    if len(analyzers) == 1:
        analyzers = analyzers * len(files)
    if len(files) != len(analyzers):
        raise ValueError(
            f"Number of files ({len(files)}) and analyzers ({len(analyzers)}) must be the same or there must be only one analyzer."
        )

    for data in extract_files(files, analyzers):
        print(data[2])


def extract_files(files: list[str], analyzers: list[str], show_debug_graphs: bool = False):
    habmoti = Habmoti()

    for file, analyzer_name in zip(files, analyzers):
        device = CsvReaderDevice(filepath=Path(file))
        if analyzer_name == "gallop":
            analyzer = GallopAnalyzer(show_debug_graphs=show_debug_graphs)
        elif analyzer_name == "hop":
            analyzer = HopAnalyzer(show_debug_graphs=show_debug_graphs)
        elif analyzer_name == "horizontal_jump":
            analyzer = HorizontalJumpAnalyzer(show_debug_graphs=show_debug_graphs)
        elif analyzer_name == "run":
            analyzer = RunAnalyzer(show_debug_graphs=show_debug_graphs)
        elif analyzer_name == "skip":
            analyzer = SkipAnalyzer(show_debug_graphs=show_debug_graphs)
        elif analyzer_name == "slide":
            analyzer = SlideAnalyzer(show_debug_graphs=show_debug_graphs)
        else:
            raise ValueError(f"Unknown analyzer: {analyzer_name}")

        habmoti.analyzer = None
        habmoti.device = device
        habmoti.analyzer = analyzer
        habmoti.initialize()
        habmoti.wait_for_trial_to_end()

        yield (analyzer.data, analyzer.data_centered, analyzer.analyzed_data)

        habmoti.terminate()
        habmoti.wait_for_termination()


if __name__ == "__main__":
    main()
