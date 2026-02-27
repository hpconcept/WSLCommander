# WSL Commander

A modern Windows desktop application for managing your **Windows Subsystem for Linux (WSL2)** distributions — built with Python and PyQt6 Fluent Widgets.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)
![License](https://img.shields.io/badge/Source%20Licence-MIT-green)
![Binary License](https://img.shields.io/badge/Binary%20Licence-GPLv3-orange)

---

## Features

- 📋 **View** all installed WSL distributions with live status and version info
- ▶️ **Launch** a terminal for any distribution with a single click
- ⭐ **Set** a distribution as the system default
- ⏹️ **Stop** a running distribution
- 🗑️ **Remove** a distribution
- 💾 **Export** a distribution to a `.tar` archive for backup or transfer
- 📦 **Install** new distributions from the official online catalogue
- 📂 **Import** a distribution from a `.tar` archive with a custom name and install location
- 🔌 **USB Sharing** — list connected USB devices and manage their attachment to WSL
- 🎨 Modern Fluent Design UI with automatic light/dark theme support

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

### Enable WSL2 (if not already set up)

Open an elevated PowerShell and run:

```powershell
wsl --install
```

Restart your machine before launching WSL Commander.

---

## Running the Application

### Option 1 — Pre-built Executable (no Python required)

1. Download the latest release from the [Releases](../../releases) page.
2. Extract the zip archive.
3. Run `WSLCommander.exe` from the extracted folder.

> **Note:** The executable is self-contained. No Python or additional dependencies need to be installed.

### Option 2 — Run from Source

**Prerequisites:** Python 3.10 or higher.

#### 1. Clone the repository

```bash
git clone https://github.com/yourusername/WSLCommander.git
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
│   ├── utils/                # Helpers (logo resolver)
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
└── README.md
```

---

## Dependencies

### Runtime

| Package | Licence | Purpose |
|---|---|---|
| `PyQt6>=6.6.0` | GPLv3 / Commercial | Qt6 Python bindings |
| `PyQt6-Fluent-Widgets[full]>=1.6.0` | GPLv3 (free tier) | Fluent Design UI component library |

### Dev / Build

| Package | Licence | Purpose |
|---|---|---|
| `PyInstaller` | GPL + exception | Packaging into a standalone executable |

---

## Licence

The **source code** of WSL Commander is licensed under the **MIT Licence** — see the [LICENSE](LICENSE) file for details.

The **pre-built binary** bundles [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) and
[PyQt6-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets), both of which are licensed
under **GPLv3**. As a result, redistribution of the compiled binary is subject to the terms of the
[GNU General Public License v3](https://www.gnu.org/licenses/gpl-3.0.html).

If you require a licence that is compatible with proprietary use, a commercial licence for PyQt6 is
available from [Riverbank Computing](https://www.riverbankcomputing.com/software/pyqt/) and a
commercial licence for PyQt-Fluent-Widgets is available at
[qfluentwidgets.com](https://qfluentwidgets.com/pages/pro).

