# ZED SDK - Getting Started Guide


## Glossary
- Target -> The NVIDIA computer on which the camera are pluged into (it is a small square box). 
- Host -> The computer on which the Target is connected when flashing  
- Flash -> Pressing the central button + reset. Allows using the Target as a USB key to update it from *NVIDIA SDK manager* on the Host. 

## Resources
The main resources should be from the *stereolabs* in priority (and probably solely): 
https://www.stereolabs.com/docs

WARNING: Using documentation from nvidia official website (or other official resources) will probably results in the Target being in a failing state. In case of emergency (e.g. Target won't turn on anymore), flashing Target (see [Initialization of Target](#initialization-of-target) below) should work. 


## Initialization of Target

### Prerequisites
The Host cannot be just any computer. We are limited to what is mentioned on the page <https://developer.nvidia.com/sdk-manager> in the section **Base SDKs Host Operating System Compatibility Matrix**. Also, the computer must be native on the mentioned operating system. The choice of JetPack depends on the SDKs we want to use (DeepStream, Holoscan, etc.). That said, using the docker version of the SDK manager seems to solve most of the compatibility issues (that is navigating the different versions of Ubuntu so any SDK version can be used).


### Troubleshooting

#### DPKG failed**
If you get the error "the DPKG command fails" (spoiler, it will fail...), you need to install (on the Host) a compatibility layer (assuming the Host is under Linux):
```bash
sudo apt install qemu-user-static binfmt-support  
sudo update-binfmts --enable  
```


### USB in the docker
Contrary to what the documentation mentions, you need to actively pass the USB to the docker. The command to launch the docker should therefore be the following (note that this command assumes that the Host is under Linux):
```bash
docker run -it --rm --privileged -v /dev/bus/<usb:/dev/bus/usb> -v /<dev:/dev> --network host sdkmanager --cli
```


### Non-optimal USB
If you get the mention that the USB is not optimal, there are potentially several causes.
- Using a virtualbox (not confirmed, as I had the same problem with Docker, solved by the next method)
- Bad USB port generation (confirmed). Solution: a USB-C to USB-C cable guarantees that the ports are compliant.


### Installing/updating Target drivers
As stated before, the main resources for this project should be from the *stereolabs* website (see [Resources](#resources)). The installation of the ZED SDK and ZED Tools should be done following the instructions on the website, but here is a summary of the steps to follow:


1. Download the *ZED Link Duo* drivers. The download link is https://www.stereolabs.com/en-ca/developers/drivers. For convenience, the latest file was put in `~/Programming/SDK/<file_name>`.
2. Download the *ZED SDK*, see the Getting Started of the ZED SDK section of the documentation. At the time of writing this, the download link is https://www.stereolabs.com/en-ca/developers/release. For convenience, the latest file was put in `~/Programming/SDK/<file_name>`. 
3. Run the install file (you may need to give it execution permissions with before, i.e. the first line of the following code).
    ```bash
    chmod +x <file_name>
    ./<file_name>
    ```
    During the installation, different prompts will ask you to accept or validate options, here are the answers:
    - Terms and license: first press "q" to exit the reading of the terms, then "y" and "enter" to accept them;
    - When requested, type the sudo password (admin password of the Target) and press "enter";
    - When requested for "Installing samples", type "y" and press "enter";
    - When requested for "Installation path", keep the default path (press "enter" without typing anything);
    - When requested for "Install of the Python API", type "y" and press "enter"; **IMPORTANT** You must have created a new conda environment AND have installed *python* and *pip* in that environment (see [Setup a conda environment](#setup-a-conda-environment)) before running the install file. Otherwise the installation of the Python API will be installed at the system level which can cause the computer the fail, forcing the user to reinstall the system.
    - When requested for the "Python executable", leave the default value, i.e. "python3" (press "enter" without typing anything); 
    - When requested for "Download and optimize the NEURAL Depth models", type "y" and press "enter". The first time (but only the first time) you accept these optimizations, it will take several hours to complete. We suggest you accept them though as it fasten things up on later install.
    - When requested for "Running the ZED Diagnostic tool", type "y" and press "enter". The same comment as for the previous point applies here, it will take a long time the first time but it is worth it.
    - When requested for "Optimizing the AI models", type "y" and press "enter". The same comment as for the previous point applies here, it will take a long time the first time but it is worth it.
4. Since Zed Tools must be regularly accessed, it is suggested to create a link to that folder directly in the nautilus explorer (the file explorer of Ubuntu). To do so, simply open the folder where the ZED SDK was installed (by default, it is in `/usr/local/zed`), then drag the `tools` folder to the "Favorites" section of the left panel of the nautilus explorer. This will create a link to the `tools` folder in the left panel, allowing you to easily access it in the future.


### Installing utilities
There are several utilities that can be useful for the development of the project, here are some of them:

#### Miniconda
Miniconda is a minimal version of Anaconda that allows you to create and manage conda environments. It is recommended to use conda environments for the development of the project, as it allows you to easily manage dependencies and avoid conflicts between different projects. To install Miniconda on the Target, from the terminal, follow these steps:

```bash
curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
chmod +x Miniconda3-latest-Linux-x86_64.sh
./Miniconda3-latest-Linux-x86_64.sh
```

During the installation, different prompts will ask you to accept or validate options, here are the answers:

- Press Return to review the license agreement;
- Enter "yes" to accept the EULA;
- When requested for "Miniconda3 will now be installed into this location", keep the default path (press "enter" without typing anything);
- When requested for "Do you wish the installer to initialize Miniconda3", type "y" and press "enter". This will add conda to your PATH variable, allowing you to use conda commands in the terminal without having to specify the full path to the conda executable.
- Restart the terminal to apply the changes to the PATH variable.

#### vscode
VSCode is a popular code editor that can be used for the development of the project. It is recommended to use VSCode for the development of the project, as it has a lot of useful features and extensions that can help with the development process. To install VSCode on the Target, follow these steps:

1. Navigate to the official website (https://code.visualstudio.com/download) and download the ARM64 version of the .deb file.
2. Install the .deb file by double-clicking on it and following the instructions.
  
Note if double-click does not work, you can also install the .deb files using the terminal with the following command:
```bash
sudo dpkg -i <file_name>
```

#### gitkraken
GitKraken is a popular git client that can be used for the development of the project. It is recommended to use GitKraken for the development of the project, as it has a lot of useful features and extensions that can help with the development process. To install GitKraken on the Target, follow these steps:

1. Navigate to the official website (https://www.gitkraken.com/download) and download the Linux ARM version of the .deb file.
2. Install the .deb file by double-clicking on it and following the instructions.

Note if double-click does not work, you can also install the .deb files using the terminal with the following command:
```bash
sudo dpkg -i <file_name>
```

## New Project Setup
When starting a new project (assuming this is a Python based project), here are the recommended steps to follow:
1. Create a new repository on GitHub (see [Create a new repository](#create-a-new-repository)).
2. Clone the repository on the Target (see [Clone the repository](#clone-the-repository)).
3. Setup a conda environment for the project (see [Setup a conda environment](#setup-a-conda-environment)).
4. Initial commit (see [Initial commit](#initial-commit)).
5. Use the example code from the ZED SDK as a starting point for the development of the project (see [Example codes](#example-codes)).
6. Create configuration files for the fusion project, i.e. multiple cameras (see [Configuration files for fusion projects](#configuration-files-for-fusion-projects)).


### Create a new repository
From GitHub of *LaboratoireELAN*'s account, create a new repository for the project. It is recommended to use a descriptive name for the repository. Also, if it is a python project, camel case is recommended for the name of the repository (e.g. `my_project_name` instead of `MyProjectName` or `My Project Name`). In any cases, avoid using spaces and special characters (e.g. `é`, `à`, ...) in the name of the repository as it can cause issues with some tools (e.g. git).

Then Fork the repository using the *LaboratoireELAN-ZED* account.

### Clone the repository
Using *GitKraken*, clone the repository on the Target. It is recommended to clone the repository in a dedicated folder for the project (e.g. `~/Programming/Projects/<project_name>`).

### Setup a conda environment
Assuming a conda client is installed on the Target (see [Miniconda](#miniconda)), open a terminal and follow these steps to create a new conda environment for the project:
```bash
conda create -n <env_name> 
conda activate <env_name>
conda install -c conda-forge pip 
```
For simplicity, `<env_name>` should match the name of the git project cloned in the previous step. This helps to easily identify which environment is associated with which project as the number of projects and environments grows. 

Once the environment is created, the step 3 of [Installing/updating Target drivers](#installingupdating-target-drivers) should be done to install the Python API of the ZED SDK in the conda environment. The file is supposed to be located in `~/Programming/SDK/<file_name>`.
It is important to have activated the environment BEFORE running the install file of the ZED SDK. 

### Initial commit
If not done already, clone the `https://github.com/LaboratoireELAN-ZED/python_project_template/` on the Target and copy the content of the project into the current project. NOTE: All files and folders should be copied except the `.git` folder.

If done using the *nautilus* GUI (the file explorer of Ubuntu), make sure to copy hidden files and folders (i.e. those starting with a dot, e.g. `.gitignore`). If you do not see them, you can press `Ctrl + H` to show hidden files and folders in the nautilus explorer.

Now open *vscode* and open the folder of the project. You should see all the files and folders of the project in the left panel of *vscode*. 
Open any *.py* file and on the bottom right of *vscode*, you shoulde see a Python version number. Click on it and select the Python interpreter of the conda environment created in the previous step. This will allow *vscode* to use the correct Python interpreter for the project, which is important for features like linting, debugging, and running the code.

Search for all occurrences of `template` in the project and replace them with the name of the current project.

You probably do not want to version configuration files (such as configuration files for the ZED SDK, or configuration files for the project itself). If that is the case, make sure to add those files to the `.gitignore` file of the project. The wildcard `*.json` can be useful in that regard. 

Finally, using *GitKraken*, stage all the changes, commit them with a descriptive message (e.g. "Initial commit") and push the changes to the remote repository on GitHub. 

### Example codes

The `zed-sdk` repository of *stereolabs* (forked in the *LaboratoireELAN-ZED*'s account) contains a lot of example code that can be used as a starting point for the development of the project. It is recommended to use these examples as a reference and to adapt them to the needs of the project.

### Configuration files for fusion projects

If using the fusion (i.e. multiple cameras), remember that a configuration file is needed. This file is used by the fusion algotithm to know which cameras are used and their relative positions. This file can be created by running the ZED360 calibration tool in the `ZED Tools` folder.

### Known issues

#### OpenGL error

If running the codes that uses openGL, you may run into a cryptic error related to OpenGL when launching the code. Most likely, this is because the OpenGL drivers are not properly installed on the Target. To solve this issue, you can install the `freeglut3-dev` package on the Target with the following command:

```bash
sudo apt install freeglut3-dev
```