from time import time

from habmoti import Habmoti, ZedDevice


def main():
    device = ZedDevice()
    habmoti = Habmoti(kinematics_device=device, save_path="data")
    habmoti.start()

    time.sleep(10)

    habmoti.stop()


if __name__ == "__main__":
    main()
