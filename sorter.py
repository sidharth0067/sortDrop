"""Core sorting logic. No GUI here, so it can be tested on its own."""
import json
import shutil
import time
from pathlib import Path

CONFIG_DIR = Path.home() / ".sortdrop"
CONFIG_FILE = CONFIG_DIR / "config.json"
LOG_FILE = CONFIG_DIR / "moves.log"
OLD_CONFIG = Path.home() / ".downloadsorter" / "config.json"  # v1 (Download Sorter) settings
OTHERS = "Others"

# Browsers write these while a download is still running.
TEMP_EXTS = {".crdownload", ".part", ".partial", ".download", ".opdownload", ".tmp"}

CATEGORIES = {
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".md", ".xls", ".xlsx",
                  ".csv", ".ppt", ".pptx", ".pages", ".numbers", ".key"},
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".svg", ".bmp", ".tiff"},
    "Videos": {".mp4", ".mov", ".mkv", ".avi", ".webm"},
    "Audio": {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz"},
    "Installers": {".dmg", ".pkg", ".exe", ".msi"},
    "Code": {".py", ".js", ".ts", ".json", ".java", ".html", ".css", ".ipynb", ".sh"},
}


def default_config():
    watch = Path.home() / "Downloads"
    return {
        "watch": str(watch),
        "categories": {c: str(watch / c) for c in CATEGORIES},  # "" = leave in Downloads
        "rules": [],  # {"type": "ext"|"name", "value": ..., "dest": folder or ""}
        "setup_done": False,
        "palette": "route",  # one of theme.PALETTES (GoalWall's colours)
    }


def load_config(path=None):
    path = path or (CONFIG_FILE if CONFIG_FILE.exists() or not OLD_CONFIG.exists() else OLD_CONFIG)
    cfg = default_config()
    if path.exists():
        cfg.update(json.loads(path.read_text()))
    return cfg


def save_config(cfg, path=None):
    path = path or CONFIG_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg, indent=2))
    tmp.replace(path)  # atomic, so a crash mid-save never wipes the user's rules


def others_dir(cfg):
    """Unknown types go here when the user says so; it follows the watched folder."""
    return str(Path(cfg["watch"]).expanduser() / OTHERS)


def make_rule(kind, value, dest):
    value = value.strip()
    if not value:
        raise ValueError("Type something to match.")
    if kind == "ext":
        value = "." + value.lower().lstrip(".")
    return {"type": kind, "value": value, "dest": dest}


def destination(name, cfg):
    """Folder to move into, "" to leave it where it is, or None if unknown (ask the user)."""
    dest = _match(name, cfg)
    # A rule pointing at the watched folder itself would rename and re-sort the file forever.
    if dest and Path(dest).expanduser().resolve() == Path(cfg["watch"]).expanduser().resolve():
        return ""
    return dest


def _match(name, cfg):
    lower = name.lower()
    ext = Path(lower).suffix
    for kind in ("name", "ext"):  # name rules beat extension rules
        for r in cfg["rules"]:
            if r["type"] == kind and (r["value"].lower() in lower if kind == "name" else r["value"] == ext):
                return r["dest"]
    for cat, exts in CATEGORIES.items():
        if ext in exts:
            return cfg["categories"].get(cat, "")
    return None


def downloading(path):
    """Firefox and Chrome keep a sibling temp file (name.pdf.part) until the download is done."""
    return any(path.with_name(path.name + t).exists() for t in TEMP_EXTS)


def should_ignore(path, watch):
    return (
        path.parent.resolve() != Path(watch).resolve()  # only top-level files, not our sorted subfolders
        or path.name.startswith(".")
        or path.name.lower() == "desktop.ini"
        or path.suffix.lower() in TEMP_EXTS
        or path.is_dir()
    )


def wait_until_stable(path, interval=1.0, checks=2, timeout=3600):
    """True once the file stops growing; False if it vanished or never settled."""
    last, same, end = -1, 0, time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            size = path.stat().st_size
        except FileNotFoundError:
            return False
        same = same + 1 if size == last and not downloading(path) else 0
        if same >= checks:
            return True
        last = size
        time.sleep(interval)
    return False


def unique_path(folder, name):
    folder, name = Path(folder), Path(name)
    target, n = folder / name, 1
    while target.exists():
        target = folder / f"{name.stem} ({n}){name.suffix}"
        n += 1
    return target


def _move(src, target):
    # shortcut: tiny race if another program creates the same name between the check and the move; fine for a personal Downloads folder
    shutil.move(str(src), str(target))
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{src}\t{target}\n")
    return target


def move_file(src, dest_dir):
    dest_dir = Path(dest_dir).expanduser()
    dest_dir.mkdir(parents=True, exist_ok=True)
    return _move(src, unique_path(dest_dir, src.name))


def undo(target, back):
    """Move a sorted file back. Caller picks `back` (via unique_path) so it can ignore the event first."""
    return _move(target, back)
