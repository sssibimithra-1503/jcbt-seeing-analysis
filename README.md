# JCBT Seeing Analysis Pipeline

A Python-based pipeline for real-time seeing analysis and FWHM measurement at the Vainu Bappu Observatory (VBO). This tool automates data retrieval from a remote Windows server to a local Linux client, handles file conversion (SPE to FITS), and generates live plots.

## Prerequisites

* **Server (Data Source):** Windows PC with the source folder containing `.fits` or `.spe` files.
* **Client (Analysis):** Linux PC (e.g., Fedora/Ubuntu).
* **Software:**
    * cifs-utils (must be installed and running on the Linux PC).
    * `uv` (Python package manager) installed on the Linux client.

---

## 1. Network & File Sharing Setup

Before running the scripts, the data folder on the Windows machine must be mounted on the Linux client.

### Step 1: Configure Windows Sharing
1.  On the **Windows PC**, right-click the folder you wish to share.
2.  Navigate to **Properties** -> **Sharing** -> **Advanced Sharing**.
3.  Check the **Share this folder** option.
4.  Click **Apply** -> **OK**.
5.  *Note:* To find the IP address of the Windows machine, open Command Prompt (`cmd`) and run `ipconfig`.

### Step 2: Mount Folder on Linux
On your **Linux PC**, create the mount point (if it does not already exist):

```bash
sudo mkdir -p /mnt/telescope_remote
```
Mount the shared Windows folder using the `cifs` protocol:
```bash
sudo mount -t cifs //(Windows_IP)/(Shared_Folder_Name) /mnt/telescope_remote -o username=WIN_USER,password=WIN_PASS
```
- Replace `(Windows_IP)` and `(Shared_Folder_Name)` with your specific details.
- Replace `WIN_USER` and `WIN_PASS` with the Windows account credentials.

**To unmount the folder later:**
```bash
sudo umount /mnt/telescope_remote
```
---
## 2. Installation & Environment
This project uses `uv` for high-performance dependency management.

### Step 1: Verify uv Installation
Ensure `uv` is installed on your Linux machine:

```bash
uv --version
```

### Step 2: Initialize Project

If setting up the project for the first time:

```bash
# Create and enter the project directory
mkdir jcbt-seeing-analysis
cd jcbt-seeing-analysis

# Initialize uv and pin Python version
uv init
uv python pin 3.11  # Uses Python 3.11

# Create virtual environment
uv venv
```
### Step 3: Install Dependencies

Add required modules (e.g., `astropy`, `matplotlib`, `numpy`) using:

```bash
uv add module_name1 module_name2
```
### Step 4: Activate Environment

Before running any scripts, activate the virtual environment:

```bash
source .venv/bin/activate
```

## 3. Usage

This repository contains two versions of the analysis pipeline depending on the input file format available on the server.

**Select the Correct Version**
| Version | Input Format | Description |
| :--- | :--- | :--- |
| **Version 1 (v1)** | `.fits` | Use this when the server directory already contains pre-processed FITS files. |
| **Version 2 (v2)** | `.spe` | Use this when the server contains raw `.spe` files. This script handles SPE-to-FITS conversion automatically. |

**Running the Analysis**

Run the appropriate Python script for your data type:
```bash
python3 <script_name>.py
```
**Live Plotting**

To visualize the Full Width at Half Maximum (FWHM) in real-time, open a separate terminal, activate the environment, and run:

```bash
python3 plot_fwhm_v1.py
```

# Credits

**Developed by the Research Trainees of Vainu Bappu Observatory.**
