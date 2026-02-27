import re
import subprocess
from typing import List

from PyQt6.QtCore import QThread, pyqtSignal

from app.models.usb_device import UsbDevice


def _run(args: list[str], timeout: int = 20) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        for enc in ("utf-8", "cp1252"):
            try:
                return result.returncode, result.stdout.decode(enc).strip(), result.stderr.decode(enc).strip()
            except UnicodeDecodeError:
                continue
        return result.returncode, result.stdout.decode("utf-8", errors="replace").strip(), ""
    except FileNotFoundError:
        return -1, "", "usbipd.exe not found. Please install usbipd-win."
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out."


class ListUsbWorker(QThread):
    """Lists USB devices via `usbipd list`."""
    result = pyqtSignal(list)   # list[UsbDevice]
    error = pyqtSignal(str)

    def run(self):
        rc, stdout, stderr = _run(["usbipd.exe", "list"])
        if rc != 0 and not stdout:
            self.error.emit(stderr or "Failed to list USB devices.")
            return

        devices: List[UsbDevice] = []
        lines = stdout.splitlines()

        # Parse only the "Connected:" section
        in_connected_section = False
        header_found = False

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Check for section headers
            if stripped.lower().startswith("connected:"):
                in_connected_section = True
                header_found = False
                continue
            elif stripped.lower().startswith("persisted:"):
                # Stop parsing when we hit the Persisted section
                break

            # Look for the column header in the Connected section
            if in_connected_section and "BUSID" in stripped.upper() and "STATE" in stripped.upper():
                header_found = True
                continue

            # Parse device rows after the header
            if in_connected_section and header_found:
                # Split on 2+ spaces to handle spaces in device names
                parts = re.split(r"\s{2,}", stripped)
                if len(parts) >= 3:
                    busid = parts[0].strip()
                    # Skip if it's not a valid BUSID format (e.g., x-y)
                    if not re.match(r"^\d+-\d+", busid):
                        continue
                    # parts[1] is VID:PID, parts[2] is DEVICE, parts[3] is STATE
                    description = parts[2].strip() if len(parts) > 2 else parts[1].strip()
                    state = parts[3].strip() if len(parts) > 3 else "Unknown"
                    devices.append(UsbDevice(busid=busid, description=description, state=state))

        self.result.emit(devices)


class BindUsbWorker(QThread):
    """Binds a USB device via `usbipd bind --busid <id>`."""
    done = pyqtSignal(bool, str)

    def __init__(self, busid: str, force: bool = False, parent=None):
        super().__init__(parent)
        self.busid = busid
        self.force = force

    def run(self):
        args = ["usbipd.exe", "bind", "--busid", self.busid]
        if self.force:
            args.append("--force")
        rc, stdout, stderr = _run(args)
        msg = stdout or stderr
        if rc == 0:
            self.done.emit(True, f"Device {self.busid} bound successfully.")
        else:
            self.done.emit(False, msg or f"Failed to bind device {self.busid}.")


class AttachUsbWorker(QThread):
    """Attaches a USB device to WSL via `usbipd attach --wsl --busid <id>`."""
    done = pyqtSignal(bool, str)

    def __init__(self, busid: str, distro: str = "", parent=None):
        super().__init__(parent)
        self.busid = busid
        self.distro = distro

    def run(self):
        args = ["usbipd.exe", "attach", "--wsl", "--busid", self.busid]
        if self.distro:
            args += ["--distribution", self.distro]
        rc, stdout, stderr = _run(args)
        msg = stdout or stderr
        if rc == 0:
            self.done.emit(True, f"Device {self.busid} attached to WSL successfully.")
        else:
            self.done.emit(False, msg or f"Failed to attach device {self.busid}.")


class DetachUsbWorker(QThread):
    """Detaches a USB device from WSL via `usbipd detach --busid <id>`."""
    done = pyqtSignal(bool, str)

    def __init__(self, busid: str, parent=None):
        super().__init__(parent)
        self.busid = busid

    def run(self):
        rc, stdout, stderr = _run(["usbipd.exe", "detach", "--busid", self.busid])
        msg = stdout or stderr
        if rc == 0:
            self.done.emit(True, f"Device {self.busid} detached successfully.")
        else:
            self.done.emit(False, msg or f"Failed to detach device {self.busid}.")

