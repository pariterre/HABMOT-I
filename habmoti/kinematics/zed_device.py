from typing import TYPE_CHECKING, override

from .kinematics_device import KinematicsDevice

if TYPE_CHECKING:
    import pyzed.sl as sl  # type: ignore


class ZedDevice(KinematicsDevice):
    def __init__(self, zed: "sl.Camera"):
        self._load_module()

        self.zed = zed

    def _load_module(self):
        try:
            import pyzed.sl as sl  # type: ignore
        except ImportError:
            raise ImportError(
                "The pyzed.sl module is required to use the ZedDevice. Please install it before using this class."
            )

        self._sl = sl

    @override
    def _forward_kinematics(self, joint_angles):
        # Implement the forward kinematics for the Zed device here
        self._sl
