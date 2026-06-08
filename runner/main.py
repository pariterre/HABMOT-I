import json
import os
from pathlib import Path
from time import sleep

from habmoti import Habmoti, ZedDevice, MockedZedDevice, AnalyzerList, ToConsoleAnalyzer, ToCsvAnalyzer, OGLViewer


def main():
    device_type = os.getenv("HABMOTI_DEVICE_TYPE")
    if device_type is None:
        raise ValueError("Environment variable 'HABMOTI_DEVICE_TYPE' is not set")

    if device_type == "mocked_zed":
        zed_parameters = json.loads(os.getenv("HABMOTI_ZED_PARAMETERS", "{}"))
        mock_parameters = json.loads(os.getenv("HABMOTI_MOCKED_ZED_PARAMETERS", "{}"))
        device = MockedZedDevice(**mock_parameters | zed_parameters)
    elif device_type == "zed":
        parameters = json.loads(os.getenv("HABMOTI_ZED_PARAMETERS", "{}"))
        device = ZedDevice(**parameters)
    else:
        raise NotImplementedError(f"Unsupported device type: {device_type}")

    analyzers = []
    for analyzer in json.loads(os.getenv("HABMOTI_ANALYZERS", "[]")):
        if analyzer == "to_console":
            parameters = json.loads(os.getenv("HABMOTI_TO_CONSOLE_ANALYZER_PARAMETERS", "{}"))
            if "joint_center" not in parameters:
                raise ValueError(
                    "Missing 'joint_center' parameter in the HABMOTI_TO_CONSOLE_ANALYZER_PARAMETERS environment variable"
                )
            analyzers.append(
                ToConsoleAnalyzer(joint_center=device.joint_center_type.from_name(parameters["joint_center"]))
            )
        elif analyzer == "to_csv":
            parameters = json.loads(os.getenv("HABMOTI_TO_CSV_ANALYZER_PARAMETERS", "{}"))
            if "filepath" not in parameters:
                raise ValueError(
                    "Missing 'filepath' parameter in the HABMOTI_TO_CSV_ANALYZER_PARAMETERS environment variable"
                )
            analyzers.append(ToCsvAnalyzer(filepath=Path(parameters["filepath"])))
        else:
            raise NotImplementedError(f"Unsupported analyzer type: {analyzer}")

    analyzers = AnalyzerList(analyzers=analyzers)
    viewer = OGLViewer()
    habmoti = Habmoti(
        body_kinematics_device=device,
        # analyzer=analyzers,
        viewer=viewer,
    )

    habmoti.start()
    sleep(10)
    habmoti.stop()


if __name__ == "__main__":
    main()
