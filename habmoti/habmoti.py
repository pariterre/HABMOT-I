import logging
import queue
import time
import threading

from .data.frame_data import FrameData
from .analyses.analyzer import Analyzer, EmptyAnalyzer
from .kinematics.body_kinematics_device import BodyKinematicsDevice
from .viewers.viewer import Viewer

_logger = logging.getLogger(__name__)


class Habmoti:
    def __init__(
        self,
        body_kinematics_device: BodyKinematicsDevice,
        analyzer: Analyzer | None = None,
        viewer: Viewer | None = None,
    ):
        self._body_kinematics_device = body_kinematics_device
        self._analyzer = analyzer if analyzer is not None else EmptyAnalyzer()
        self._viewer = viewer

        self._to_analyzer_queue = queue.Queue()
        self._to_viewer_queue = queue.Queue()

        self._stop_event = threading.Event()
        self._capture_is_over_event = threading.Event()

    def start(self) -> None:
        """
        Start the pipeline threads.
        """

        self._stop_event.clear()
        self._capture_is_over_event.clear()

        # Start the pipeline and their associated threads
        self._body_kinematics_device.start()
        self.threads = [threading.Thread(target=self._capture_loop, daemon=False)]
        if self._has_analyzer:
            self._analyzer.start(device=self._body_kinematics_device)
            self.threads.append(threading.Thread(target=self._analysis_loop, daemon=False))
        if self._has_viewer:
            self.threads.append(threading.Thread(target=self._run_view_loop, daemon=False))

        for t in self.threads:
            t.start()

    def stop(self):
        """
        Stop the pipeline threads.
        """
        self._stop_event.set()

        for t in self.threads:
            t.join()

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
                    if self._has_viewer:
                        self._to_viewer_queue.put(frame_data)

                except Exception as e:
                    _logger.error("Capture error:", exc_info=e)

            self._body_kinematics_device.stop()

        finally:
            self._capture_is_over_event.set()

    @property
    def _has_analyzer(self) -> bool:
        return self._analyzer is not None

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

    @property
    def _has_viewer(self) -> bool:
        return self._viewer is not None

    def _run_view_loop(self) -> None:
        if self._viewer is None:
            return

        self._viewer.start(device=self._body_kinematics_device)
        try:
            self._view_loop()
        except Exception as e:
            _logger.error("Viewer loop error:", exc_info=e)

    def _view_loop(self) -> None:
        """
        View loop: continuously get frames from the queue and display them.
        When the capture is over, the loop continues until the queue is empty then stops.
        """
        while not self._capture_is_over_event.is_set() or not self._to_viewer_queue.empty():
            try:
                frame: FrameData = self._to_viewer_queue.get(timeout=0.5)
                if self._viewer is not None:
                    self._viewer.update(frame)
            except queue.Empty:
                continue
