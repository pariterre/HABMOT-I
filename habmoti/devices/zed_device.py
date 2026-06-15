import pathlib as Path
import time
from typing import TYPE_CHECKING, override

import numpy as np

from .device import Device
from ..data.body_kinematics import BodyModel18Joints, MultiBodyKinematics
from ..data.frame_data import FrameData

if TYPE_CHECKING:
    from ..habmoti import Habmoti
    from ..data.body_kinematics import BodyModel
    import pyzed.sl as sl  # type: ignore


class ZedDevice(Device):
    def __init__(self, configuration_filepath: Path):
        self._load_module()

        self._configuration_filepath = configuration_filepath
        self._fusion_configurations: list["sl._sl.FusionConfiguration"] = None
        self._senders: dict[str, "sl._sl.Camera"] = {}

        self._fusion: "sl._sl.Fusion" = None
        self._rt: "sl._sl.BodyTrackingFusionRuntimeParameters" = None
        self._bodies: "sl._sl.Bodies" = None

    @property
    @override
    def name(self) -> str:
        return "ZED Camera"

    @property
    @override
    def body_model(self) -> type[BodyModel]:
        return BodyModel18Joints

    @override
    def start(self, habmoti: Habmoti) -> None:
        self._initialize_cameras()
        self._initialize_body_tracking()

    @override
    def get_current_frame_data(self) -> FrameData | None:
        # Get the bodies for each camera
        for serial in self._senders:
            zed = self._senders[serial]
            if zed.grab() <= self._sl.ERROR_CODE.SUCCESS:
                zed.retrieve_bodies(self._bodies)

        # Fuse the bodies from all cameras
        if self._fusion.process() == self._sl.FUSION_ERROR_CODE.SUCCESS:
            self._fusion.retrieve_bodies(self._bodies, self._rt)

        return FrameData(
            timestamp=int(self._fusion.get_current_timestamp().data_ns / 1000 / 1000),
            body_kinematics=MultiBodyKinematics(
                body_model=self.body_model, values=[body.keypoint for body in self._bodies.body_list]
            ),
        )

    @override
    def stop(self) -> None:
        for serial in self._senders:
            zed = self._senders[serial]
            zed.close()

        self._fusion_configurations = None
        self._senders = {}

        self._fusion = None
        self._rt = None
        self._bodies = None

    def _load_module(self):
        try:
            import pyzed.sl as sl  # type: ignore
        except ImportError:
            raise ImportError(
                "The pyzed.sl module is required to use the ZedDevice. Please install it before using this class."
            )

        self._sl = sl

    @property
    def camera_count(self) -> int:
        return len(self._senders)

    def _initialize_cameras(self):
        self._fusion_configurations = self._sl.read_fusion_configuration_file(
            str(self._configuration_filepath),
            self._sl.COORDINATE_SYSTEM.RIGHT_HANDED_Y_UP,
            self._sl.UNIT.METER,
        )
        if len(self._fusion_configurations) <= 0:
            raise ValueError(f"Invalid configuration file: {self._configuration_filepath}")

        # common parameters
        init_params = self._sl.InitParameters()
        init_params.coordinate_system = self._sl.COORDINATE_SYSTEM.RIGHT_HANDED_Y_UP
        init_params.coordinate_units = self._sl.UNIT.METER
        init_params.depth_mode = self._sl.DEPTH_MODE.NEURAL
        init_params.camera_resolution = self._sl.RESOLUTION.HD1200

        communication_parameters = self._sl.CommunicationParameters()
        communication_parameters.set_for_shared_memory()

        positional_tracking_parameters = self._sl.PositionalTrackingParameters()
        positional_tracking_parameters.set_as_static = True

        body_tracking_parameters = self._sl.BodyTrackingParameters()
        body_tracking_parameters.detection_model = self._sl.BODY_TRACKING_MODEL.HUMAN_BODY_ACCURATE
        if self.body_model == BodyModel18Joints:
            body_tracking_parameters.body_format = self._sl.BODY_FORMAT.BODY_18
        else:
            raise NotImplementedError(f"Unsupported joint center type: {self.body_model}")
        body_tracking_parameters.enable_body_fitting = False
        body_tracking_parameters.enable_tracking = False

        for conf in self._fusion_configurations:
            print("Try to open ZED", conf.serial_number)
            init_params.input = self._sl.InputType()

            # network cameras are already running, or so they should
            if conf.communication_parameters.comm_type == self._sl.COMM_TYPE.LOCAL_NETWORK:
                raise NotImplementedError("Network cameras are not supported yet.")
            else:
                init_params.input = conf.input_type

                self._senders[conf.serial_number] = self._sl.Camera()

                init_params.set_from_serial_number(conf.serial_number)
                status = self._senders[conf.serial_number].open(init_params)
                if status > self._sl.ERROR_CODE.SUCCESS:
                    raise RuntimeError("Error opening camera", conf.serial_number)

                status = self._senders[conf.serial_number].enable_positional_tracking(positional_tracking_parameters)
                if status > self._sl.ERROR_CODE.SUCCESS:
                    raise RuntimeError(
                        "Error enabling the positional tracking of camera",
                        conf.serial_number,
                    )

                status = self._senders[conf.serial_number].enable_body_tracking(body_tracking_parameters)
                if status > self._sl.ERROR_CODE.SUCCESS:
                    raise RuntimeError("Error enabling the body tracking of camera", conf.serial_number)

                self._senders[conf.serial_number].start_publishing(communication_parameters)

            print("Camera", conf.serial_number, "is open")

        if self.camera_count < 1:
            raise RuntimeError("No camera opened. Please check the configuration file and the cameras.")

    def _initialize_body_tracking(self):
        init_fusion_parameters = self._sl.InitFusionParameters()
        init_fusion_parameters.coordinate_system = self._sl.COORDINATE_SYSTEM.RIGHT_HANDED_Y_UP
        init_fusion_parameters.coordinate_units = self._sl.UNIT.METER
        init_fusion_parameters.output_performance_metrics = False
        init_fusion_parameters.verbose = True

        communication_parameters = self._sl.CommunicationParameters()
        self._fusion = self._sl.Fusion()
        camera_identifiers = []

        self._fusion.init(init_fusion_parameters)

        bodies = self._sl.Bodies()
        for serial in self._senders:
            zed = self._senders[serial]
            if zed.grab() <= self._sl.ERROR_CODE.SUCCESS:
                zed.retrieve_bodies(bodies)

        for i in range(0, len(self._fusion_configurations)):
            conf = self._fusion_configurations[i]
            uuid = self._sl.CameraIdentifier()
            uuid.serial_number = conf.serial_number
            print(
                "Subscribing to",
                conf.serial_number,
                conf.communication_parameters.comm_type,
            )

            status = self._fusion.subscribe(uuid, conf.communication_parameters, conf.pose)
            if status != self._sl.FUSION_ERROR_CODE.SUCCESS:
                print("Unable to subscribe to", uuid.serial_number, status)
            else:
                camera_identifiers.append(uuid)
                print("Subscribed.")

        if len(camera_identifiers) <= 0:
            raise RuntimeError(
                "No camera subscribed to the fusion. Please check the configuration file and the cameras."
            )

        body_tracking_fusion_params = self._sl.BodyTrackingFusionParameters()
        body_tracking_fusion_params.enable_tracking = True
        body_tracking_fusion_params.enable_body_fitting = False

        self._fusion.enable_body_tracking(body_tracking_fusion_params)

        self._rt = self._sl.BodyTrackingFusionRuntimeParameters()
        self._rt.skeleton_minimum_allowed_keypoints = 7
        self._bodies = self._sl.Bodies()


class ZedMockDevice(ZedDevice):
    def __init__(
        self,
        target_fps: int = 60,
        max_fps_lag_ms: int = 0,
        **kwargs,
    ):
        """
        A mocked version of the ZedDevice that generates random body kinematics data. It is used for testing purposes.
        Args:
            target_fps: The target fps of the device.
            max_fps_lag_ms: The maximum lag in ms to add to the capture time to simulate fps variability. Set to 0 to have a fixed fps.
        """

        super().__init__(**kwargs)

        import time

        self._dt = 1 / target_fps
        self._max_fps_lag = max_fps_lag_ms / 1000.0
        self._previous_capture_time = time.time()

    @property
    @override
    def name(self) -> str:
        return "ZED (Mock) Camera"

    @override
    def _load_module(self):
        self._sl = self
        self.coordinate_system = None
        self.unit = None

    @override
    def get_current_frame_data(self) -> FrameData | None:
        # Make sure data are not feed over the maximum fps of the device
        lag_dt = 0.0
        if self._max_fps_lag > 0:
            import random

            lag_dt = random.uniform(0.0, self._max_fps_lag)

        current_time = time.time()
        if current_time - self._previous_capture_time < self._dt:
            time.sleep(self._dt - (current_time - self._previous_capture_time) + lag_dt)
        self._previous_capture_time = time.time()

        return super().get_current_frame_data()

    # Mocker of the sl module
    COORDINATE_SYSTEM = type("COORDINATE_SYSTEM", (), {"RIGHT_HANDED_Y_UP": 0})
    UNIT = type("UNIT", (), {"METER": 0})
    DEPTH_MODE = type("DEPTH_MODE", (), {"NEURAL": 0})
    RESOLUTION = type("RESOLUTION", (), {"HD1200": 0})
    BODY_TRACKING_MODEL = type("BODY_TRACKING_MODEL", (), {"HUMAN_BODY_ACCURATE": 0})
    BODY_FORMAT = type("BODY_FORMAT", (), {"BODY_18": 0})
    COMM_TYPE = type("COMM_TYPE", (), {"LOCAL_NETWORK": 0, "INTRA_PROCESS": 1})
    ERROR_CODE = type("ERROR_CODE", (), {"SUCCESS": 0})
    FUSION_ERROR_CODE = type("FUSION_ERROR_CODE", (), {"SUCCESS": 0})

    def read_fusion_configuration_file(self, config_path: str, *args, **kwargs):
        import json

        with open(config_path, "r") as f:
            conf = json.load(f)

        confs = []
        for key in conf.keys():
            fusion = self.FusionConfiguration()
            fusion.serial_number = key
            confs.append(fusion)
        return confs

    @staticmethod
    def InitParameters():
        return type(
            "InitParameters",
            (),
            {
                "coordinate_system": None,
                "coordinate_units": None,
                "depth_mode": None,
                "camera_resolution": None,
                "input": None,
                "set_from_serial_number": lambda _, __: None,
            },
        )()

    @staticmethod
    def FusionConfiguration():
        return type(
            "FusionConfiguration",
            (),
            {
                "serial_number": None,
                "communication_parameters": ZedMockDevice.CommunicationParameters(),
                "input_type": ZedMockDevice.InputType(),
                "pose": None,
            },
        )()

    @staticmethod
    def CommunicationParameters():
        return type(
            "CommunicationParameters",
            (),
            {
                "set_for_shared_memory": lambda _: None,
                "comm_type": ZedMockDevice.COMM_TYPE.INTRA_PROCESS,
            },
        )()

    @staticmethod
    def PositionalTrackingParameters():
        return type("PositionalTrackingParameters", (), {"set_as_static": None})()

    @staticmethod
    def BodyTrackingParameters():
        return type(
            "BodyTrackingParameters",
            (),
            {
                "detection_model": None,
                "body_format": None,
                "enable_body_fitting": None,
                "enable_tracking": None,
            },
        )()

    @staticmethod
    def InputType():
        return type("InputType", (), {})()

    @staticmethod
    def Camera():
        return type(
            "Camera",
            (),
            {
                "open": lambda _, __: ZedMockDevice.ERROR_CODE.SUCCESS,
                "enable_positional_tracking": lambda _, __: ZedMockDevice.ERROR_CODE.SUCCESS,
                "enable_body_tracking": ZedMockDevice._setup_body_tracking,
                "start_publishing": lambda _, __: None,
                "grab": lambda _: ZedMockDevice.ERROR_CODE.SUCCESS,
                "retrieve_bodies": ZedMockDevice._retrieve_bodies,
                "close": lambda _: None,
                "_body_format": None,
                "_camera_index_in_bodylist": None,
                "_biorbd_model": None,
                "_current_retrieved_body_frame": 0,
            },
        )()

    @staticmethod
    def _setup_body_tracking(self, parameters):
        self._body_format = parameters.body_format
        return ZedMockDevice.ERROR_CODE.SUCCESS

    @staticmethod
    def _retrieve_bodies(self, bodies):
        # If this is the first time we add this camera to the body list, remember the index of which
        if self._camera_index_in_bodylist is None:
            self._camera_index_in_bodylist = len(bodies.body_list)
        while len(bodies.body_list) <= self._camera_index_in_bodylist:
            bodies.body_list.append(None)

        import biorbd

        # Add new data
        if self._body_format == ZedMockDevice.BODY_FORMAT.BODY_18:
            if self._biorbd_model is None:
                try:
                    import biorbd
                except ImportError:
                    raise ImportError(
                        "The biorbd module is required to use the ZedMockDevice. You can install it with conda install -c conda-forge biorbd",
                    )
                self._biorbd_model = biorbd.Biorbd(str(Path.Path(__file__).parent / "pyomecaman_18_joints.bioMod"))

            q = np.zeros(self._biorbd_model.nb_q)
            # Place the body in front of the camera
            q[0:6] = [0.0, 4.0, 0.0, 0.0, 0.0, np.pi]
            # Simulate a movement of the right shoulder
            q[9] = np.linspace(0, np.pi, 100)[self._current_retrieved_body_frame % 100]
            self._current_retrieved_body_frame += 1
            markers = self._biorbd_model.markers(q)

            keypoints = np.ndarray((18, 3)) * np.nan
            for marker in markers:
                index = BodyModel18Joints.from_name(marker.name).value
                keypoints[index, :] = marker.forward_kinematics()
            data = type("Body", (), {"keypoint": keypoints})()

        else:
            raise NotImplementedError(f"Unsupported body format: {self._body_format}")
        bodies.body_list[self._camera_index_in_bodylist] = data

        return ZedMockDevice.ERROR_CODE.SUCCESS

    @staticmethod
    def InitFusionParameters():
        return type(
            "InitFusionParameters",
            (),
            {
                "coordinate_system": None,
                "coordinate_units": None,
                "output_performance_metrics": None,
                "verbose": None,
            },
        )()

    @staticmethod
    def Fusion():
        return type(
            "Fusion",
            (),
            {
                "init": lambda _, __: None,
                "subscribe": lambda _, __, ___, ____: ZedMockDevice.ERROR_CODE.SUCCESS,
                "enable_body_tracking": lambda _, __: None,
                "process": lambda _: ZedMockDevice.FUSION_ERROR_CODE.SUCCESS,
                "retrieve_bodies": lambda _, bodies, __: None,
                "get_current_timestamp": lambda _: type("Timestamp", (), {"data_ns": int(time.time() * 1000 * 1000)})(),
            },
        )()

    @staticmethod
    def Body():
        return type("Body", (), {"keypoint": np.ndarray((18, 3)) * np.nan})()

    @staticmethod
    def Bodies():
        return type(
            "Bodies",
            (),
            {"is_tracked": lambda _, __: True, "body_list": []},
        )()

    @staticmethod
    def CameraIdentifier():
        return type("CameraIdentifier", (), {"serial_number": None})()

    @staticmethod
    def BodyTrackingFusionParameters():
        return type(
            "BodyTrackingFusionParameters",
            (),
            {"enable_tracking": None, "enable_body_fitting": None},
        )()

    @staticmethod
    def BodyTrackingFusionRuntimeParameters():
        return type(
            "BodyTrackingFusionRuntimeParameters",
            (),
            {"enable_tracking": None, "enable_body_fitting": None},
        )()
