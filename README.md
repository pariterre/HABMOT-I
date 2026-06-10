# HABMOT-I

## Installation
Assuming the dedicated conda environment is installed and activated, to setup the project, run the following command in the terminal:

```bash
pip install -e .[zed_mocker,gui_opengl,gui_matplotlib]
```
The `[zed_mocker]` part of the command is optional and is only required if one wants to use the `mocked_zed` device. Additionnally, if one wants to use the `mocked_zed` device, they must also manually install the `biorbd` library as it is not available on pip. 

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
- `mocked_zed`: Use mocked data that simulates the ZED camera output. 
    - This requires the [HABMOTI_ZED_PARAMETERS](#habmoti_zed_parameters) and the  [HABMOTI_MOCKED_ZED_PARAMETERS](#habmoti_mocked_zed_parameters) environment variable to be set.
    - Note, this requires the `biorbd` library to be installed. 
- `csv_reader`: Use a CSV file as the source of motion data. 
    - This requires the [HABMOTI_CSV_READER_PARAMETERS](#habmoti_csv_reader_parameters) environment variable to be set.  


### HABMOTI_ZED_PARAMETERS
This variable defines the configuration of the ZED device and consists of JSON formatted string. It must contain the following keys:
- `configuration_filepath`: The path to the ZED configuration file (see the installation available at http://github.com/laboratoireELAN-ZED/Documentation)

### HABMOTI_MOCKED_ZED_PARAMETERS
This variable defines the configuration of the mocked ZED device and consists of JSON formatted string. It must contain the following keys:
- `target_fps`: The target frames per second to simulate as an integer (e.g. 30)
- `max_fps_lag_ms`: The maximum lag to simulate inconsistencies in the frame rate in milliseconds to simulate as an integer. Please note, on Windows, target_fps will not be perfectly respected anyway, so this parameter does not make much of a difference. 

### HABMOTI_CSV_READER_PARAMETERS
This variable defines the configuration of the CSV reader device and consists of JSON formatted string. It must contain the following keys:
- `filepath`: The path to the input CSV file. The CSV file must be created from the `to_csv` analyzer or follow the same format.

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

### HABMOTI_STOP_CONTROLLER
This variable defines the stopping criteria of the main loop and consists of JSON formatted string. It must contain the following keys:
- `max_runtime`: The maximum runtime of the main loop in seconds as an integer. If set to `null` or omitted, the main loop will run indefinitely.
- `stop_if_data_runs_out`: Whether to stop the main loop if the device runs out of data to provide as a boolean. If set to `true`, the main loop will stop if the device runs out of data to provide. If set to `false` or omitted, the main loop will continue running even if the device runs out of data to provide.
