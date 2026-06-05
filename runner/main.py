import os
from pathlib import Path
from time import time

from habmoti import Habmoti, MockedZedDevice


def main():
    device = MockedZedDevice(configuration_filepath=Path(os.getenv("HABMOTI_CONFIG_PATH")))
    habmoti = Habmoti(kinematics_device=device, save_path=Path(os.getenv("HABMOTI_SAVE_PATH")))

    habmoti.start()
    time.sleep(10)
    habmoti.stop()


if __name__ == "__main__":
    main()
