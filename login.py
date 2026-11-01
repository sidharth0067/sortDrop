"""Open SortDrop at login: a LaunchAgent on macOS, a Run registry value on Windows."""
import plistlib
import sys
from pathlib import Path

LABEL = "com.sortdrop.app"
PLIST = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def supported():
    # Only the packaged app has a stable path to launch; `python app.py` does not.
    return getattr(sys, "frozen", False) and sys.platform in ("darwin", "win32")


def app_path():
    exe = Path(sys.executable)
    return str(exe.parents[2]) if sys.platform == "darwin" else str(exe)  # .app/Contents/MacOS/SortDrop -> .app


def enabled():
    if sys.platform == "darwin":
        return PLIST.exists()
    if sys.platform == "win32":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
                winreg.QueryValueEx(key, "SortDrop")
            return True
        except OSError:
            return False
    return False


def set_enabled(on, path=None):
    path = path or app_path()
    if sys.platform == "darwin":
        if on:
            PLIST.parent.mkdir(parents=True, exist_ok=True)
            PLIST.write_bytes(plistlib.dumps(
                {"Label": LABEL, "ProgramArguments": ["/usr/bin/open", "-a", path], "RunAtLoad": True}))
        else:
            PLIST.unlink(missing_ok=True)
    elif sys.platform == "win32":
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if on:
                winreg.SetValueEx(key, "SortDrop", 0, winreg.REG_SZ, f'"{path}"')
            else:
                try:
                    winreg.DeleteValue(key, "SortDrop")
                except FileNotFoundError:
                    pass
