import logging
import queue
import time
import threading

from .analyzers.analyzer import Analyzer
from .controllers.controller import Controller
from .data.frame_data import FrameData
from .devices.device import Device

_logger = logging.getLogger(__name__)


class Habmoti:
    def __init__(
        self,
        device: Device,
        analyzer: Analyzer | None = None,
        controller: Controller | None = None,
    ):
        self._device = device
        self._analyzer = analyzer
        self._controller = controller

        self._to_analyzer_queue = queue.Queue()
        self._to_controller_queue = queue.Queue()

        self._stop_event = threading.Event()
        self._capture_is_over_event = threading.Event()

    def start(self, blocking: bool = True) -> None:
        """
        Start the pipeline threads.
        """

        self._stop_event.clear()
        self._capture_is_over_event.clear()

        # Start the pipeline and their associated threads
        self._device.start()
        self.threads = [threading.Thread(target=self._capture_loop, daemon=False)]
        if self._has_analyzer:
            self.threads.append(threading.Thread(target=self._run_analysis_loop, daemon=False))
        if self._has_controller:
            self.threads.append(threading.Thread(target=self._run_controller_loop, daemon=False))

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
    def device(self) -> Device:
        return self._device

    @property
    def analyzer(self) -> Analyzer:
        return self._analyzer

    @property
    def controller(self) -> Controller:
        return self._controller

    def _capture_loop(self) -> None:
        """
        Capture loop: continuously capture data from the device and put it in the queue.
        """
        try:
            while not self._stop_event.is_set():
                try:
                    frame_data = self._device.get_current_frame_data()

                    if self._has_analyzer:
                        self._to_analyzer_queue.put(frame_data)
                    if self._has_controller:
                        self._to_controller_queue.put(frame_data)

                    # Sleep a bit to avoid overwhelming the queues if the device is very fast
                    time.sleep(0.001)

                except Exception as e:
                    _logger.error("Capture error:", exc_info=e)

            self._device.stop()

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
                frame: FrameData | None = self._to_analyzer_queue.get(timeout=0.5)
                if frame is None:
                    continue
                self._analyzer.perform(frame)
            except queue.Empty:
                continue

    @property
    def _has_controller(self) -> bool:
        return self._controller is not None

    def _run_controller_loop(self) -> None:
        if self._controller is None:
            return

        try:
            self._controller.start(habmoti=self)
            self._controller_loop()
        except Exception as e:
            _logger.error("Controller loop error:", exc_info=e)

    def _controller_loop(self) -> None:
        """
        Controller loop: continuously get frames from the queue and perform control actions.
        When the capture is over, the loop continues until the queue is empty then stops.
        """
        while not self._capture_is_over_event.is_set() or not self._to_controller_queue.empty():
            try:
                frame: FrameData | None = self._to_controller_queue.get(timeout=0.5)
                self._controller.perform(frame)
            except queue.Empty:
                continue
