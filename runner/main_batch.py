import json
import logging
import os
from pathlib import Path

from habmoti import csv_read_multiple_files


def main():
    logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(filename)s - %(levelname)s - %(message)s")

    files = [Path(f) for f in json.loads(os.getenv("FILES_TO_PROCESS", "[]"))]
    analyzers = json.loads(os.getenv("ANALYZER_TO_USE", "[]"))

    for analyzer in csv_read_multiple_files(files=files, analyzers=analyzers):
        # Do whatever analyses you want with the analyzer object here
        print(f"{analyzer.criteria if analyzer.criteria is not None else 'No criteria available'}")

        # # Here are the relevent properties of the analyzer object that you can use:
        # analyzer.data  # Access the data as collected by the device
        # analyzer.data_centered  # Access with the center of mass centered over the origin
        # analyzer.criteria  # Access the criteria of the analyzer, which contains the results of the analysis
        # analyzer.show_data()  # Show the debug graphs of the analyzer


if __name__ == "__main__":
    main()
