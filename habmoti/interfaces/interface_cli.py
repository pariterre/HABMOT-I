from pathlib import Path

from ..analyzers.analyzer import AnalyzerList
from ..analyzers.writers.to_console_analyzer import ToConsoleAnalyzer
from ..analyzers.writers.to_csv_analyzer import ToCsvAnalyzer
from ..analyzers.viewers.to_matplotlib_analyzer import ToMatplotlibAnalyzer
from ..analyzers.viewers.to_ogl_analyzer import ToOglAnalyzer
from ..devices.device import Device
from ..devices.zed_device import ZedDevice, MockedZedDevice
from ..devices.csv_reader_device import CsvReaderDevice
from ..habmoti import Habmoti


class InterfaceCli:
    def __init__(self):
        self._habmoti = Habmoti(analyzer=AnalyzerList())

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
                self._handle_device_command(command[1:])

            elif command[0] == "analyzer":
                self._handle_analyzer_command(command[1:])

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
                print(
                    "  When navigating through subcommands, you can usually type 'help' for more information on the subcommands and also type"
                    "'list' to see available options. To go back to the previous menu, leave the input empty or type 'back'."
                )
            else:
                print(f"  Unknown command: {command[0]}. Type 'help' for a list of commands.")

    def _handle_device_command(self, command: list[str]):
        if not command:
            while True:
                subcommand = input("[Habmoti / device]> ").strip().lower().split()
                if not subcommand or subcommand[0] in ["back", ".."]:
                    return
                else:
                    self._handle_device_command(subcommand)

        if command[0] == "help":
            self._handle_device_help_command()
        elif command[0] in ["list", "ls"]:
            self._handle_device_list_command()
        elif command[0] == "connect":
            self._handle_device_connect_command(command[1:])
        elif command[0] == "connected":
            print(f"  Connected device: {self._habmoti.device.name if self._habmoti.device is not None else 'None'}")
        else:
            print(
                f"  Unknown 'device' subcommand: '{command[0]}'. Use the 'help' subcommand for a list of subcommands."
            )

    def _handle_device_help_command(self):
        print("  Available 'device' subcommands:")
        print("    help - Show this help message")
        print("    list,ls - List available devices")
        print(
            "    connect <device_name> - connect a device to the system. If <device_name> is not specified, you will be prompted to enter it."
        )
        print("    connected - Show the currently connected device")
        print("    back,.. - Go back to the previous menu")

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
            response = (
                input(
                    "  A device is already connected. Please note, this will remove the current analyzer. "
                    "Do you want to continue?  (y/N) "
                )
                .strip()
                .lower()
            )
            if response != "y":
                return

        if len(command) < 1:
            while True:
                subcommand = input("[Habmoti / device / connect]> ").strip().lower().split()
                if not subcommand or subcommand[0] in ["back", ".."]:
                    return
                else:
                    self._handle_device_connect_command(subcommand)
        device_name = command[0]

        try:
            if device_name in ["list", "ls", "help"]:
                self._handle_device_list_command()
            elif device_name == "zed" or device_name == "zed_mocked":
                self._handle_device_connect_zed_command(device_name)
            elif device_name == "csv_reader":
                self._handle_device_connect_csv_reader_command(command[1:])
            else:
                print(f"  Unknown device: {device_name}. Use the 'list' subcommand for available devices.")
        except Exception as e:
            print(f"  Failed to connect device: {e}")

    def _safe_device_connect(self, device: Device):
        self._habmoti.analyzer = None
        self._habmoti.device = device
        self._habmoti.analyzer = AnalyzerList()

    def _handle_device_connect_zed_command(self, device_name: str):
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

            self._safe_device_connect(
                device=MockedZedDevice(
                    configuration_filepath=config_path, target_fps=target_fps, max_fps_lag_ms=max_fps_lag_ms
                )
            )
        else:
            self._safe_device_connect(device=ZedDevice(configuration_filepath=config_path))
        print(f"  ZED{' (Mocked)' if is_mock else ''} camera added.")

    def _handle_device_connect_csv_reader_command(self, command: list[str]):
        if not command:
            filepath = input("  Path of the CSV file to read (leave empty to cancel): ").strip()
            if filepath == "":
                return
        else:
            filepath = command[0]

        self._safe_device_connect(device=CsvReaderDevice(filepath=Path(filepath)))
        print("  CSV reader added.")

    def _handle_analyzer_command(self, command: list[str]):
        if not command:
            while True:
                subcommand = input("[Habmoti / analyzer]> ").strip().lower().split()
                if not subcommand or subcommand[0] in ["back", ".."]:
                    return
                else:
                    self._handle_analyzer_command(subcommand)
        if command[0] == "help":
            self._handle_analyzer_help_command()
        elif command[0] in ["list", "ls"]:
            self._handle_analyzer_list_command()
        elif command[0] == "viewer":
            self._handle_analyzer_viewer_command(command[1:])
        elif command[0] == "writer":
            # TODO - RENDU ICI
            # TODO: Move ToConsole in writer instead of viewer
            self._handle_analyzer_writer_command(command[1:])
        else:
            print(
                f"  Unknown 'analyzer' subcommand: '{command[0]}'. Use the 'help' subcommand for a list of subcommands."
            )

    def _handle_analyzer_help_command(self):
        print("  Available 'analyzer' subcommands:")
        print("    help - Show this help message")
        print("    list,ls - List available analyzer types")
        print("    back,.. - Go back to the previous menu")

    def _handle_analyzer_list_command(self):
        print("  Available analyzer types:")
        print("    data")
        print("    viewer")
        print("    writer")

    def _handle_analyzer_viewer_command(self, command: list[str]):
        if not command:
            while True:
                subcommand = input("[Habmoti / analyzer / viewer]> ").strip().lower().split()
                if not subcommand or subcommand[0] in ["back", ".."]:
                    return
                else:
                    self._handle_analyzer_viewer_command(subcommand)

        if command[0] == "help":
            self._handle_analyzer_viewer_help_command()
        elif command[0] == "add":
            self._handle_analyzer_viewer_add_command(command[1:])
        elif command[0] == "added":
            self._handle_analyzer_viewer_added_command()
        elif command[0] == "remove":
            self._handle_analyzer_viewer_remove_command(command[1:])
        else:
            print(
                f"  Unknown 'viewer' subcommand: '{command[0]}'. Use the 'help' subcommand for a list of subcommands."
            )

    def _handle_analyzer_viewer_help_command(self):
        print("  Available 'viewer' subcommands:")
        print("    help - Show this help message")
        print(
            "    add <viewer_name> - Add a viewer analyzer to the system. If <viewer_name> is not specified, you will be prompted to enter it."
        )
        print("    added - Show the currently added analyzers")
        print(
            "    remove <analyzer_index> - Remove the analyzer with the specified index. You can see the indices by using the 'added' subcommand."
        )
        print("    back,.. - Go back to the previous menu")

    def _handle_analyzer_viewer_add_command(self, command: list[str]):
        if self._habmoti.device is None:
            print("  You need to connect a device before adding an analyzer.")
            return

        if not command:
            while True:
                subcommand = input("[Habmoti / analyzer / viewer / add]> ").strip().lower().split()
                if not subcommand or subcommand[0] in ["back", ".."]:
                    return
                else:
                    self._handle_analyzer_viewer_add_command(subcommand)

        if not isinstance(self._habmoti.analyzer, AnalyzerList):
            raise ValueError(
                "Analyzer should be an AnalyzerList to use multiple analyzers. "
                "This should not happen, you are invited to contact the developers."
            )
        analyzers: AnalyzerList = self._habmoti.analyzer

        try:
            if command[0] in ["list", "ls"]:
                print("  Available viewer analyzers:")
                print("    console <joint_center> - Print the joint positions to the console")
                print("    matplotlib - Display the joint positions in a Matplotlib window")
                print("    opengl - Display the joint positions in an OpenGL window")
            elif command[0] == "console":
                joint_center_name = (
                    input("  Joint center name (leave empty to cancel): ").strip() if len(command) < 2 else command[1]
                )
                if joint_center_name == "":
                    return
                try:
                    joint_center = self._habmoti.device.body_model.from_name(joint_center_name)
                except:
                    raise ValueError(f"Invalid joint center name: {joint_center_name}")
                analyzers.append(ToConsoleAnalyzer(joint_center=joint_center))
                print(f"  Added a console viewer.")
            elif command[0] == "matplotlib":
                analyzers.append(ToMatplotlibAnalyzer())
                print("  Added a Matplotlib viewer.")
            elif command[0] == "opengl":
                analyzers.append(ToOglAnalyzer())
                print("  Added an OpenGL viewer.")
            else:
                print(f"  Unknown viewer analyzer: {command[0]}. Use the 'list' subcommand for available analyzers.")
        except Exception as e:
            print(f"  Failed to add analyzer: {e}")

    def _handle_analyzer_viewer_added_command(self):
        print("  Currently added analyzers:")
        if not isinstance(self._habmoti.analyzer, AnalyzerList):
            raise ValueError(
                "Analyzer should be an AnalyzerList to use multiple analyzers. "
                "This should not happen, you are invited to contact the developers."
            )
        analyzers: AnalyzerList = self._habmoti.analyzer
        for i, analyzer in enumerate(analyzers):
            print(f"    [{i}] {analyzer.name}")

    def _handle_analyzer_viewer_remove_command(self, command: list[str]):
        if not command:
            index_str = input("  Index of the analyzer to remove (leave empty to cancel): ").strip()
        else:
            index_str = command[0]
        if index_str == "":
            return
        try:
            index = int(index_str)
        except:
            print(f"  Invalid index: {index_str}")
            return

        if not isinstance(self._habmoti.analyzer, AnalyzerList):
            raise ValueError(
                "Analyzer should be an AnalyzerList to use multiple analyzers. "
                "This should not happen, you are invited to contact the developers."
            )
        analyzers: AnalyzerList = self._habmoti.analyzer

        if index < 0 or index >= len(analyzers):
            print(f"  Invalid index: {index}. Use the 'added' subcommand to see valid indices.")
            return

        removed_analyzer_name = analyzers[index].name
        del analyzers[index]
        print(f"  Removed analyzer: {removed_analyzer_name}")
