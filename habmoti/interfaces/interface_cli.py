import json
from pathlib import Path

from .utils import habmoti_from_dict
from ..analyzers.analyzer import AnalyzerList
from ..analyzers.movement_analyzers.hop_analyzer import HopAnalyzer
from ..analyzers.writers.to_console_analyzer import ToConsoleAnalyzer
from ..analyzers.writers.to_csv_analyzer import ToCsvAnalyzer
from ..analyzers.viewers.to_matplotlib_analyzer import ToMatplotlibAnalyzer
from ..analyzers.viewers.to_ogl_analyzer import ToOglAnalyzer
from ..devices.device import Device
from ..devices.zed_device import ZedDevice, ZedMockDevice
from ..devices.csv_reader_device import CsvReaderDevice
from ..habmoti import Habmoti


def navigable_menu(func):
    def wrapper(self, commands: list[str], previous_commands: list[str] = []):
        has_navigated = not commands
        if has_navigated:
            commands = _prompt_commands(previous_commands=previous_commands)
        if not commands:
            return wrapper(self, commands=[], previous_commands=previous_commands)

        if has_navigated and (commands[0] in ["back", ".."]):
            return

        ignore_has_navigated = func(self, commands, previous_commands)

        if not ignore_has_navigated and has_navigated:
            return wrapper(self, commands=[], previous_commands=previous_commands)

    return wrapper


class InterfaceCli:
    def __init__(self):
        self._habmoti = Habmoti(analyzer=AnalyzerList())
        self._auto_initialize = False

    def exec(self) -> None:
        print("Welcome to the HABMOT-I CLI!")
        print("Type 'help' for a list of commands, or 'quit' to quit.")

        commands = []

        while True:
            try:
                commands = _prompt_commands(previous_commands=[])
            except Exception as e:
                print("Error reading input. Please try again.")
                continue

            if not commands:
                continue
            elif commands[0] in ["help", "h"]:
                self._handle_help_command()
            elif commands[0] == "load":
                self._handle_load_command(commands[1:])
            elif commands[0] == "device":
                self._handle_device_command(commands[1:], [commands[0]])
            elif commands[0] == "analyzer":
                self._handle_analyzer_command(commands[1:], [commands[0]])
            elif commands[0] == "controller":
                self._handle_controller_command(commands[1:], [commands[0]])
            elif commands[0] == "quit":
                self._handle_quit_command()
                break
            else:
                print(f"  Unknown command: {commands[0]}. Type 'help' for a list of commands.")
        
        self._handle_controller_command(["terminate"], previous_commands=["controller"])

    def exec_from_config(self, config_filepath: str):
        is_success = self._handle_load_command([f"filepath={config_filepath}"])
        if not is_success:
            # The error message is already printed in _handle_load_command, so we just exit silently here
            return
        if self._habmoti.device is None:
            raise ValueError("No device configured. Please configure a device in the configuration file, or use 'exec' to start the CLI.")
        
        self._handle_controller_command(["initialize"], previous_commands=["controller"])
        self._habmoti.exec()


    def _handle_help_command(self):
        print("""  Available commands:
    help,h     - Show this help message
    load       - Load a configuration from a JSON file. This will remove the current device and analyzer.
    device     - Manage devices (type 'device help' for more information)
    analyzer   - Manage analyzers (type 'analyzer help' for more information)
    controller - Start the HABMOT-I system
    quit       - Exit the CLI
    
    When navigating through subcommands, you can usually type 'help' for more information on the subcommands and also type"
    'list' to see available options. To go back to the previous menu, leave the input empty or type 'back'.""")

    def _handle_quit_command(self):
        print("Exiting the HABMOT-I CLI. Goodbye!")

    def _handle_load_command(self, parameters: list[str]) -> bool:
        """
        Load a configuration from a JSON file. This will remove the current device and analyzer.
        If a configuration file path is provided in the parameters, it will be used directly. Otherwise, the user will be prompted to enter a file path.

        Returns True if the configuration was loaded successfully, False otherwise.
        """
        analyzers = self._habmoti.analyzer
        if analyzers is not None and not isinstance(analyzers, AnalyzerList):
            raise ValueError(
                "Analyzer should be an AnalyzerList to use multiple analyzers. "
                "This should not happen, you are invited to contact the developers."
            )
        if self._habmoti.device is not None or (analyzers is not None and len(analyzers) > 0):
            response = (
                input(
                    "  Loading a configuration will remove the current device and analyzer. Do you want to continue?  (y/N) "
                )
                .strip()
                .lower()
            )
            if response != "y":
                return

        parameters = _fill_parameters(all_keys=["filepath"], parameters=parameters)
        filepath = _input_if_not_in_parameters(
            parameters,
            key="filepath",
            prompt="Path of the configuration file to load (leave empty to cancel)",
            value_type=str,
        )
        if not filepath:
            return
        try:
            with open(filepath, "r") as f:
                config = json.load(f)

            self._habmoti.analyzer = None
            habmoti_from_dict(self._habmoti, config)

            print(f"  Configuration loaded from {filepath}.")
            return True
        except Exception as e:
            print(f"  Failed to load configuration: {e}")
            return False

    @navigable_menu
    def _handle_device_command(self, commands: list[str], previous_commands: list[str]) -> bool:
        ignore_has_navigated = False
        if commands[0] in ["help", "h"]:
            self._handle_device_help_command()
        elif commands[0] in ["list", "ls"]:
            self._handle_device_list_command()
        elif commands[0] == "add":
            self._handle_device_add_command(commands[1:], previous_commands + [commands[0]])
        elif commands[0] == "added":
            print(f"  Added device: {self._habmoti.device.name if self._habmoti.device is not None else 'None'}")
        else:
            print(
                f"  Unknown 'device' subcommand: '{commands[0]}'. Use the 'help' subcommand for a list of subcommands."
            )
        return ignore_has_navigated

    def _handle_device_help_command(self):
        print("""Available 'device' subcommands:
    help,h            - Show this help message.
    list,ls           - List available devices.
    add <device_name> - Add a device to the system. If <device_name> is not specified, you will be prompted to enter it.
    added             - Show the currently added device.
    back,..           - Go back to the previous menu.""")

    def _handle_device_list_command(self):
        print("""  Available devices:
    zed - ZED camera
    zed_mock - ZED (Mock) camera
    csv_reader - CSV reader""")

    def _handle_device_add_command(self, commands: list[str], previous_commands: list[str] = []):
        if self._habmoti.is_initialized:
            print(
                "  Cannot change device while Habmoti is started. Please stop the pipeline before changing the device."
            )
            return
        if self._habmoti.device is not None:
            response = (
                input(
                    "  A device is already added. Please note, this will remove the current analyzer. "
                    "Do you want to continue?  (y/N) "
                )
                .strip()
                .lower()
            )
            if response != "y":
                return
        self._handle_device_add_command_guarded(commands=commands, previous_commands=previous_commands)

    @navigable_menu
    def _handle_device_add_command_guarded(self, commands: list[str], previous_commands: list[str] = []) -> bool:
        ignore_has_navigated = False

        try:
            if commands[0] in ["list", "ls", "help", "h"]:
                self._handle_device_list_command()
            elif commands[0] == "zed" or commands[0] == "zed_mock":
                self._handle_device_add_zed_command(device_name=commands[0], parameters=commands[1:])
                ignore_has_navigated = True
            elif commands[0] == "csv_reader":
                self._handle_device_add_csv_reader_command(commands[1:])
                ignore_has_navigated = True
            else:
                print(f"  Unknown device: {commands[0]}. Use the 'list' subcommand for available devices.")
        except Exception as e:
            print(f"  Failed to add device: {e}")

        return ignore_has_navigated

    def _safe_device_add(self, device: Device):
        self._habmoti.analyzer = None
        self._habmoti.device = device
        self._habmoti.analyzer = AnalyzerList()

    def _handle_device_add_zed_command(self, device_name: str, parameters: list[str]):
        is_mock = device_name == "zed_mock"

        parameters = _fill_parameters(
            all_keys=["filepath"] + (["fps", "max_lag"] if is_mock else []), parameters=parameters
        )

        config_path = _input_if_not_in_parameters(
            parameters,
            key="filepath",
            prompt="A configuration file is required to use the ZED camera. If not done already, you can create one by using the ZED360 tool.\n  Path of the file",
            default="zed_configuration.json",
            value_type=str,
        )
        if is_mock:
            target_fps = _input_if_not_in_parameters(
                parameters, key="fps", prompt="Target FPS", default=30, value_type=int
            )
            max_fps_lag_ms = _input_if_not_in_parameters(
                parameters, key="max_lag", prompt="Max FPS lag in ms", default=0, value_type=int
            )

            self._safe_device_add(
                device=ZedMockDevice(
                    configuration_filepath=config_path, target_fps=target_fps, max_fps_lag_ms=max_fps_lag_ms
                )
            )
        else:
            self._safe_device_add(device=ZedDevice(configuration_filepath=config_path))
        print(f"  ZED{' (Mock)' if is_mock else ''} camera added.")

    def _handle_device_add_csv_reader_command(self, parameters: list[str]):
        parameters = _fill_parameters(all_keys=["filepath"], parameters=parameters)
        filepath = _input_if_not_in_parameters(
            parameters,
            key="filepath",
            prompt="Path of the CSV file to read (leave empty to cancel)",
            value_type=str,
        )
        if not filepath:
            return

        self._safe_device_add(device=CsvReaderDevice(filepath=Path(filepath)))
        print("  CSV reader added.")

    @navigable_menu
    def _handle_analyzer_command(self, command: list[str], previous_commands: list[str]) -> bool:
        ignore_has_navigated = False

        if command[0] in ["help", "h"]:
            self._handle_analyzer_help_command()
        elif command[0] in ["list_types", "lt"]:
            self._handle_analyzer_types_list_command()
        elif command[0] in ["list", "ls"]:
            self._handle_analyzers_list_command()
        elif command[0] == "add":
            self._handle_analyzer_add_command(command[1:], previous_commands=previous_commands + [command[0]])
        elif command[0] == "added":
            self._handle_analyzer_added_command()
        elif command[0] == "remove":
            self._handle_analyzer_remove_command(command[1:])
        else:
            print(
                f"  Unknown 'analyzer' subcommand: '{command[0]}'. Use the 'help' subcommand for a list of subcommands."
            )
        return ignore_has_navigated

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

    def _handle_analyzer_add_command(self, commands: list[str], previous_commands: list[str]):
        if self._habmoti.device is None:
            print("  You need to add a device before adding an analyzer.")
            return
        if not isinstance(self._habmoti.analyzer, AnalyzerList):
            raise ValueError(
                "Analyzer should be an AnalyzerList to use multiple analyzers. "
                "This should not happen, you are invited to contact the developers."
            )

        self._handle_analyzer_add_command_guarded(commands, previous_commands)

    @navigable_menu
    def _handle_analyzer_add_command_guarded(self, commands: list[str], previous_commands: list[str]) -> bool:
        ignore_has_navigated = False

        try:
            if commands[0] in ["list", "ls"]:
                self._handle_analyzers_list_command()
            elif commands[0] == "matplotlib":
                self._handle_add_matplotlib_command()
                ignore_has_navigated = True
            elif commands[0] == "opengl":
                self._handle_add_opengl_command()
                ignore_has_navigated = True
            elif commands[0] == "console":
                self._handle_add_console_command(commands[1:])
                ignore_has_navigated = True
            elif commands[0] == "csv":
                self._handle_add_csv_command(commands[1:])
                ignore_has_navigated = True
            elif commands[0] == "hop":
                self._handle_add_hop_command()
                ignore_has_navigated = True
            else:
                print(f"  Unknown analyzer: {commands[0]}. Use the 'list' subcommand for available analyzers.")
        except Exception as e:
            print(f"  Failed to add analyzer: {e}")

        return ignore_has_navigated

    def _handle_add_matplotlib_command(self):
        self._habmoti.analyzer.append(ToMatplotlibAnalyzer())
        print("  Added a Matplotlib viewer.")

    def _handle_add_opengl_command(self):
        self._habmoti.analyzer.append(ToOglAnalyzer())
        print("  Added an OpenGL viewer.")

    def _handle_add_console_command(self, parameters: list[str]):
        parameters = _fill_parameters(all_keys=["joint"], parameters=parameters)
        joint_center = _input_if_not_in_parameters(
            parameters,
            key="joint",
            prompt="Joint center name (leave empty to cancel)",
            value_type=str,
        )
        if not joint_center:
            return

        try:
            # Test if it is going to fail later, so fail now
            self._habmoti.device.body_model.from_name(joint_center)
        except:
            raise ValueError(f"Invalid joint center name: {joint_center}")

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

    def _handle_add_csv_command(self, parameters: list[str]):
        parameters = _fill_parameters(all_keys=["filepath"], parameters=parameters)
        filepath = _input_if_not_in_parameters(
            parameters,
            key="filepath",
            prompt="CSV file path (leave empty to cancel)",
            value_type=str,
        )
        if not filepath:
            return

        try:
            csv_path = Path(filepath)
        except:
            raise ValueError(f"Invalid CSV file path: {filepath}")

        auto_increment = _input_if_not_in_parameters(
            parameters,
            key="auto_increment",
            prompt="Automatically increment filename if it already exists? (y/N)",
            default="y",
            value_type=lambda x: x.strip().lower() == "y",
        )
        allow_overwrite = _input_if_not_in_parameters(
            parameters,
            key="allow_overwrite",
            prompt="Allow overwriting existing files? (y/N)",
            default="N",
            value_type=lambda x: x.strip().lower() == "y",
        )

        self._habmoti.analyzer.append(
            ToCsvAnalyzer(filepath=csv_path, auto_increment=auto_increment, allow_overwrite=allow_overwrite)
        )
        print(f"  Added a CSV writer.")

    def _handle_add_hop_command(self):
        self._habmoti.analyzer.append(HopAnalyzer())
        print(f"  Added a Hop analyzer.")

    def _handle_controller_command(self, command: list[str], previous_commands: list[str]) -> bool:
        if self._habmoti.device is None:
            print("  You need to add a device before starting the controller.")
            return
        if not isinstance(self._habmoti.analyzer, AnalyzerList):
            raise ValueError(
                "Analyzer should be an AnalyzerList to use multiple analyzers. "
                "This should not happen, you are invited to contact the developers."
            )
        self._handle_controller_command_guarded(command, previous_commands=previous_commands)

    @navigable_menu
    def _handle_controller_command_guarded(self, command: list[str], previous_commands: list[str]) -> bool:
        ignore_has_navigated = False

        try:
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
        except Exception as e:
            print(f"  Controller error: {e}")

        return ignore_has_navigated

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


def _prompt_commands(previous_commands: list[str]):
    prompt = f"[{' / '.join(['Habmoti'] + previous_commands)}]> "
    try:
        command = input(prompt).strip().lower().split()
    except:
        print("Error reading input. Please try again.")
        return _prompt_commands(previous_commands)
    return command


def _fill_parameters(all_keys: list[str], parameters: list[str]):
    output = {key: None for key in all_keys}

    return output | {
        key: value for param in parameters if "=" in param for key, value in [param.split("=", 1)] if key in all_keys
    }


def _input_if_not_in_parameters(parameters: dict, key: str, prompt: str, default=None, value_type=str):
    if key in parameters and parameters[key]:
        return value_type(parameters[key])
    else:
        value_str = input(f"  {prompt}{'' if default is None else f' [default={default}]'}: ").strip()
        if not value_str:
            return default
        else:
            return value_type(value_str)
