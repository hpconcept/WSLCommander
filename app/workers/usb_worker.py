import re
import subprocess
from typing import List

from PyQt6.QtCore import QThread, pyqtSignal

from app.models.usb_device import UsbDevice
from app.utils.elevation import run_or_elevate


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
        seen_busids: set[str] = set()
        lines = stdout.splitlines()

        # Parse both "Connected:" and "Persisted:" sections so devices that
        # move to Persisted after a detach are still visible in the table.
        in_section = False
        header_found = False

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Detect any recognised section header
            lower = stripped.lower()
            if lower.startswith("connected:") or lower.startswith("persisted:"):
                in_section = True
                header_found = False
                continue

            # Look for the column header row (BUSID … STATE)
            if in_section and "BUSID" in stripped.upper() and "STATE" in stripped.upper():
                header_found = True
                continue

            # Parse device rows after the header
            if in_section and header_found:
                # Split on 2+ spaces to handle spaces in device names
                parts = re.split(r"\s{2,}", stripped)
                if len(parts) >= 3:
                    busid = parts[0].strip()
                    # Skip if it's not a valid BUSID format (e.g., x-y)
                    if not re.match(r"^\d+-\d+", busid):
                        continue
                    # Avoid duplicates (same busid can appear in both sections)
                    if busid in seen_busids:
                        continue
                    seen_busids.add(busid)
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
        rc, stdout, stderr = run_or_elevate(args)
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


class UnbindUsbWorker(QThread):
    """Unbinds a USB device via `usbipd unbind --busid <id>`."""
    done = pyqtSignal(bool, str)

    def __init__(self, busid: str, parent=None):
        super().__init__(parent)
        self.busid = busid

    def run(self):
        rc, stdout, stderr = run_or_elevate(["usbipd.exe", "unbind", "--busid", self.busid])
        msg = stdout or stderr
        if rc == 0:
            self.done.emit(True, f"Device {self.busid} unbound successfully.")
        else:
            self.done.emit(False, msg or f"Failed to unbind device {self.busid}.")


class AutoAttachWorker(QThread):
    """Long-running worker that auto-attaches a USB device to WSL.

    Spawns ``usbipd attach --wsl --auto-attach`` as a child process and
    monitors it until :meth:`stop` is called or the process exits on its own.
    """
    started = pyqtSignal(str)   # busid
    stopped = pyqtSignal(str)   # busid
    error = pyqtSignal(str, str)  # busid, message

    def __init__(self, busid: str, distro: str = "", unplugged: bool = False, parent=None):
        super().__init__(parent)
        self.busid = busid
        self.distro = distro
        self.unplugged = unplugged
        self._process: subprocess.Popen | None = None
        self._stop_requested = False

    def run(self):
        args = ["usbipd.exe", "attach", "--wsl", "--auto-attach", "--busid", self.busid]
        if self.distro:
            args += ["--distribution", self.distro]
        if self.unplugged:
            args.append("--unplugged")
        try:
            self._process = subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except FileNotFoundError:
            self.error.emit(self.busid, "usbipd.exe not found. Please install usbipd-win.")
            return

        self.started.emit(self.busid)

        # Block until the process exits (or is killed via stop()).
        self._process.wait()

        if self._stop_requested:
            self.stopped.emit(self.busid)
        else:
            stderr = ""
            if self._process.stderr:
                raw = self._process.stderr.read()
                stderr = raw.decode("utf-8", errors="replace").strip() if raw else ""
            if self._process.returncode == 0:
                self.stopped.emit(self.busid)
            else:
                self.error.emit(
                    self.busid,
                    stderr or f"Auto-attach for {self.busid} exited with code {self._process.returncode}.",
                )

    def stop(self):
        """Terminate the auto-attach process."""
        self._stop_requested = True
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()


