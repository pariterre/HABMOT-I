import os
from pathlib import Path
from time import sleep

from habmoti import Habmoti, ZedDevice, AnalyzerList, ToConsoleAnalyzer, ToCsvAnalyzer, JointCenter18Joints


def main():
    device = ZedDevice(
        configuration_filepath=Path(os.getenv("HABMOTI_CONFIG_PATH")),  # target_fps=10, max_fps_lag_ms=0
    )
    save_path = Path(os.getenv("HABMOTI_SAVE_PATH"))
    analyzer = AnalyzerList(
        analyzers=[
            ToConsoleAnalyzer(joint_center=JointCenter18Joints.LEFT_SHOULDER),
            ToCsvAnalyzer(filepath=save_path),
        ]
    )

    habmoti = Habmoti(body_kinematics_device=device, analyzer=analyzer)

    habmoti.start()
    sleep(10)
    habmoti.stop()


if __name__ == "__main__":
    main()
