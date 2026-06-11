from enum import Enum, auto


class ControlEvent(Enum):
    START_RECORDING = auto()
    STOP_RECORDING = auto()
