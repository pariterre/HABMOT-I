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
                print("Exiting the HABMOT-I CLI. Goodbye!")
                break
            elif command[0] == "device":
                self._handle_device_command(command[1:])
            elif command[0] == "analyzer":
                self._handle_analyzer_command(command[1:])
            elif command[0] == "controller":
                self._handle_controller_command(command[1:])
            elif command[0] == "help":
                print("""  Available commands:
    help - Show this help message
    device - Manage devices (type 'device help' for more information)
    analyzer - Manage analyzers (type 'analyzer help' for more information)
    controller - Start the HABMOT-I system
    quit - Exit the CLI
    
    When navigating through subcommands, you can usually type 'help' for more information on the subcommands and also type"
    'list' to see available options. To go back to the previous menu, leave the input empty or type 'back'.""")
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
        elif command[0] == "add":
            self._handle_device_add_command(command[1:])
        elif command[0] == "added":
            print(f"  Added device: {self._habmoti.device.name if self._habmoti.device is not None else 'None'}")
        else:
            print(
                f"  Unknown 'device' subcommand: '{command[0]}'. Use the 'help' subcommand for a list of subcommands."
            )

    def _handle_device_help_command(self):
        print("""Available 'device' subcommands:
    help - Show this help message.
    list,ls - List available devices.
    add <device_name> - add a device to the system. If <device_name> is not specified, you will be prompted to enter it.
    added - Show the currently added device.
    back,.. - Go back to the previous menu.""")

    def _handle_device_list_command(self):
        print("""  Available devices:
    zed - ZED camera
    zed_mocked - ZED (Mocked) camera
    csv_reader - CSV reader""")

    def _handle_device_add_command(self, command: list[str]):
        if self._habmoti.is_initialized:
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
                    self._handle_device_add_command(subcommand)
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
            "  Path of the file [default=zed_configuration.json]: "
        ).strip()
        if config_path == "":
            config_path = "zed_configuration.json"

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

    def _handle_analyzer_command(self, command: list[str], filter_type: str | None = None):
        if not command:
            while True:
                subcommand = input("[Habmoti / analyzer]> ").strip().lower().split()
                if not subcommand or subcommand[0] in ["back", ".."]:
                    return
                else:
                    self._handle_analyzer_command(subcommand)
        if command[0] in ["help", "h"]:
            self._handle_analyzer_help_command()
        elif command[0] in ["list_types", "lt"]:
            self._handle_analyzer_types_list_command()
        elif command[0] in ["list", "ls"]:
            self._handle_analyzers_list_command()
        elif command[0] == "add":
            self._handle_analyzer_add_command(command[1:])
        elif command[0] == "added":
            self._handle_analyzer_added_command()
        elif command[0] == "remove":
            self._handle_analyzer_remove_command(command[1:])
        else:
            print(
                f"  Unknown 'analyzer' subcommand: '{command[0]}'. Use the 'help' subcommand for a list of subcommands."
            )

    def _handle_analyzer_help_command(self):
        print("""  Available 'analyzer' subcommands:
    help,h                  - Show this help message.
    list_type,t             - List available analyzer types.
    list,ls [<type_name>]   - List available analyzers. If <type_name> (see [list_types]) is specified, only analyzers of that type are listed.
    add <analyzer_name>     - Add an analyzer to the system. If <analyzer_name> is not specified, you will be prompted to enter it.
    added [<type_name>]     - Show the currently added analyzers. If <type_name> is specified, only analyzers of that type will be shown.
    remove <analyzer_index> - Remove the analyzer with the specified index. You can see the indices by using the 'added' subcommand.
    back,..                 - Go back to the previous menu""")

    def _handle_analyzer_types_list_command(self):
        print("""  Available 'analyzer' types:
    data   - Analyzers that only process the data and do not have side effects (e.g. movement analyzers, etc.)
    viewer - Analyzers that display the data in some way (e.g. Matplotlib, OpenGL, Console, etc.)
    writer - Analyzers that write the data to some output (e.g. CSV file, database, etc.)""")

    def _handle_analyzers_list_command(self):
        print("""  Available 'analyzers':
    viewers:
      matplotlib - Display the joint positions in a Matplotlib window
      opengl     - Display the joint positions in an OpenGL window
    writers:
      console    - Print the joint positions to the console
      csv        - Write the joint positions to a CSV file""")

    def _handle_analyzer_add_command(self, command: list[str]):
        if self._habmoti.device is None:
            print("  You need to connect a device before adding an analyzer.")
            return
        if not isinstance(self._habmoti.analyzer, AnalyzerList):
            raise ValueError(
                "Analyzer should be an AnalyzerList to use multiple analyzers. "
                "This should not happen, you are invited to contact the developers."
            )

        if not command:
            while True:
                subcommand = input("[Habmoti / analyzer / add]> ").strip().lower().split()
                if not subcommand or subcommand[0] in ["back", ".."]:
                    return
                else:
                    self._handle_analyzer_add_command(subcommand)

        try:
            if command[0] in ["list", "ls"]:
                self._handle_analyzers_list_command()
            elif command[0] == "matplotlib":
                self._handle_add_matplotlib_command()
            elif command[0] == "opengl":
                self._handle_add_opengl_command()
            elif command[0] == "console":
                self._handle_add_console_command(command[1:])
            elif command[0] == "csv":
                self._handle_add_csv_command(command[1:])
            else:
                print(f"  Unknown viewer analyzer: {command[0]}. Use the 'list' subcommand for available analyzers.")
        except Exception as e:
            print(f"  Failed to add analyzer: {e}")

    def _handle_add_matplotlib_command(self):
        self._habmoti.analyzer.append(ToMatplotlibAnalyzer())
        print("  Added a Matplotlib viewer.")

    def _handle_add_opengl_command(self):
        self._habmoti.analyzer.append(ToOglAnalyzer())
        print("  Added an OpenGL viewer.")

    def _handle_add_console_command(self, command: list[str]):
        joint_center_name = (
            input("  Joint center name (leave empty to cancel): ").strip() if len(command) < 1 else command[0]
        )
        if joint_center_name == "":
            return
        try:
            joint_center = self._habmoti.device.body_model.from_name(joint_center_name)
        except:
            raise ValueError(f"Invalid joint center name: {joint_center_name}")
        self._habmoti.analyzer.append(ToConsoleAnalyzer(joint_center=joint_center))
        print(f"  Added a console writer.")

    def _handle_analyzer_added_command(self):
        if not isinstance(self._habmoti.analyzer, AnalyzerList):
            raise ValueError(
                "Analyzer should be an AnalyzerList to use multiple analyzers. "
                "This should not happen, you are invited to contact the developers."
            )
        analyzers: AnalyzerList = self._habmoti.analyzer

        print("  Currently added analyzers:")
        for i, analyzer in enumerate(analyzers):
            print(f"    [{i}] {analyzer.name}")

    def _handle_analyzer_remove_command(self, command: list[str]):
        if not isinstance(self._habmoti.analyzer, AnalyzerList):
            raise ValueError(
                "Analyzer should be an AnalyzerList to use multiple analyzers. "
                "This should not happen, you are invited to contact the developers."
            )
        analyzers: AnalyzerList = self._habmoti.analyzer

        index_str = (
            input("  Index of the analyzer to remove (leave empty to cancel): ").strip() if not command else command[0]
        )
        if index_str == "":
            return
        try:
            index = int(index_str)
        except:
            print(f"  Invalid index: {index_str}")
            return

        if index < 0 or index >= len(analyzers):
            print(f"  Invalid index: {index}. Use the 'added' subcommand to see valid indices.")
            return

        removed_analyzer_name = analyzers[index].name
        del analyzers[index]
        print(f"  Removed analyzer: {removed_analyzer_name}")

    def _handle_add_csv_command(self, command: list[str]):
        filepath = input("  CSV file path (leave empty to cancel): ").strip() if len(command) < 1 else command[0]
        if filepath == "":
            return
        try:
            csv_path = Path(filepath)
        except:
            raise ValueError(f"Invalid CSV file path: {filepath}")
        self._habmoti.analyzer.append(ToCsvAnalyzer(filepath=csv_path))
        print(f"  Added a CSV writer.")

    def _handle_controller_command(self, command: list[str]):
        if self._habmoti.device is None:
            print("  You need to connect a device before starting the controller.")
            return

        if not command:
            while True:
                subcommand = input("[Habmoti / controller]> ").strip().lower().split()
                if not subcommand or subcommand[0] in ["back", ".."]:
                    return
                else:
                    self._handle_controller_command(subcommand)
        if command[0] in ["help", "h"]:
            self._handle_controller_help_command()
        elif command[0] == "initialize":
            self._handle_controller_initialize_command()
        elif command[0] == "terminate":
            self._handle_controller_terminate_command()
        elif command[0] == "start":
            self._handle_controller_start_command()
        elif command[0] == "stop":
            self._handle_controller_stop_command()
        else:
            print(
                f"  Unknown 'controller' subcommand: '{command[0]}'. Use the 'help' subcommand for a list of subcommands."
            )

    def _handle_controller_help_command(self):
        print("""  Available 'controller' subcommands:
    help,h     - Show this help message.
    list,ls    - List available controllers.
    initialize - Initialize the HABMOT-I system.
    terminate  - Terminate the HABMOT-I system.
    start      - Start recording a trial.
    stop       - Stop recording the current trial.
    back,..    - Go back to the previous menu.""")

    def _handle_controller_initialize_command(self):
        self._habmoti.initialize()
        print("HABMOT-I initialized.")

    def _handle_controller_terminate_command(self):
        self._habmoti.terminate()
        print("HABMOT-I terminated.")

    def _handle_controller_start_command(self):
        if not self._habmoti.is_initialized:
            print("  HABMOT-I is not initialized. Please initialize the system before starting a trial.")
            return
        self._habmoti.start_trial()
        print("HABMOT-I started a new trial.")

    def _handle_controller_stop_command(self):
        if not self._habmoti.is_initialized:
            print("  HABMOT-I is not initialized. Please initialize the system before stopping a trial.")
            return
        self._habmoti.stop_trial()
        print("HABMOT-I stopped the current trial.")
