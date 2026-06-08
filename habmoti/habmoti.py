import logging
import queue
import time
import threading

from .data.frame_data import FrameData
from .analyses.analyzer import Analyzer
from .kinematics.body_kinematics_device import BodyKinematicsDevice

_logger = logging.getLogger(__name__)


class Habmoti:
    def __init__(
        self,
        body_kinematics_device: BodyKinematicsDevice,
        analyzer: Analyzer | None = None,
    ):
        self._body_kinematics_device = body_kinematics_device
        self._analyzer = analyzer

        self._to_analyzer_queue = queue.Queue()

        self._stop_event = threading.Event()
        self._capture_is_over_event = threading.Event()

    def start(self, blocking: bool = True) -> None:
        """
        Start the pipeline threads.
        """

        self._stop_event.clear()
        self._capture_is_over_event.clear()

        # Start the pipeline and their associated threads
        self._body_kinematics_device.start()
        self.threads = [threading.Thread(target=self._capture_loop, daemon=False)]
        if self._has_analyzer:
            self.threads.append(threading.Thread(target=self._run_analysis_loop, daemon=False))

        for t in self.threads:
            t.start()

        if blocking:
            self.join()

    def join(self):
        for t in self.threads:
            t.join()

    def stop(self):
        """
        Stop the pipeline threads.
        """
        if self._stop_event.is_set():
            return
        self._stop_event.set()

    @property
    def device(self) -> BodyKinematicsDevice:
        return self._body_kinematics_device

    @property
    def analyzer(self) -> Analyzer:
        return self._analyzer

    def _capture_loop(self) -> None:
        """
        Capture loop: continuously capture data from the device and put it in the queue.
        """
        try:
            while not self._stop_event.is_set():
                try:
                    frame_data = FrameData(
                        timestamp=int(time.time() * 1000),
                        body_kinematics=self._body_kinematics_device.get_current_body_kinematics(),
                    )

                    if self._has_analyzer:
                        self._to_analyzer_queue.put(frame_data)

                except Exception as e:
                    _logger.error("Capture error:", exc_info=e)

            self._body_kinematics_device.stop()

        finally:
            self._capture_is_over_event.set()

    @property
    def _has_analyzer(self) -> bool:
        return self._analyzer is not None

    def _run_analysis_loop(self) -> None:
        if self._analyzer is None:
            return

        try:
            self._analyzer.start(habmoti=self)
            self._analysis_loop()
        except Exception as e:
            _logger.error("Analyzer loop error:", exc_info=e)

    def _analysis_loop(self) -> None:
        """
        Analysis loop: continuously get frames from the queue and analyze them.
        When the capture is over, the loop continues until the queue is empty then stops.
        """
        while not self._capture_is_over_event.is_set() or not self._to_analyzer_queue.empty():
            try:
                frame: FrameData = self._to_analyzer_queue.get(timeout=0.5)
                self._analyzer.perform(frame)
            except queue.Empty:
                continue
