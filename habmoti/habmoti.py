import logging
import queue
import time
import threading

from .analyzers.analyzer import Analyzer
from .data.frame_data import FrameData
from .devices.device import Device

_logger = logging.getLogger(__name__)


class Habmoti:
    def __init__(
        self,
        device: Device | None = None,
        analyzer: Analyzer | None = None,
    ):
        self._device = device
        self._analyzer = analyzer

        self._is_initialized = False
        self._is_trial_started = False

        self._threads: list[threading.Thread] = []
        self._analyzer_ready_event = threading.Event()
        self._capture_has_ended_event = threading.Event()
        self._stop_request_event = threading.Event()

        self._to_analyzer_queue = queue.Queue()

    @property
    def is_initialized(self) -> bool:
        return self._is_initialized

    def initialize(self) -> None:
        """
        Initialize the pipeline threads.
        """
        if self._is_initialized:
            raise RuntimeError(
                "Pipeline is already initialized. Please stop the pipeline before initializing it again."
            )

        if self._device is None:
            raise ValueError("No device set. Please set a device before initializing the pipeline.")

        self._analyzer_ready_event.clear()
        self._capture_has_ended_event.clear()
        self._stop_request_event.clear()

        self._threads = [
            threading.Thread(target=self._run_capture_loop, daemon=False),
            threading.Thread(target=self._run_analysis_loop, daemon=False),
        ]
        for t in self._threads:
            t.start()

        self._is_initialized = True

    def exec(self) -> None:
        """
        Execute the pipeline. This method blocks until the pipeline is terminated.
        """
        if not self._is_initialized:
            raise RuntimeError("Pipeline is not initialized. Please initialize the pipeline before executing it.")

        for t in self._threads:
            t.join()

    def start_trial(self):
        """
        Start a trial
        """
        self._analyzer.start_trial()
        self._is_trial_started = True

    def stop_trial(self):
        """
        Stop a trial
        """
        self._analyzer.stop_trial()
        self._is_trial_started = False

    def terminate(self) -> None:
        """
        Terminate the pipeline threads.
        """
        if not self._is_initialized:
            return

        if self._stop_request_event.is_set():
            return

        if self._is_trial_started:
            self.stop_trial()

        self._stop_request_event.set()
        self._threads = []

    @property
    def device(self) -> Device | None:
        return self._device

    @device.setter
    def device(self, device: Device) -> None:
        if self._is_initialized:
            raise RuntimeError(
                "Cannot change device while the pipeline is running. Please stop the pipeline before changing the device."
            )
        if self._analyzer is not None:
            raise RuntimeError(
                "Cannot change device while an analyzer is set. Please remove the analyzer or stop the pipeline before changing the device."
            )
        self._device = device

    @property
    def analyzer(self) -> Analyzer:
        return self._analyzer

    @analyzer.setter
    def analyzer(self, analyzer: Analyzer | None) -> None:
        if self._is_initialized:
            raise RuntimeError(
                "Cannot change analyzer while the pipeline is running. Please stop the pipeline before changing the analyzer."
            )
        self._analyzer = analyzer

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
            self._wait_for_analyzer()
            self._capture_loop()
        except Exception as e:
            _logger.error("Capture loop error:", exc_info=e)
        finally:
            self._capture_has_ended_event.set()

        try:
            self._device.stop()
        except Exception as e:
            _logger.error("Failed to stop device:", exc_info=e)

    def _wait_for_analyzer(self) -> None:
        """
        Wait for the analyzer to be ready
        """
        while not self._analyzer_ready_event.is_set():
            # If Haboti is stopped while waiting for initialization, stop waiting
            if not self._capture_has_ended_event.is_set() and not self._stop_request_event.is_set():
                return
            time.sleep(0.1)

    def _capture_loop(self) -> None:
        """
        Capture loop: continuously capture data from the device and put it in the queue.
        """

        analyses = {}
        while not self._capture_has_ended_event.is_set() and not self._stop_request_event.is_set():
            try:
                frame_data = self._device.get_current_frame_data()

                if self._has_analyzer:
                    self._to_analyzer_queue.put({"frame_data": frame_data, "analyses": analyses})

                # Rest the CPU a bit to avoid a busy loop when the device is fast (e.g., mocked device or csv reader)
                time.sleep(0.001)
            except Exception as e:
                _logger.error("Capture error:", exc_info=e)

        # Wait until the analyzer queue is empty before setting started to False
        self._to_analyzer_queue.join()
        self._is_initialized = False

    @property
    def _has_analyzer(self) -> bool:
        return self._analyzer is not None

    def _run_analysis_loop(self) -> None:
        if self._analyzer is None:
            self._analyzer_ready_event.set()
            return

        try:
            self._analyzer.initialize(habmoti=self)
            self._analyzer_ready_event.set()
            self._analysis_loop()
        except Exception as e:
            _logger.error("Analyzer failed, stopping data capture. Stack trace:\n", exc_info=e)
            self.terminate()
        finally:
            self._analyzer.dispose()

    def _analysis_loop(self) -> None:
        """
        Analysis loop: continuously get frames from the queue and analyze them.
        When the capture is over, the loop continues until the queue is empty then stops.
        """
        while not self._capture_has_ended_event.is_set() or not self._to_analyzer_queue.empty():
            is_empty = False
            try:
                data: dict = self._to_analyzer_queue.get(timeout=0.5)
                frame_data: FrameData | None = data.get("frame_data")
                analyses: dict = data.get("analyses", {})
                if frame_data is None:
                    continue
                self._analyzer.perform(frame_data)

            except queue.Empty:
                is_empty = True
                continue

            finally:
                if not is_empty:
                    self._to_analyzer_queue.task_done()
