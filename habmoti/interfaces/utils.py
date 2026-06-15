from ..analyzers.analyzer import Analyzer, AnalyzerList
from ..analyzers.movement_analyzers.hop_analyzer import HopAnalyzer
from ..analyzers.viewers.to_matplotlib_analyzer import ToMatplotlibAnalyzer
from ..analyzers.viewers.to_ogl_analyzer import ToOglAnalyzer
from ..analyzers.writers.to_console_analyzer import ToConsoleAnalyzer
from ..analyzers.writers.to_csv_analyzer import ToCsvAnalyzer
from ..devices.device import Device
from ..devices.csv_reader_device import CsvReaderDevice
from ..devices.zed_device import ZedDevice, ZedMockDevice
from ..habmoti import Habmoti

_device_factories = {
    "zed": ZedDevice,
    "zed_mock": ZedMockDevice,
    "csv_reader": CsvReaderDevice,
}

_analyzer_factories = {
    "to_console": ToConsoleAnalyzer,
    "to_csv": ToCsvAnalyzer,
    "to_ogl": ToOglAnalyzer,
    "to_matplotlib": ToMatplotlibAnalyzer,
    "hop": HopAnalyzer,
}


def habmoti_from_dict(habmoti: Habmoti | None, config: dict) -> Habmoti:
    device_config = config.get("device")
    if device_config is None or not isinstance(device_config, dict):
        raise ValueError("Device configuration is missing in the configuration dictionary")

    device = _load_device(device_config)

    analyzers_config = config.get("analyzers", [])
    if analyzers_config is None:
        analyzers_config = []
    if not isinstance(analyzers_config, list):
        raise ValueError("Analyzers configuration is missing or invalid in the configuration dictionary")
    analyzers = _load_analyzers(analyzers_config=analyzers_config)

    if habmoti is None:
        return Habmoti(device=device, analyzer=analyzers)
    else:
        habmoti.device = device
        habmoti.analyzer = analyzers
        return habmoti


def _load_device(device_config: dict) -> Device:
    if "name" not in device_config or device_config["name"] is None:
        raise ValueError("Device configuration must contain a 'name' key")

    device_name = device_config["name"]
    if device_name not in _device_factories:
        raise NotImplementedError(f"Unsupported device type: {device_name}")

    return _device_factories[device_name](**device_config.get("parameters", {}))


def _load_analyzers(analyzers_config: list) -> Analyzer:
    analyzers = AnalyzerList()

    for analyzer_config in analyzers_config:
        analyzer_name = analyzer_config.get("name")
        if analyzer_name not in _analyzer_factories:
            raise NotImplementedError(f"Unsupported analyzer type: {analyzer_name}")

        analyzers.append(_analyzer_factories[analyzer_name](**analyzer_config.get("parameters", {})))

    return analyzers
