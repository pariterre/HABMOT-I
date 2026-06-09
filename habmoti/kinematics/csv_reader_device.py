import datetime
import pathlib as Path
from time import sleep
from typing import override, TYPE_CHECKING

import numpy as np
from packaging import version as version_checker

from .body_kinematics_device import BodyKinematicsDevice
from ..data.body_kinematics import BodyModel18Joints, BodyKinematics
from ..data.frame_data import FrameData
from ..version import __version__ as habmoti_version
from ..analyzers.file_io.to_csv_analyzer import _csv_version as csv_version

if TYPE_CHECKING:
    from ..data.body_kinematics import BodyModel


class CsvReaderDevice(BodyKinematicsDevice):
    def __init__(self, filepath: Path):
        self._filepath = filepath
        self._parse_header()
        self._data = None
        self._current_index = None

    @override
    def start(self) -> None:
        self._data = np.genfromtxt(self._filepath, delimiter=",", skip_header=self._header_len + 1)
        self._data = self._data[1:]  # Remove the header row (all nans)
        self._current_index = -1

    @override
    def get_current_frame_data(self) -> FrameData | None:
        self._current_index += 1
        if self._current_index >= self._data.shape[0]:
            return None

        return FrameData(
            timestamp=int(self._data[self._current_index, 0]),
            body_kinematics=BodyKinematics(
                body_model=self.body_model,
                values=self._data[self._current_index, 1:].reshape(-1, 3),
            ),
        )

    @override
    def stop(self) -> None:
        self._data = None
        self._current_index = None

    def _parse_header(self) -> list[str]:
        header = []
        with open(self._filepath, "r") as f:
            # Read the header
            for line in f:
                line = line.strip()
                if line == "endheader":
                    break
                header.append(line)

        parsers = {  # None refers to a mandatory field
            "date": [None, lambda x: _parse_date(x, default=datetime.datetime.now())],
            "device_type": [None, lambda x: _parse_device_type(x, default="Not specified")],
            "body_model": [None, lambda x: _parse_body_model(x)],
            "file_type": [None, lambda x: _parse_file_type(x, default="csv")],
            "habmoti_version": [None, lambda x: _parse_habmoti_version(x, default=habmoti_version)],
            "csv_version": [None, lambda x: _parse_csv_version(x, default=csv_version)],
        }
        for key in parsers.keys():
            for line in header:
                if line.startswith(f"{key}:"):
                    parsers[key][0] = parsers[key][1](line[len(f"{key}:") :].strip())
                    break
            if parsers[key][0] is None:
                # Fallback to default
                parsers[key][0] = parsers[key][1](None)

        self._header_len = len(header)
        self._date: datetime.datetime = parsers["date"][0]
        self._device_type: str = parsers["device_type"][0]
        self._body_model: type[BodyModel] = parsers["body_model"][0]
        self._file_type: str = parsers["file_type"][0]
        self._habmoti_version: str = parsers["habmoti_version"][0]
        self._csv_version: str = parsers["csv_version"][0]

    @property
    def date(self) -> datetime.datetime:
        return self._date

    @property
    def device_type(self) -> str:
        return self._device_type

    @property
    def body_model(self) -> type[BodyModel]:
        return self._body_model

    @property
    def file_type(self) -> str:
        return self._file_type

    @property
    def habmoti_version(self) -> str:
        return self._habmoti_version

    @property
    def csv_version(self) -> str:
        return self._csv_version


def _parse_date(date: str, default: datetime.datetime) -> datetime.datetime:
    try:
        return datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return default


def _parse_device_type(name: str, default: str) -> str:
    if name is None:
        name = default
    return name


def _parse_body_model(name: str) -> type[BodyModel]:
    if name == "BodyModel18Joints":
        return BodyModel18Joints
    else:
        raise ValueError(f"Unsupported body model: {name}")


def _parse_file_type(file_type: str, default: str) -> str:
    if file_type is None:
        file_type = default

    if file_type != "csv":
        raise ValueError(f"Unsupported file type: {file_type}")
    return file_type


def _parse_habmoti_version(version: str, default: str) -> str:
    if version is None:
        version = default
    return version


def _parse_csv_version(version: str, default: str) -> str:
    if version is None:
        version = default

    if version_checker.parse(version) < version_checker.parse("1.0.0"):
        raise ValueError(f"Unsupported csv version: {version}")
    elif version_checker.parse(version) >= version_checker.parse("2.0.0"):
        raise ValueError(f"Unsupported csv version: {version}")
    return version
