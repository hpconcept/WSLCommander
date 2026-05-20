import ctypes
import ctypes.wintypes
import shutil
import subprocess


# ── Win32 constants ──────────────────────────────────────────────────────────

_SEE_MASK_NOCLOSEPROCESS = 0x00000040
_SW_HIDE = 0
_INFINITE = 0xFFFFFFFF


# ── Win32 structures ────────────────────────────────────────────────────────


class _SHELLEXECUTEINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.wintypes.DWORD),
        ("fMask", ctypes.c_ulong),
        ("hwnd", ctypes.wintypes.HANDLE),
        ("lpVerb", ctypes.c_wchar_p),
        ("lpFile", ctypes.c_wchar_p),
        ("lpParameters", ctypes.c_wchar_p),
        ("lpDirectory", ctypes.c_wchar_p),
        ("nShow", ctypes.c_int),
        ("hInstApp", ctypes.wintypes.HINSTANCE),
        ("lpIDList", ctypes.c_void_p),
        ("lpClass", ctypes.c_wchar_p),
        ("hkeyClass", ctypes.wintypes.HKEY),
        ("dwHotKey", ctypes.wintypes.DWORD),
        ("hIconOrMonitor", ctypes.wintypes.HANDLE),
        ("hProcess", ctypes.wintypes.HANDLE),
    ]


# ── Public helpers ──────────────────────────────────────────────────────────


def is_admin() -> bool:
    """Return *True* if the current process has administrator privileges."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except OSError:
        return False


def run_elevated(args: list[str], timeout_ms: int = 30000) -> tuple[int, str]:
    """Run *args* with a UAC elevation prompt (``runas`` verb).

    Returns ``(exit_code, error_message)``.  stdout / stderr are **not**
    available from elevated processes; success is inferred from exit code 0.
    """
    exe = shutil.which(args[0])
    if exe is None:
        return -1, f"{args[0]} not found. Please install usbipd-win."
    params = subprocess.list2cmdline(args[1:])

    sei = _SHELLEXECUTEINFO()
    sei.cbSize = ctypes.sizeof(sei)
    sei.fMask = _SEE_MASK_NOCLOSEPROCESS
    sei.hwnd = None
    sei.lpVerb = "runas"
    sei.lpFile = exe
    sei.lpParameters = params
    sei.lpDirectory = None
    sei.nShow = _SW_HIDE

    if not ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(sei)):
        return -1, "Failed to launch elevated process (UAC cancelled or denied)."

    kernel32 = ctypes.windll.kernel32
    kernel32.WaitForSingleObject(sei.hProcess, ctypes.wintypes.DWORD(timeout_ms))
    exit_code = ctypes.wintypes.DWORD()
    kernel32.GetExitCodeProcess(sei.hProcess, ctypes.byref(exit_code))
    kernel32.CloseHandle(sei.hProcess)

    return exit_code.value, ""


def run_or_elevate(args: list[str], timeout: int = 20) -> tuple[int, str, str]:
    """Run *args*, requesting elevation only when the process lacks admin rights.

    When the application is already running as administrator the command is
    executed directly via :func:`subprocess.run` so that stdout and stderr
    are captured normally.  Otherwise :func:`run_elevated` is used which
    triggers a UAC prompt but cannot capture output.

    Returns ``(exit_code, stdout, stderr)`` — *stdout* and *stderr* will be
    empty strings when elevation was required.
    """
    if is_admin():
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            for enc in ("utf-8", "cp1252"):
                try:
                    return (
                        result.returncode,
                        result.stdout.decode(enc).strip(),
                        result.stderr.decode(enc).strip(),
                    )
                except UnicodeDecodeError:
                    continue
            return (
                result.returncode,
                result.stdout.decode("utf-8", errors="replace").strip(),
                "",
            )
        except FileNotFoundError:
            return -1, "", f"{args[0]} not found. Please install usbipd-win."
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out."

    rc, err = run_elevated(args)
    return rc, "", err
