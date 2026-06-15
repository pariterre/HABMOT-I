# HABMOT-I

## Installation
Assuming the dedicated conda environment is installed and activated, to setup the project, run the following command in the terminal:

```bash
pip install -e .[zed_mock,gui_opengl,gui_matplotlib]
```
The `[zed_mock]` part of the command is optional and is only required if one wants to use the `zed_mock` device. Additionnally, if one wants to use the `zed_mock` device, they must also manually install the `biorbd` library as it is not available on pip. 

The `[gui_opengl]` part of the command is optional and is only required to run the `to_ogl` option of the analyzers. 

The `[gui_matplotlib]` part of the command is optional and is only required to run the `to_matplotlib` option of the analyzers.
```
conda install -c conda-forge biorbd
```

## Running the code
The code that can be run is the `main.py` file located in the root directory of the project. From the `runner` directory, run the following command in the terminal:
```bash
python main.py
```
To run the code, one must declare the environment variables described in the subsections below. 

NOTE: If the code is run using *vscode*, you can copy-paste the file `.vscode/launch.json.in` to `.vscode/launch.json` and fill in the values. You will then be able to run the code using the *Run and Debug* tab in *vscode* (or press the *F5* key).

### HABMOTI_DEVICE_TYPE
This variable defines what device to use to capture the motion data and consists of a single string with one of the following value:

- `zed`: Use the ZED camera to capture motion data. 
    - This requires the [HABMOTI_ZED_PARAMETERS](#habmoti_zed_parameters) environment variable to be set.
- `zed_mock`: Use mocked data that simulates the ZED camera output. 
    - This requires the [HABMOTI_ZED_PARAMETERS](#habmoti_zed_parameters) and the  [HABMOTI_ZED_MOCK_PARAMETERS](#habmoti_zed_mock_parameters) environment variable to be set.
    - Note, this requires the `biorbd` library to be installed. 
- `csv_reader`: Use a CSV file as the source of motion data. 
    - This requires the [HABMOTI_CSV_READER_PARAMETERS](#habmoti_csv_reader_parameters) environment variable to be set.  


### HABMOTI_ZED_PARAMETERS
This variable defines the configuration of the ZED device and consists of JSON formatted string. It must contain the following keys:
- `configuration_filepath`: The path to the ZED configuration file (see the installation available at http://github.com/laboratoireELAN-ZED/Documentation)

### HABMOTI_ZED_MOCK_PARAMETERS
This variable defines the configuration of the ZED mock device and consists of JSON formatted string. It must contain the following keys:
- `target_fps`: The target frames per second to simulate as an integer (e.g. 30)
- `max_fps_lag_ms`: The maximum lag to simulate inconsistencies in the frame rate in milliseconds to simulate as an integer. Please note, on Windows, target_fps will not be perfectly respected anyway, so this parameter does not make much of a difference. 

### HABMOTI_CSV_READER_PARAMETERS
This variable defines the configuration of the CSV reader device and consists of JSON formatted string. It must contain the following keys:
- `filepath`: The path to the input CSV file. The CSV file must be created from the `to_csv` analyzer or follow the same format.
- `frame_per_second`: The target fps to stream the data, as integer. 
    - `null` is as fast as possible
    - A negative value targets to replicate the original frame rate
    - Zero (0) is on a frame by frame basis (i.e. pressing enter between each frame)
    - A positive value is a fixed value
- `terminate_on_end`: Whether to terminate the main loop when the end of the file is reached as a boolean. If set to `true`, the device will send a terminate signal to the main loop. If set to `false` or omitted, the device send a stop_trial signal to the main loop.

### HABMOTI_ANALYZERS
This variable defines the analyzers to use and consists of a list of comma-separated strings surrounded by square brackets. Each string must be one of the following values:
- `to_console`: Print the motion data to the console.
    - This requires the [HABMOTI_TO_CONSOLE_ANALYZER_PARAMETERS](#habmoti_to_console_analyzer_parameters) environment variable to be set.
- `to_csv`: Save the motion data to a CSV file.
    - This requires the [HABMOTI_TO_CSV_ANALYZER_PARAMETERS](#habmoti_to_csv_analyzer_parameters) environment variable to be set.
- `to_ogl`: Visualize the motion data in a OpenGL window.
    - This requires the `pyopengl` and `pyopengl_accelerate` packages to be installed (e.g. `pip install -e .[gui_opengl]`).
- `to_matplotlib`: Visualize the motion data in a Matplotlib window.
    - This requires the `matplotlib` package to be installed (e.g. `pip install -e .[gui_matplotlib]`).

### HABMOTI_TO_CONSOLE_ANALYZER_PARAMETERS
This variable defines the configuration of the `to_console` analyzer and consists of JSON formatted string. It must contain the following keys:
- `joint_center`: The degree of freedom to print the value of in the console as a string. The valid values depend on the model used.

### HABMOTI_TO_CSV_ANALYZER_PARAMETERS
This variable defines the configuration of the `to_csv` analyzer and consists of JSON formatted string. It must contain the following keys:
- `filepath`: The path to the output CSV file.
- `auto_increment`: Whether to automatically increment the filename if the file already exists as a boolean. If set to `true`, the filename will be automatically incremented (e.g. `output_1.csv`, `output_2.csv`, etc.) if the file already exists. If set to `false` or omitted, the file will be overwritten if it already exists.
- `allow_overwrite`: Whether to allow overwriting the file if it already exists as a boolean. If set to `true`, the file will be overwritten if it already exists. If set to `false` or omitted, the file will not be overwritten if it already exists and an error will be raised. Please note that if `auto_increment` is set to `true`, the `allow_overwrite` parameter will be ignored as the file will never be overwritten.

### HABMOTI_STOP_CONTROLLER
This variable defines the stopping criteria of the main loop and consists of JSON formatted string. It must contain the following keys:
- `max_runtime`: The maximum runtime of the main loop in seconds as an integer. If set to `null` or omitted, the main loop will run indefinitely.
- `stop_if_data_runs_out`: Whether to stop the main loop if the device runs out of data to provide as a boolean. If set to `true`, the main loop will stop if the device runs out of data to provide. If set to `false` or omitted, the main loop will continue running even if the device runs out of data to provide.

## Running the CLI
The code that can be run is the `main_cli.py` file located in the root directory of the project. From the `runner` directory, run the following command in the terminal:
```bash
python main_cli.py
```

A menu will be displayed in the terminal to select the device and analyzers to use. 

A json file can be loaded to pre-fill the menu options. To do so, select the `load` option, then enter the path to the json file. 

### JSON configuration file
Examples of JSON configuration files can be found in the `templates` directory.

The JSON configuration is as follows:

```json
{
    "device": {
        "name": "<DEVICE_NAME>",
        "parameters": {
            // Device-specific parameters
        }
    },
    "analyzers": [
        {
            "name": "<FIRST_ANALYZER_NAME>",
            "parameters": {
                // Analyzer-specific parameters
            }
        }, 
        {
            "name": "<SECOND_ANALYZER_NAME>",
            "parameters": {
                // Analyzer-specific parameters
            }
        },
        ...
        {
            "name": "<LAST_ANALYZER_NAME>",
            "parameters": {
                // Analyzer-specific parameters
            }
        }
    ]
}
```
Where:
- `<DEVICE_NAME>` is the name of the device to use, which must be one of the following values:
    - `zed` ([parameters](#device-zed-parameters))
    - `zed_mock` ([parameters](#device-zed-mock-parameters))
    - `csv_reader` ([parameters](#device-csv-reader-parameters))
- `<ANALYZER_NAME>`
    - `to_console` ([parameters](#analyzer-to_console-parameters))
    - `to_csv` ([parameters](#analyzer-to_csv-parameters))
    - `to_ogl` (no parameters)
    - `to_matplotlib` (no parameters)

#### Device Zed parameters
The parameters for the `zed` device are as follows:
```json
{
    "configuration_filepath": "<PATH_TO_ZED_CONFIG>"
}
```

#### Device Zed Mock parameters
The parameters for the `zed_mock` device are as follows:
```json
{
    "configuration_filepath": "<PATH_TO_ZED_CONFIG>",
    "target_fps": <TARGET_FPS>,
    "max_fps_lag_ms": <MAX_FPS_LAG_MS>
}
```
where `<TARGET_FPS>` is the target frames per second to simulate as an integer (e.g. 30) and `<MAX_FPS_LAG_MS>` is the maximum lag to simulate inconsistencies in the frame rate in milliseconds to simulate as an integer. Please note, on Windows, target_fps will not be perfectly respected anyway, so this parameter does not make much of a difference.

#### Device CSV Reader parameters
The parameters for the `csv_reader` device are as follows:
```json
{
    "filepath": "<PATH_TO_CSV_FILE>",
    "frame_per_second": <FRAME_PER_SECOND>,
    "terminate_on_end": <TERMINATE_ON_END>
}
```
where `<FRAME_PER_SECOND>` can be:
- `null` for as fast as possible
- A negative value to replicate the original frame rate
- Zero (0) for a frame by frame basis (i.e. pressing enter between each frame)
- A positive value for a fixed value
where `<TERMINATE_ON_END>` is a boolean that indicates whether to terminate the main loop when the end of the file is reached. If set to `true`, the device will send a terminate signal to the main loop. If set to `false` or omitted, the device send a stop_trial signal to the main loop.

#### Analyzer to_console parameters
The parameters for the `to_console` analyzer are as follows:
```json
{
    "joint_center": "<JOINT_CENTER_NAME>"
}
```
where `<JOINT_CENTER_NAME>` is the degree of freedom to print the value of in the console as a string. The valid values depend on the model used.

#### Analyzer to_csv parameters

The parameters for the `to_csv` analyzer are as follows:
```json
{
    "filepath": "<PATH_TO_CSV_FILE>",
    "auto_increment": <AUTO_INCREMENT>,
    "allow_overwrite": <ALLOW_OVERWRITE>
}
```
where `<AUTO_INCREMENT>` is a boolean that indicates whether to automatically increment the filename if the file already exists. If set to `true`, the filename will be automatically incremented (e.g. `output_1.csv`, `output_2.csv`, etc.) if the file already exists. If set to `false` or omitted, the file will be overwritten if it already exists. 

`<ALLOW_OVERWRITE>` is a boolean that indicates whether to allow overwriting the file if it already exists. If set to `true`, the file will be overwritten if it already exists. If set to `false` or omitted, the file will not be overwritten if it already exists and an error will be raised. Please note that if `auto_increment` is set to `true`, the `allow_overwrite` parameter will be ignored as the file will never be overwritten.

