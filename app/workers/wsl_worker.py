import re
import subprocess
from typing import List

from PyQt6.QtCore import QThread, pyqtSignal

from app.models.distro import Distro
from app.utils.logo_resolver import resolve_logo_path


def _run(args: list[str], timeout: int = 30) -> tuple[int, str, str]:
    """Run a subprocess and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        # WSL outputs UTF-16 LE on some systems; try multiple decodings
        for enc in ("utf-16-le", "utf-16", "utf-8", "cp1252"):
            try:
                stdout = result.stdout.decode(enc).strip()
                stderr = result.stderr.decode(enc).strip()
                return result.returncode, stdout, stderr
            except (UnicodeDecodeError, ValueError):
                continue
        return result.returncode, result.stdout.decode("utf-8", errors="replace").strip(), ""
    except FileNotFoundError:
        return -1, "", "wsl.exe not found"
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"


class ListInstalledWorker(QThread):
    """Lists all installed WSL distributions via `wsl --list --verbose`."""
    result = pyqtSignal(list)   # list[Distro]
    error = pyqtSignal(str)

    def run(self):
        rc, stdout, stderr = _run(["wsl.exe", "--list", "--verbose"])
        if rc != 0 and not stdout:
            self.error.emit(stderr or "Failed to list distributions")
            return

        distros: List[Distro] = []
        lines = stdout.splitlines()
        for line in lines[1:]:  # skip header
            # Remove BOM / non-printable chars
            line = re.sub(r"[^\x20-\x7E*]", "", line).strip()
            if not line:
                continue
            is_default = line.startswith("*")
            line = line.lstrip("* ").strip()
            parts = line.split()
            if len(parts) < 3:
                continue
            name, state, version = parts[0], parts[1], parts[2]
            distros.append(Distro(
                name=name,
                state=state,
                version=version,
                is_default=is_default,
                logo_path=resolve_logo_path(name),
            ))
        self.result.emit(distros)


class SetDefaultWorker(QThread):
    """Sets a WSL distribution as default."""
    done = pyqtSignal(bool, str)   # success, message

    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        self.name = name

    def run(self):
        rc, stdout, stderr = _run(["wsl.exe", "--set-default", self.name])
        if rc == 0:
            self.done.emit(True, f"'{self.name}' is now the default distribution.")
        else:
            self.done.emit(False, stderr or f"Failed to set '{self.name}' as default.")


class ListAvailableWorker(QThread):
    """Lists distributions available to install via `wsl --list --online`."""
    result = pyqtSignal(list)   # list[dict]  {'name': str, 'friendly_name': str}
    error = pyqtSignal(str)

    def run(self):
        rc, stdout, stderr = _run(["wsl.exe", "--list", "--online"], timeout=60)
        distros = []
        if rc != 0 and not stdout:
            self.error.emit(stderr or "Could not fetch online distribution list.")
            return

        lines = stdout.splitlines()
        # Skip header lines, then parse distro entries
        header_found = False
        for line in lines:
            clean = re.sub(r"[^\x20-\x7E]", "", line).strip()
            if not clean:
                continue

            # Skip intro text and find the header line
            if "NAME" in clean.upper() and "FRIENDLY" in clean.upper():
                header_found = True
                continue

            # Skip lines before the header
            if not header_found:
                continue

            # Parse distro entries (lines with two columns)
            parts = clean.split(None, 1)
            if len(parts) >= 1 and not clean.startswith(("The ", "Install ")):
                name = parts[0].strip()
                friendly = parts[1].strip() if len(parts) > 1 else name
                # Skip if it looks like a header or instruction
                if name and not name.startswith("-"):
                    distros.append({"name": name, "friendly_name": friendly})
        self.result.emit(distros)


class InstallDistroWorker(QThread):
    """Installs a WSL distribution via `wsl --install -d <name>`."""
    progress = pyqtSignal(str)
    done = pyqtSignal(bool, str)

    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        self.name = name

    def run(self):
        try:
            proc = subprocess.Popen(
                ["wsl.exe", "--install", "-d", self.name],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            for raw_line in proc.stdout:
                decoded = raw_line.decode("utf-8", errors="replace").rstrip()
                for enc in ("utf-8", "utf-16-le", "cp1252"):
                    try:
                        decoded = raw_line.decode(enc).rstrip()
                        break
                    except (UnicodeDecodeError, ValueError):
                        continue
                if decoded:
                    self.progress.emit(decoded)
            proc.wait()
            if proc.returncode == 0:
                self.done.emit(True, f"'{self.name}' installed successfully.")
            else:
                self.done.emit(False, f"Installation of '{self.name}' failed (exit {proc.returncode}).")
        except FileNotFoundError:
            self.done.emit(False, "wsl.exe not found.")
        except Exception as e:
            self.done.emit(False, str(e))


class TerminateDistroWorker(QThread):
    """Terminates a running WSL distribution."""
    done = pyqtSignal(bool, str)

    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        self.name = name

    def run(self):
        rc, stdout, stderr = _run(["wsl.exe", "--terminate", self.name])
        if rc == 0:
            self.done.emit(True, f"'{self.name}' terminated.")
        else:
            self.done.emit(False, stderr or f"Failed to terminate '{self.name}'.")


class UnregisterDistroWorker(QThread):
    """Unregisters (removes) a WSL distribution."""
    done = pyqtSignal(bool, str)

    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        self.name = name

    def run(self):
        rc, stdout, stderr = _run(["wsl.exe", "--unregister", self.name])
        if rc == 0:
            self.done.emit(True, f"'{self.name}' unregistered.")
        else:
            self.done.emit(False, stderr or f"Failed to unregister '{self.name}'.")


class LaunchDistroTerminalWorker(QThread):
    """Launches a terminal for a WSL distribution."""
    done = pyqtSignal(bool, str)

    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        self.name = name

    def run(self):
        try:
            # Launch a WSL terminal for the distribution, starting in the home directory
            subprocess.Popen(
                ["wsl.exe", "-d", self.name, "--", "bash", "-c", "cd ~ && exec bash -l"],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
            self.done.emit(True, f"Opened terminal for '{self.name}'.")
        except FileNotFoundError:
            self.done.emit(False, "wsl.exe not found.")
        except Exception as e:
            self.done.emit(False, str(e))


class LaunchInstallTerminalWorker(QThread):
    """Launches a terminal with the WSL install command."""
    done = pyqtSignal(bool, str)

    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        self.name = name

    def run(self):
        try:
            # Launch PowerShell with the install command
            cmd = f"wsl.exe --install -d {self.name}; pause"
            subprocess.Popen(
                ["powershell.exe", "-Command", cmd],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
            self.done.emit(True, f"Launched installer for '{self.name}' in a new terminal.")
        except FileNotFoundError:
            self.done.emit(False, "PowerShell not found.")
        except Exception as e:
            self.done.emit(False, str(e))


class ExportDistroWorker(QThread):
    """Exports a WSL distribution to a .tar file via `wsl --export`."""
    done = pyqtSignal(bool, str)

    def __init__(self, name: str, export_path: str, parent=None):
        super().__init__(parent)
        self.name = name
        self.export_path = export_path

    def run(self):
        rc, stdout, stderr = _run(
            ["wsl.exe", "--export", self.name, self.export_path],
            timeout=600,
        )
        if rc == 0:
            self.done.emit(True, f"'{self.name}' exported successfully to:\n{self.export_path}")
        else:
            self.done.emit(False, stderr or f"Failed to export '{self.name}'.")


class ImportDistroWorker(QThread):
    """Imports a WSL distribution from a .tar file via `wsl --import`."""
    done = pyqtSignal(bool, str)

    def __init__(self, name: str, install_dir: str, tar_path: str, parent=None):
        super().__init__(parent)
        self.name = name
        self.install_dir = install_dir
        self.tar_path = tar_path

    def run(self):
        import os
        os.makedirs(self.install_dir, exist_ok=True)
        rc, stdout, stderr = _run(
            ["wsl.exe", "--import", self.name, self.install_dir, self.tar_path],
            timeout=600,
        )
        if rc == 0:
            self.done.emit(True, f"'{self.name}' imported successfully.")
        else:
            self.done.emit(False, stderr or f"Failed to import '{self.name}'.")


