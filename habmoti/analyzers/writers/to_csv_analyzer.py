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
    def __init__(self, filepath: Path, auto_increment: bool = True, allow_overwrite: bool = False):
        """
        An analyzer that writes the data to a CSV file.

        Args:
            filepath: The path to the CSV file to write to. If [auto_increment] is True, a suffix ("_X") is added to the
            filename to avoid overwriting existing files.
            auto_increment: Whether to automatically increment the filename if a file with the same name already exists.
            allow_overwrite: Whether to allow overwriting existing files. Ignored if [auto_increment] is True as it already prevents overwriting.
        """

        self._filepath = Path(filepath)
        self._auto_increment = auto_increment
        self._allow_overwrite = allow_overwrite
        if not self._allow_overwrite and not self._auto_increment and self._filepath.exists():
            raise FileExistsError(
                f"The file {self._filepath} already exists and overwrite is not allowed. Either change the filename, "
                "allow overwrite, or enable auto-increment."
            )

        self._folder = self._filepath.parent
        self._folder.mkdir(parents=True, exist_ok=True)
        self._filename = self._filepath.stem
        if self._filepath.suffix != "" and self._filepath.suffix != ".csv":
            raise ValueError("The filepath must have a .csv extension (or left empty)")
        self._extension = ".csv"

        self._file: io.TextIOWrapper = None
        self._writing_mutex = Lock()

        self._device_type = None
        self._body_model = None
        super().__init__()

    @property
    @override
    def name(self) -> str:
        return f"CSV Writer ({self._filename})"

    def _path_to_save(self) -> Path:
        path = self._filepath
        if self._auto_increment:
            counter = 0
            while True:
                path = self._folder / f"{self._filename}_{counter}{self._extension}"
                if not path.exists():
                    return path
                counter += 1
        if not self._allow_overwrite and path.exists():
            raise FileExistsError(
                f"The file {path} already exists and overwrite is not allowed. Either change the filename, "
                "allow overwrite, or enable auto-increment."
            )
        return path

    @override
    def initialize(self, habmoti: Habmoti) -> None:
        self._device_type = habmoti.device.__class__.__name__
        self._body_model = habmoti.device.body_model

    @override
    def start_trial(self) -> None:
        if self.is_writing:
            raise RuntimeError(
                "Cannot start a new trial while already writing. Please stop the current trial before starting a new one."
            )

        with self._writing_mutex:
            try:
                self._filepath = self._path_to_save()
                self._file = open(self._filepath, "w")
                self._file.write(self._generate_header() + "\n")
                super().start_trial()
            except Exception as e:
                self._stop_trial()
                raise e

    @override
    def perform(self, frame_data: FrameData | None) -> None:
        if frame_data is None:
            return 
        
        with self._writing_mutex:
            if not self.is_writing:
                return

            timestamp = frame_data.timestamp
            data = f"{frame_data.body_kinematics.joint_centers.flatten().tolist()}"
            self._file.write(f"{timestamp}, {data[1:-1]}\n")

    @override
    def stop_trial(self) -> None:
        if not self.is_writing:
            return

        with self._writing_mutex:
            self._stop_trial()

    @override
    def dispose(self) -> None:
        with self._writing_mutex:
            if self.is_writing:
                self._stop_trial()

    @override
    def _stop_trial(self) -> None:
        if self._file is not None:
            self._file.flush()
            self._file.close()
        self._file = None
        super().stop_trial()

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
