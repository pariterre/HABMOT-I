import io
from pathlib import Path
import datetime
from typing import override, TYPE_CHECKING

from ..analyzer import Analyzer
from ...version import __version__ as habmoti_version

if TYPE_CHECKING:
    from ..analyzer import FrameData
    from ..analyzer import Habmoti

_csv_version = "1.0.0"


class ToCsvAnalyzer(Analyzer):
    def __init__(self, filepath: Path):
        self._filepath = filepath
        self._filepath.parent.mkdir(parents=True, exist_ok=True)

        self._file: io.TextIOWrapper = None

        super().__init__()

    @override
    def start(self, habmoti: Habmoti) -> None:
        self._file = open(self._filepath, "w")

        heading = (
            "startheader\n"
            f"  date: {datetime.datetime.now():%Y-%m-%d %H:%M:%S}\n"
            f"  device_type: {habmoti.device.__class__.__name__}\n"
            f"  body_model: {habmoti.device.body_model.__name__}\n"
            f"  file_type: csv\n"
            f"  habmoti_version: {habmoti_version}\n"
            f"  csv_version: {_csv_version}\n"
            "endheader\n"
            "\n\n"
        )

        header = (
            heading
            + "timestamp, "
            + ", ".join(
                [
                    f"{joint_center.name}_x, {joint_center.name}_y, {joint_center.name}_z"
                    for joint_center in habmoti.device.body_model
                ]
            )
        )
        self._file.write(header + "\n")

    @override
    def perform(self, frame_data: FrameData) -> None:
        timestamp = frame_data.timestamp
        data = f"{frame_data.body_kinematics.joint_centers.flatten().tolist()}"
        self._file.write(f"{timestamp}, {data[1:-1]}\n")

    @override
    def stop(self) -> None:
        self._file.close()
        self._file = None
