"""End-to-end check of the real app, off-screen: python test_app.py (needs PySide6 + watchdog)."""
import os
import sys
import tempfile
import time
from pathlib import Path

HOME = Path(tempfile.mkdtemp()).resolve()
os.environ["HOME"] = os.environ["USERPROFILE"] = str(HOME)  # keep the test away from the real Downloads
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

import app  # noqa: E402
import login  # noqa: E402
import sorter  # noqa: E402


def wait_for(check, what, qapp, timeout=20):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        qapp.processEvents()
        if check():
            return
        time.sleep(0.05)
    raise AssertionError(f"timed out waiting for: {what}")


def answer_popup(choice):
    """Click a button on the next SortDrop question, the way a user would."""
    def click():
        box = QApplication.activeModalWidget()
        if not isinstance(box, QMessageBox):
            return QTimer.singleShot(50, click)
        next(b for b in box.buttons() if b.text() == choice).click()
    QTimer.singleShot(50, click)


def main():
    qapp = QApplication(sys.argv)
    downloads = HOME / "Downloads"
    downloads.mkdir()
    cfg = sorter.default_config()
    cfg["setup_done"] = True
    sorter.save_config(cfg)

    # Settings window builds without errors, first-run and normal.
    for first in (True, False):
        s = app.Settings(cfg, first)
        s.show()
        qapp.processEvents()
        s.close()

    a = app.App(qapp)
    assert a.watch == downloads

    # Known type: moved automatically, no question.
    (downloads / "report.pdf").write_text("pdf")
    wait_for(lambda: (downloads / "Documents" / "report.pdf").exists(), "pdf sorted into Documents", qapp)

    # Chrome-style: temp file renamed when done.
    (downloads / "photo.png.crdownload").write_text("png")
    time.sleep(0.5)
    assert (downloads / "photo.png.crdownload").exists(), "half-finished download was touched"
    (downloads / "photo.png.crdownload").rename(downloads / "photo.png")
    wait_for(lambda: (downloads / "Images" / "photo.png").exists(), "finished download sorted", qapp)

    # Unknown type: the user clicks "Move to Others"; the answer becomes a rule.
    answer_popup("Move to Others")
    (downloads / "book.epub").write_text("epub")
    wait_for(lambda: (downloads / "Others" / "book.epub").exists(), "epub moved to Others", qapp)
    assert sorter.load_config()["rules"][-1] == {"type": "ext", "value": ".epub",
                                                  "dest": str(downloads / "Others")}

    # Second file of that type: no question this time.
    (downloads / "novel.epub").write_text("epub")
    wait_for(lambda: (downloads / "Others" / "novel.epub").exists(), "rule reused without asking", qapp)

    # "Keep in Downloads" leaves it alone.
    answer_popup(app.LEAVE)
    (downloads / "data.xyz").write_text("x")
    wait_for(lambda: any(r["value"] == ".xyz" for r in a.cfg["rules"]), "keep answer saved", qapp)
    time.sleep(1)
    qapp.processEvents()
    assert (downloads / "data.xyz").exists()

    # Undo puts the last file back and the watcher does not grab it again.
    a.undo_last()
    assert (downloads / "novel.epub").exists()
    time.sleep(3)
    qapp.processEvents()
    assert (downloads / "novel.epub").exists(), "undone file was re-sorted"

    # Open at login writes and removes the startup entry.
    if sys.platform in ("darwin", "win32"):
        if sys.platform == "darwin":
            login.PLIST = HOME / "Library" / "LaunchAgents" / "test.plist"
        login.set_enabled(True, path="/Applications/SortDrop.app")
        assert login.enabled()
        login.set_enabled(False, path="/Applications/SortDrop.app")
        assert not login.enabled()

    a.quit()
    print("all app tests passed")


if __name__ == "__main__":
    main()
