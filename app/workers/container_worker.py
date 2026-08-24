import json
import subprocess
from typing import List

from PyQt6.QtCore import QThread, pyqtSignal

from app.models.container import Container
from app.utils.logo_resolver import resolve_container_logo
from app.utils.wslc_locator import resolve_wslc_path


def _decode(raw: bytes) -> str:
    """Decode subprocess output trying several encodings."""
    for enc in ("utf-8", "utf-16-le", "utf-16", "cp1252"):
        try:
            return raw.decode(enc).strip()
        except (UnicodeDecodeError, ValueError):
            continue
    return raw.decode("utf-8", errors="replace").strip()


def _run_wslc(args: List[str], timeout: int = 30) -> tuple[int, str, str]:
    """Run a `wslc` command and return (returncode, stdout, stderr).

    Resolves the absolute path to ``wslc.exe`` so the call works even when the
    WSL directory is not on PATH.
    """
    wslc = resolve_wslc_path()
    if not wslc:
        return -1, "", "WSL container support (wslc.exe) is not available."
    try:
        result = subprocess.run(
            [wslc, *args],
            capture_output=True,
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return result.returncode, _decode(result.stdout), _decode(result.stderr)
    except FileNotFoundError:
        return -1, "", "wslc.exe not found."
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out."


class ListContainersWorker(QThread):
    """Lists all containers via `wslc list --all --format json`."""
    result = pyqtSignal(list)   # list[Container]
    error = pyqtSignal(str)

    def run(self):
        rc, stdout, stderr = _run_wslc(["list", "--all", "--format", "json"])
        if rc != 0 and not stdout:
            self.error.emit(stderr or "Failed to list containers.")
            return

        containers: List[Container] = []
        stdout = stdout.strip()
        if stdout:
            try:
                data = json.loads(stdout)
            except json.JSONDecodeError:
                # Some CLIs emit newline-delimited JSON objects.
                data = []
                for line in stdout.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            if isinstance(data, dict):
                data = [data]
            for entry in data:
                if not isinstance(entry, dict):
                    continue
                container = Container.from_json(entry)
                container.logo_path = resolve_container_logo(container.image)
                containers.append(container)
        self.result.emit(containers)


class ListSessionsWorker(QThread):
    """Lists active wslc sessions via `wslc system session list`.

    Emits a list of dicts: {"id", "creator_pid", "display_name", "is_elevated"}.
    There is no JSON output for this command, so the table is parsed. A session
    is treated as elevated when its display name contains "admin" (wslc names
    sessions e.g. ``wslc-cli-<user>`` vs ``wslc-cli-admin-<user>``).
    """
    result = pyqtSignal(list)

    def run(self):
        rc, stdout, stderr = _run_wslc(["system", "session", "list"])
        sessions = []
        if rc == 0 and stdout:
            for line in stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                # Skip header and informational lines.
                if line.lower().startswith("id") or line.startswith("["):
                    continue
                parts = line.split(None, 2)
                if len(parts) < 3 or not parts[0].isdigit():
                    continue
                display_name = parts[2].strip()
                sessions.append({
                    "id": parts[0],
                    "creator_pid": parts[1],
                    "display_name": display_name,
                    "is_elevated": "admin" in display_name.lower(),
                })
        self.result.emit(sessions)


class StartContainerWorker(QThread):
    """Starts a container via `wslc start <id>`."""
    done = pyqtSignal(bool, str)

    def __init__(self, container_id: str, name: str = "", parent=None):
        super().__init__(parent)
        self.container_id = container_id
        self.name = name or container_id

    def run(self):
        rc, stdout, stderr = _run_wslc(["start", self.container_id])
        if rc == 0:
            self.done.emit(True, f"'{self.name}' started.")
        else:
            self.done.emit(False, stderr or f"Failed to start '{self.name}'.")


class StopContainerWorker(QThread):
    """Stops a container via `wslc stop <id>`."""
    done = pyqtSignal(bool, str)

    def __init__(self, container_id: str, name: str = "", parent=None):
        super().__init__(parent)
        self.container_id = container_id
        self.name = name or container_id

    def run(self):
        rc, stdout, stderr = _run_wslc(["stop", self.container_id], timeout=60)
        if rc == 0:
            self.done.emit(True, f"'{self.name}' stopped.")
        else:
            self.done.emit(False, stderr or f"Failed to stop '{self.name}'.")


class RemoveContainerWorker(QThread):
    """Removes a container via `wslc remove [-f] <id>`."""
    done = pyqtSignal(bool, str)

    def __init__(self, container_id: str, name: str = "", force: bool = False, parent=None):
        super().__init__(parent)
        self.container_id = container_id
        self.name = name or container_id
        self.force = force

    def run(self):
        args = ["remove"]
        if self.force:
            args.append("-f")
        args.append(self.container_id)
        rc, stdout, stderr = _run_wslc(args, timeout=60)
        if rc == 0:
            self.done.emit(True, f"'{self.name}' removed.")
        else:
            self.done.emit(False, stderr or f"Failed to remove '{self.name}'.")


class InspectContainerWorker(QThread):
    """Fetches detailed info for a container via `wslc inspect <id>`."""
    result = pyqtSignal(str, dict)   # container_id, parsed detail dict
    error = pyqtSignal(str, str)     # container_id, message

    def __init__(self, container_id: str, parent=None):
        super().__init__(parent)
        self.container_id = container_id

    def run(self):
        rc, stdout, stderr = _run_wslc(
            ["inspect", "--type", "container", self.container_id]
        )
        if rc != 0 and not stdout:
            self.error.emit(self.container_id, stderr or "Failed to inspect container.")
            return
        try:
            data = json.loads(stdout) if stdout.strip() else {}
        except json.JSONDecodeError:
            self.error.emit(self.container_id, "Could not parse inspect output.")
            return
        if isinstance(data, list):
            data = data[0] if data else {}
        self.result.emit(self.container_id, data if isinstance(data, dict) else {})


class GetContainerLogsWorker(QThread):
    """Fetches container logs via `wslc logs -n <tail> <id>`."""
    result = pyqtSignal(str, str)    # container_id, logs text
    error = pyqtSignal(str, str)     # container_id, message

    def __init__(self, container_id: str, tail: int = 500, parent=None):
        super().__init__(parent)
        self.container_id = container_id
        self.tail = tail

    def run(self):
        rc, stdout, stderr = _run_wslc(
            ["logs", "-n", str(self.tail), self.container_id], timeout=60
        )
        if rc != 0 and not stdout:
            self.error.emit(self.container_id, stderr or "Failed to fetch logs.")
            return
        # wslc may emit logs on stderr as well; combine for completeness.
        text = stdout
        if stderr and stderr not in stdout:
            text = f"{stdout}\n{stderr}".strip() if stdout else stderr
        self.result.emit(self.container_id, text or "(no log output)")


class GetContainerStatsWorker(QThread):
    """Fetches a resource-usage snapshot via `wslc stats --format json <id>`.

    Best-effort: emits an empty dict on any failure so callers can silently
    skip the resource line.
    """
    result = pyqtSignal(str, dict)   # container_id, stats dict

    def __init__(self, container_id: str, parent=None):
        super().__init__(parent)
        self.container_id = container_id

    def run(self):
        rc, stdout, stderr = _run_wslc(
            ["stats", "--format", "json", self.container_id], timeout=20
        )
        stats: dict = {}
        if rc == 0 and stdout.strip():
            try:
                data = json.loads(stdout)
                if isinstance(data, list):
                    data = data[0] if data else {}
                if isinstance(data, dict):
                    stats = data
            except json.JSONDecodeError:
                stats = {}
        self.result.emit(self.container_id, stats)
