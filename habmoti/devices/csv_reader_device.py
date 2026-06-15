import datetime
from pathlib import Path
import time
from typing import override, TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray
from packaging import version as version_checker

from .device import Device
from ..analyzers.writers.to_csv_analyzer import _csv_version as csv_version
from ..data.body_kinematics import BodyModel18Joints, BodyKinematics
from ..data.frame_data import FrameData
from ..version import __version__ as habmoti_version

if TYPE_CHECKING:
    from ..habmoti import Habmoti
    from ..data.body_kinematics import BodyModel


class CsvReaderDevice(Device):
    def __init__(self, filepath: Path, frame_per_second: int | None = None, terminate_on_end: bool = False):
        """
        Reading a file and streaming the data as if it was a device

        Args:
            filepath: The path of the file to read
            frame_per_second: The target fps to stream the data, as integer.
                - None is as fast as possible
                - A negative value targets to replicate the original frame rate
                - Zero (0) is on a frame by frame basis (i.e. pressing enter between each frame)
                - A positive value is a fixed value
            terminate_on_end: Whether to stop the pipeline when the end of the file is reached, 
                If True, a terminate signal will be sent to the analyzers when the end of the file is reached.
                If False, a stop_trial signal will be sent to the analyzers when the end of the file is reached.
        """

        self._filepath = Path(filepath)
        if self._filepath.suffix != "" and self._filepath.suffix != ".csv":
            raise ValueError("The filepath must have a .csv extension (or left empty)")
        self._filepath = self._filepath.with_suffix(".csv")

        self._habmoti: Habmoti | None = None

        self._frame_per_second = frame_per_second
        self._terminate_on_end = terminate_on_end
        try:
            self._parse_header()
        except Exception as e:
            raise ValueError(f"Failed to parse the header of the CSV file: {e}")
        self._data: NDArray[np.float64] = None
        self._current_index: int = None
        self._previous_frame_time: time.time = None

    @property
    @override
    def name(self) -> str:
        return f"CSV Reader ({self._filepath.name})"

    @override
    def start(self, habmoti: Habmoti) -> None:
        self._habmoti = habmoti

        self._data = np.genfromtxt(self._filepath, delimiter=",", skip_header=self._header_len + 1)
        self._data = self._data[1:]  # Remove the header row (all nans)
        self._current_index = -1
        self._previous_frame_time = time.time()

    @override
    def get_current_frame_data(self) -> FrameData | None:
        if self._current_index < 0 and not self._habmoti.is_trial_started:
            self._habmoti.start_trial()
        elif self._current_index >= self._data.shape[0] and self._habmoti.is_trial_started:
            if self._terminate_on_end:
                self._habmoti.terminate()
            else:
                self._habmoti.stop_trial()

        self._current_index += 1
        if self._current_index >= self._data.shape[0]:
            return None

        if self._frame_per_second is None:
            pass  # Serve data as fast as possible
        elif self._frame_per_second == 0:
            input("Press Enter to continue to the next frame...")
        elif self._frame_per_second < 0:
            idx = self._current_index
            self._delay_frame(delta_time=0 if idx < 1 else ((self._data[idx, 0] - self._data[idx - 1, 0]) / 1000))
        else:
            self._delay_frame(delta_time=1 / self._frame_per_second)

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
        self._previous_frame_time = None

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

    def _delay_frame(self, delta_time: float):
        current_time = time.time()
        time_to_sleep = (self._previous_frame_time + delta_time) - current_time
        self._previous_frame_time = current_time
        if time_to_sleep > 0:
            time.sleep(time_to_sleep)
            self._previous_frame_time += time_to_sleep

    @property
    def date(self) -> datetime.datetime:
        return self._date

    @property
    def device_type(self) -> str:
        return self._device_type

    @property
    @override
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
