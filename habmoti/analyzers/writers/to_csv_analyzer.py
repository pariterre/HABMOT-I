import io
from threading import Lock
from pathlib import Path
import datetime
from typing import override, TYPE_CHECKING

from .data_writer_analyzer import DataWriterAnalyzer
from ...version import __version__ as habmoti_version

if TYPE_CHECKING:
    from ..analyzer import FrameData
    from ..analyzer import Habmoti

_csv_version = "1.0.0"


class ToCsvAnalyzer(DataWriterAnalyzer):
    def __init__(self, filepath: Path):
        self._filepath = filepath
        self._filepath.parent.mkdir(parents=True, exist_ok=True)
        self._writing_mutex = Lock()

        self._file: io.TextIOWrapper = None

        self._device_type = None
        self._body_model = None
        super().__init__()

    @override
    def initialize(self, habmoti: Habmoti) -> None:
        self._device_type = habmoti.device.__class__.__name__
        self._body_model = habmoti.device.body_model
        self.start_writing()

    @override
    def start_writing(self) -> None:
        with self._writing_mutex:
            if self._file is not None:
                raise RuntimeError("Cannot start writing as the file is already open")

            try:
                self._file = open(self._filepath, "w")
                self._file.write(self._generate_header() + "\n")
                super().start_writing()
            except Exception as e:
                self._close_file_if_open()
                raise e

    @override
    def perform(self, frame_data: FrameData) -> None:
        with self._writing_mutex:
            timestamp = frame_data.timestamp
            data = f"{frame_data.body_kinematics.joint_centers.flatten().tolist()}"
            self._file.write(f"{timestamp}, {data[1:-1]}\n")

    @override
    def stop_writing(self) -> None:
        with self._writing_mutex:
            self._stop_writing()

    @override
    def dispose(self) -> None:
        with self._writing_mutex:
            if self.is_writing:
                self._stop_writing()

    @override
    def _stop_writing(self) -> None:
        if self._file is None:
            raise RuntimeError("Cannot stop writing as the file is not open")

        self._close_file_if_open()
        super().stop_writing()

    def _generate_header(self) -> str:
        """
        Generates the CSV header.
        """

        metadata = (
            "startheader\n"
            f"  date: {datetime.datetime.now():%Y-%m-%d %H:%M:%S}\n"
            f"  device_type: {self._device_type}\n"
            f"  body_model: {self._body_model.__name__}\n"
            f"  file_type: csv\n"
            f"  habmoti_version: {habmoti_version}\n"
            f"  csv_version: {_csv_version}\n"
            "endheader\n"
            "\n\n"
        )

        return (
            metadata
            + "timestamp, "
            + ", ".join(
                [
                    f"{joint_center.name}_x, {joint_center.name}_y, {joint_center.name}_z"
                    for joint_center in self._body_model
                ]
            )
        )

    def _close_file_if_open(self) -> None:
        if self._file is not None:
            self._file.flush()
            self._file.close()
            self._file = None
