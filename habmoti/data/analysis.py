from enum import Enum
from typing import Any


class AnalysesType(Enum):
    pass


class Analysis:
    def __init__(self):
        self.current: dict[AnalysesType, Any] = {}
