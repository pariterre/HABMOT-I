import json
import os
from pathlib import Path

from ..analyzers.analyzer import Analyzer, AnalyzerList
from ..analyzers.viewers.to_console_analyzer import ToConsoleAnalyzer
from ..analyzers.viewers.to_matplotlib_analyzer import ToMatplotlibAnalyzer
from ..analyzers.viewers.to_ogl_analyzer import ToOglAnalyzer
from ..analyzers.writers.to_csv_analyzer import ToCsvAnalyzer
from ..devices.device import Device
from ..devices.csv_reader_device import CsvReaderDevice
from ..devices.zed_device import ZedDevice, MockedZedDevice
from ..habmoti import Habmoti


class InterfaceFormEnvironment:
    """
    Class representing the environment of an interface form.
    """

    def __init__(self) -> None:
        self._device = _select_device()
        self._analyzers = _select_analyzers(device=self._device)
        self._habmoti = Habmoti(device=self._device, analyzer=self._analyzers)

    def exec(self) -> None:
        self._habmoti.start(blocking=True)


def _select_device() -> Device:
    device_type = os.getenv("HABMOTI_DEVICE_TYPE")
    if device_type is None:
        raise ValueError("Environment variable 'HABMOTI_DEVICE_TYPE' is not set")

    if device_type == "zed":
        parameters = json.loads(os.getenv("HABMOTI_ZED_PARAMETERS", "{}"))
        device = ZedDevice(**parameters)
    elif device_type == "mocked_zed":
        zed_parameters = json.loads(os.getenv("HABMOTI_ZED_PARAMETERS", "{}"))
        mock_parameters = json.loads(os.getenv("HABMOTI_MOCKED_ZED_PARAMETERS", "{}"))
        device = MockedZedDevice(**mock_parameters | zed_parameters)
    elif device_type == "csv_reader":
        parameters = json.loads(os.getenv("HABMOTI_CSV_READER_PARAMETERS", "{}"))
        device = CsvReaderDevice(**parameters)
    else:
        raise NotImplementedError(f"Unsupported device type: {device_type}")
    return device


def _select_analyzers(device: Device) -> Analyzer:
    analyzers = AnalyzerList()
    for analyzer in json.loads(os.getenv("HABMOTI_ANALYZERS", "[]")):
        if analyzer == "to_console":
            parameters = json.loads(os.getenv("HABMOTI_TO_CONSOLE_ANALYZER_PARAMETERS", "{}"))
            if "joint_center" not in parameters:
                raise ValueError(
                    "Missing 'joint_center' parameter in the HABMOTI_TO_CONSOLE_ANALYZER_PARAMETERS environment variable"
                )
            analyzers.append(ToConsoleAnalyzer(joint_center=device.body_model.from_name(parameters["joint_center"])))
        elif analyzer == "to_csv":
            parameters = json.loads(os.getenv("HABMOTI_TO_CSV_ANALYZER_PARAMETERS", "{}"))
            if "filepath" not in parameters:
                raise ValueError(
                    "Missing 'filepath' parameter in the HABMOTI_TO_CSV_ANALYZER_PARAMETERS environment variable"
                )
            analyzers.append(ToCsvAnalyzer(filepath=Path(parameters["filepath"])))
        elif analyzer == "to_ogl":
            analyzers.append(ToOglAnalyzer())
        elif analyzer == "to_matplotlib":
            analyzers.append(ToMatplotlibAnalyzer())
        else:
            raise NotImplementedError(f"Unsupported analyzer type: {analyzer}")

    return analyzers
