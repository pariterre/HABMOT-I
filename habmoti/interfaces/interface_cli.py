from pathlib import Path

from ..devices.zed_device import ZedDevice, MockedZedDevice
from ..devices.csv_reader_device import CsvReaderDevice
from ..habmoti import Habmoti


class InterfaceCli:
    def __init__(self):
        self._habmoti = Habmoti()

    def exec(self) -> None:
        print("Welcome to the HABMOT-I CLI!")
        print("Type 'help' for a list of commands, or 'quit' to quit.")
        while True:
            try:
                command = input("[Habmoti]> ").strip().lower().split()
            except:
                print("Error reading input. Please try again.")
                continue

            if command[0] == "quit":
                print("Exiting the CLI. Goodbye!")
                break

            elif command[0] == "device":
                self._handle_device_command(command)

            elif command[0] == "analyzer":
                self._handle_analyzer_command(command)

            elif command[0] == "start":
                self._habmoti.start()
                print("HABMOT-I started.")
            elif command[0] == "help":
                print("  Available commands:")
                print("    help - Show this help message")
                print("    device - Manage devices (type 'device help' for more information)")
                print("    analyzer - Manage analyzers (type 'analyzer help' for more information)")
                print("    start - Start the HABMOT-I system")
                print("    quit - Exit the CLI")
            else:
                print(f"  Unknown command: {command[0]}. Type 'help' for a list of commands.")

    def _handle_device_command(self, command: list[str]):
        if len(command) < 2:
            print("  Specify a subcommand for 'device' ('list' for available devices), leave empty to go back: ")
            while True:
                subcommand = input("[Habmoti / device]> ").strip().lower().split()
                if not subcommand:
                    return
                else:
                    self._handle_device_command([command[0], *subcommand])
        if command[1] == "help":
            self._handle_device_help_command()
        elif command[1] == "list":
            self._handle_device_list_command()
        elif command[1] == "connect":
            self._handle_device_connect_command(command)
        elif command[1] == "connected":
            print(f"  Connected device: {self._habmoti.device.name if self._habmoti.device is not None else 'None'}")
        else:
            print(f"  Unknown 'device' subcommand: '{command[1]}'. Type 'device help' for a list of subcommands.")

    def _handle_device_help_command(self):
        print("  Available 'device' subcommands:")
        print("    help - Show this help message")
        print("    list - List available devices")
        print(
            "    connect <device_name> - connect a device to the system. If <device_name> is not specified, you will be prompted to enter it."
        )
        print("    connected - Show the currently connected device")

    def _handle_device_list_command(self):
        print("  Available devices:")
        print("    zed - ZED camera")
        print("    zed_mocked - ZED (Mocked) camera")
        print("    csv_reader - CSV reader")

    def _handle_device_connect_command(self, command: list[str]):
        if self._habmoti.is_started:
            print(
                "  Cannot change device while Habmoti is started. Please stop the pipeline before changing the device."
            )
            return
        if self._habmoti.device is not None:
            response = input("  A device is already connected. Do you want to replace it? (y/N) ").strip().lower()
            if response != "y":
                return

        if len(command) < 3:
            print("  Specify the device to connect ('list' for available devices), leave empty to cancel: ")
            while True:
                device_name = input("[Habmoti / device connect]> ").strip().lower()
                if device_name == "":
                    return
                elif device_name == "list":
                    self._handle_device_list_command()
                else:
                    break
        else:
            device_name = command[2]

        try:
            if device_name == "zed" or device_name == "zed_mocked":
                self._handle_connect_zed_device_command(device_name)
            elif device_name == "csv_reader":
                self._handle_connect_csv_reader_device_command(command=command)
            else:
                print(f"  Unknown device: {device_name}. Type 'device list' for available devices.")
        except Exception as e:
            print(f"  Failed to connect device: {e}")

    def _handle_connect_zed_device_command(self, device_name: str):
        is_mock = device_name == "zed_mocked"
        config_path = input(
            "  A configuration file is required to use the ZED camera. If not done already, you can create one by using the ZED360 tool.\n"
            "  Path of the file [default=configuration.json]: "
        ).strip()
        if config_path == "":
            config_path = "configuration.json"

        if is_mock:
            target_fps = input("  Target FPS [default=30]: ").strip()
            if target_fps == "":
                target_fps = 30
            else:
                target_fps = int(target_fps)

            max_fps_lag_ms = input("  Max FPS lag in ms [default=0]: ").strip()
            if max_fps_lag_ms == "":
                max_fps_lag_ms = 0
            else:
                max_fps_lag_ms = int(max_fps_lag_ms)

            self._habmoti.device = MockedZedDevice(
                configuration_filepath=config_path, target_fps=target_fps, max_fps_lag_ms=max_fps_lag_ms
            )
        else:
            self._habmoti.device = ZedDevice(configuration_filepath=config_path)
        print(f"  ZED{' (Mocked)' if is_mock else ''} camera added.")

    def _handle_connect_csv_reader_device_command(self, command: list[str]):
        if len(command) < 4:
            filepath = input("  Path of the CSV file to read (leave empty to cancel): ").strip()
            if filepath == "":
                return
        else:
            filepath = command[3]

        self._habmoti.device = CsvReaderDevice(filepath=Path(filepath))
        print("  CSV reader added.")

    def _handle_analyzer_command(self, command: list[str]):
        if len(command) < 2:
            print("  Specify a subcommand for 'analyzer' ('list' for available analyzers), leave empty to go back: ")
            while True:
                subcommand = input("[Habmoti / analyzer]> ").strip().lower().split()
                if not subcommand:
                    return
                else:
                    self._handle_analyzer_command([command[0], *subcommand])
        if command[1] == "help":
            self._handle_analyzer_help_command()
        elif command[1] == "list":
            self._handle_analyzer_list_command()
        else:
            print(f"  Unknown 'analyzer' subcommand: '{command[1]}'. Type 'analyzer help' for a list of subcommands.")

    def _handle_analyzer_help_command(self):
        print("  Available 'analyzer' subcommands:")
        print("    help - Show this help message")
        print("    list - List available analyzers")

    def _handle_analyzer_list_command(self):
        print("  Available analyzers:")
        print("    (No analyzers available yet)")
