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

        self._analyzers_ready_event = threading.Event()
        self._controllers_ready_event = threading.Event()
        self._stop_capture_request_event = threading.Event()
        self._capture_is_over_event = threading.Event()

    def start(self, blocking: bool = True) -> None:
        """
        Start the pipeline threads.
        """

        self._analyzers_ready_event.clear()
        self._controllers_ready_event.clear()
        self._stop_capture_request_event.clear()
        self._capture_is_over_event.clear()

        # Start the pipeline and their associated threads
        self.threads = [
            threading.Thread(target=self._run_capture_loop, daemon=False), 
            threading.Thread(target=self._run_analysis_loop, daemon=False), 
            threading.Thread(target=self._run_controller_loop, daemon=False)
        ]

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
        self._stop_capture_request_event.set()

    @property
    def device(self) -> Device:
        return self._device

    @property
    def analyzer(self) -> Analyzer:
        return self._analyzer

    @property
    def controller(self) -> Controller:
        return self._controller

    @property
    def is_capturing_data(self) -> bool:
        return not self._capture_is_over_event.is_set() and not self._stop_capture_request_event.is_set()

    @property
    def _are_all_threads_ready(self) -> bool:
        return self._analyzers_ready_event.is_set() and self._controllers_ready_event.is_set()

    def _run_capture_loop(self) -> None:
        """
        Prepare the device for capture, then continuously capture data from the device and put it in the queue until stopped.
        """
        try: 
            _logger.warning(
                "WARNING: Starting the device inside a sub-thread may cause issues. "
                "When this modification is tested and confirmed with a real device, you can remove this warning."
            )
            self._device.start()
            self._wait_for_capture_to_be_ready_to_start()
            self._capture_loop()
        except Exception as e:
            _logger.error("Capture loop error:", exc_info=e)
        finally:
            self._capture_is_over_event.set()

        try:
            self._device.stop()
        except Exception as e:
            _logger.error("Failed to stop device:", exc_info=e)

    def _wait_for_capture_to_be_ready_to_start(self) -> None:
        """
        Wait for the analyzers and controllers to be ready before starting the capture loop.
        """
        while self.is_capturing_data and not self._are_all_threads_ready:
            time.sleep(0.1)

    def _capture_loop(self) -> None:
        """
        Capture loop: continuously capture data from the device and put it in the queue.
        """

        analyses = {}
        while self.is_capturing_data:
            try:
                frame_data = self._device.get_current_frame_data()

                if self._has_analyzer:
                    self._to_analyzer_queue.put({"frame_data": frame_data, "analyses": analyses})
                if self._has_controller:
                    self._to_controller_queue.put({"frame_data": frame_data, "analyses": analyses})

                # Rest the CPU a bit to avoid a busy loop when the device is fast (e.g., mocked device or csv reader)
                time.sleep(0.001)
            except Exception as e:
                _logger.error("Capture error:", exc_info=e)

    @property
    def _has_analyzer(self) -> bool:
        return self._analyzer is not None

    def _run_analysis_loop(self) -> None:
        if self._analyzer is None:
            self._analyzers_ready_event.set()
            return

        try:
            self._analyzer.start(habmoti=self)
            self._analyzers_ready_event.set()
            self._analysis_loop()
        except Exception as e:
            _logger.error("Stopping data capture as analyzer failed:", exc_info=e)
            self.stop()
            return

    def _analysis_loop(self) -> None:
        """
        Analysis loop: continuously get frames from the queue and analyze them.
        When the capture is over, the loop continues until the queue is empty then stops.
        """
        while not self._capture_is_over_event.is_set() or not self._to_analyzer_queue.empty():
            try:
                data: dict = self._to_analyzer_queue.get(timeout=0.5)
                frame_data: FrameData | None = data.get("frame_data")
                analyses: dict = data.get("analyses", {})
                if frame_data is None:
                    continue
                self._analyzer.perform(frame_data)
            except queue.Empty:
                continue

    @property
    def _has_controller(self) -> bool:
        return self._controller is not None

    def _run_controller_loop(self) -> None:
        if self._controller is None:
            self._controllers_ready_event.set()
            return

        try:
            self._controller.start(habmoti=self)
            self._controllers_ready_event.set()
            self._controller_loop()
        except Exception as e:
            _logger.error("Stopping data capture as controller failed:", exc_info=e)
            self.stop()
            return

    def _controller_loop(self) -> None:
        """
        Controller loop: continuously get frames from the queue and perform control actions.
        When the capture is over, the loop continues until the queue is empty then stops.
        """
        while not self._capture_is_over_event.is_set() or not self._to_controller_queue.empty():
            try:
                data: dict = self._to_controller_queue.get(timeout=0.5)
                frame_data: FrameData | None = data.get("frame_data")
                analyses: dict = data.get("analyses", {})
                self._controller.perform(frame_data)
            except queue.Empty:
                continue
