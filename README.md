# WSL Commander

A modern Windows desktop application for managing your **Windows Subsystem for Linux (WSL2)** distributions — built with Python and PyQt6 Fluent Widgets.

---

## Features

- View all installed WSL distributions with live status and version info
- Launch a terminal for any distribution with a single click
- Set a distribution as the system default
- Stop a running distribution
- Remove a distribution
- Export a distribution to a `.tar` archive for backup or transfer
- Install new distributions from the official online catalogue
- Import a distribution from a `.tar` archive with a custom name and install location
- Share USB devices with WSL, including bind, unbind, attach, detach, and auto-attach workflows
- Browse USB devices in a sortable table with color-coded device states
- Use a modern Fluent Design UI with automatic light/dark theme support

## What's New in v1.1.0

- Added an inline **Install** button directly on the selected distribution card in the install catalogue.
- Improved USB device visibility with color-coded state labels.
- Added a sortable USB device table for easier browsing.
- Added USB **Auto-Attach** support, including optional handling for unplugged devices.
- Added automatic UAC elevation for USB bind and unbind operations when administrator rights are required.
- Included minor code cleanup and maintenance updates.

For a release-by-release history, see [`CHANGELOG.md`](./CHANGELOG.md). The release notes for `v1.1.0` are available in [`docs/release-notes-v1.1.0.md`](./docs/release-notes-v1.1.0.md).

---

## Screenshots

### Installed Distributions
![Distros Page](docs/screenshots/distros_page.png)

### Install / Import a Distribution
![Install Page](docs/screenshots/install_page.png)

### USB Device Management
![USB Page](docs/screenshots/usb_page.png)

---

## Requirements

- Windows 10 or Windows 11 with WSL2 enabled
- [usbipd-win](https://github.com/dorssel/usbipd-win) *(optional — required for USB sharing functionality)*

### Enable WSL2 (if not already set up)

Open an elevated PowerShell and run:

```powershell
wsl --install
```

Restart your machine before launching WSL Commander.

### Install usbipd-win (for USB sharing)

USB device sharing requires [usbipd-win](https://github.com/dorssel/usbipd-win). Install it via `winget`:

```powershell
winget install usbipd
```

Or download the installer from the [usbipd-win releases page](https://github.com/dorssel/usbipd-win/releases).

> **Note:** Without `usbipd-win`, the USB page will still open but no devices will be listed and attach/detach actions will not be available.

> **Note:** Binding and unbinding USB devices may trigger a Windows UAC prompt if WSL Commander is not already running with administrator privileges.

---

## Running the Application

### Option 1 — Pre-built Executable (no Python required)

1. Download the latest release from the [GitHub Releases](https://github.com/hpconcept/WSLCommander/releases) page.
2. Extract the zip archive.
3. Run `WSLCommander.exe` from the extracted folder.

> **Note:** The executable is self-contained. No Python or additional dependencies need to be installed.

### Option 2 — Run from Source

**Prerequisites:** Python 3.10 or higher.

#### 1. Clone the repository

```bash
git clone https://github.com/hpconcept/WSLCommander.git
cd WSLCommander
```

#### 2. Create a virtual environment (recommended)

```powershell
python -m venv .venv
.venv\Scripts\activate
```

#### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

#### 4. Run

```powershell
python main.py
```

---

## Building the Executable

The repository includes a PyInstaller spec file for building the standalone executable yourself.

#### 1. Install dev dependencies

```powershell
pip install -r requirements-dev.txt
```

#### 2. Build

```powershell
pyinstaller WSLCommander.spec --noconfirm
```

The output will be placed in `dist\WSLCommander\WSLCommander.exe`.

---

## Project Structure

```
WSLCommander/
├── app/
│   ├── main_window.py        # Main application window
│   ├── models/               # Data models (Distro, UsbDevice)
│   ├── pages/                # UI pages (Distributions, Install, USB)
│   ├── utils/                # Helpers (logo resolution, elevation)
│   └── workers/              # Background QThread workers (WSL, USB)
├── assets/
│   ├── distros/              # Distribution logo images
│   └── icon/                 # Application icon
├── docs/
│   └── screenshots/          # Application screenshots
├── main.py                   # Entry point
├── requirements.txt          # Runtime dependencies
├── requirements-dev.txt      # Dev/build dependencies (includes PyInstaller)
├── WSLCommander.spec         # PyInstaller build spec
├── CHANGELOG.md              # Version history and release notes
├── LICENSE                   # MIT License
└── README.md
```

---

## Dependencies

### Runtime

| Package | License | Purpose |
|---|---|---|
| `PyQt6>=6.6.0` | GPLv3 / Commercial | Qt6 Python bindings |
| `PyQt6-Fluent-Widgets[full]>=1.6.0` | GPLv3 (free tier) | Fluent Design UI component library |

### Dev / Build

| Package | License | Purpose |
|---|---|---|
| `PyInstaller` | GPL + exception | Packaging into a standalone executable |

---

## License

The **source code** of WSL Commander is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

The **pre-built binary** bundles [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) and
[PyQt6-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets), both of which are licensed
under **GPLv3**. As a result, redistribution of the compiled binary is subject to the terms of the
[GNU General Public License v3](https://www.gnu.org/licenses/gpl-3.0.html).

If you require a license that is compatible with proprietary use, a commercial license for PyQt6 is
available from [Riverbank Computing](https://www.riverbankcomputing.com/software/pyqt/) and a
commercial license for PyQt-Fluent-Widgets is available at
[qfluentwidgets.com](https://qfluentwidgets.com/pages/pro).
