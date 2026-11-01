"""SortDrop: menu-bar/tray app that files new downloads into folders."""
import copy
import html
import sys
import threading
from pathlib import Path

from PySide6.QtCore import QLockFile, QObject, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMenu, QMessageBox, QPushButton, QSystemTrayIcon,
    QTableWidget, QTableWidgetItem, QVBoxLayout,
)
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

import login
import sorter

LEAVE = "Keep in Downloads"
ASSETS = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "assets"


def pretty(path):
    if not path:
        return LEAVE
    home = str(Path.home())
    return "~" + path[len(home):] if path.startswith(home) else path


def button(text, fn):
    b = QPushButton(text)
    b.clicked.connect(fn)
    return b


class Settings(QDialog):
    def __init__(self, cfg, first_run):
        super().__init__()
        self.setWindowTitle("SortDrop Settings")
        self.setWindowIcon(QIcon(str(ASSETS / "icon.png")))
        self.setWindowFlag(Qt.WindowStaysOnTopHint)
        self.cfg = copy.deepcopy(cfg)
        lay = QVBoxLayout(self)
        lay.setSpacing(14)

        head = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(QPixmap(str(ASSETS / "icon.png")).scaled(56, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        head.addWidget(logo)
        intro = QLabel(
            "<span style='font-size:20px; font-weight:600'>"
            + ("Welcome to SortDrop" if first_run else "SortDrop") + "</span><br>"
            "New downloads move to their folder as soon as they finish. "
            + ("Choose where each type should go, then click Save to start." if first_run else ""))
        intro.setWordWrap(True)
        head.addWidget(intro, 1)
        lay.addLayout(head)

        box = QGroupBox("Watching")
        row = QHBoxLayout(box)
        self.watch_label = QLabel(pretty(self.cfg["watch"]))
        row.addWidget(self.watch_label, 1)
        row.addWidget(button("Change…", self.pick_watch))
        lay.addWidget(box)

        box = QGroupBox("Where each type goes")
        grid, self.cat_labels = QGridLayout(box), {}
        for i, cat in enumerate(sorter.CATEGORIES):
            name = QLabel(f"<b>{cat}</b>")
            name.setToolTip(" ".join(sorted(sorter.CATEGORIES[cat])))
            self.cat_labels[cat] = QLabel()
            grid.addWidget(name, i, 0)
            grid.addWidget(self.cat_labels[cat], i, 1)
            grid.addWidget(button("Choose…", lambda _=False, c=cat: self.pick_cat(c)), i, 2)
            grid.addWidget(button(LEAVE, lambda _=False, c=cat: self.set_cat(c, "")), i, 3)
            self.set_cat(cat, self.cfg["categories"].get(cat, ""))
        self.others_note = QLabel()
        self.others_note.setWordWrap(True)
        grid.addWidget(self.others_note, len(sorter.CATEGORIES), 0, 1, 4)
        self.update_others_note()
        grid.setColumnStretch(1, 1)
        lay.addWidget(box)

        box = QGroupBox("Your rules (checked first; “name contains” beats “extension is”)")
        rules = QVBoxLayout(box)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["If", "Matches", "Move to"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setMinimumHeight(120)
        rules.addWidget(self.table)
        add = QHBoxLayout()
        self.kind = QComboBox()
        self.kind.addItems(["Extension is", "Name contains"])
        self.value = QLineEdit()
        self.value.setPlaceholderText(".epub   or   invoice")
        add.addWidget(self.kind)
        add.addWidget(self.value, 1)
        add.addWidget(button("Add rule…", self.add_rule))
        add.addWidget(button("Remove selected", self.remove_rule))
        rules.addLayout(add)
        self.refresh_rules()
        lay.addWidget(box)

        self.at_login = QCheckBox("Open SortDrop when I log in")
        self.at_login.setChecked(login.enabled() or (first_run and login.supported()))
        self.at_login.setEnabled(login.supported())
        if not login.supported():
            self.at_login.setToolTip("Available in the installed app.")
        lay.addWidget(self.at_login)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("Save and start" if first_run else "Save")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)
        self.resize(780, 720)

    def pick(self, title):
        # The native picker has a "New Folder" button, which covers "create a folder for this type".
        return QFileDialog.getExistingDirectory(self, title, self.cfg["watch"])

    def pick_watch(self):
        if d := self.pick("Folder to watch"):
            self.cfg["watch"] = d
            self.watch_label.setText(pretty(d))
            self.update_others_note()

    def update_others_note(self):
        self.others_note.setText(
            f"<b>Anything else</b>: SortDrop asks you, with “Move to Others” ({pretty(sorter.others_dir(self.cfg))}) "
            "as the quick choice.")

    def pick_cat(self, cat):
        if d := self.pick(f"Where should {cat} go?"):
            self.set_cat(cat, d)

    def set_cat(self, cat, d):
        self.cfg["categories"][cat] = d
        self.cat_labels[cat].setText(pretty(d))
        self.cat_labels[cat].setToolTip(d)

    def add_rule(self):
        try:
            rule = sorter.make_rule("ext" if self.kind.currentIndex() == 0 else "name", self.value.text(), "")
        except ValueError as e:
            QMessageBox.warning(self, "Rule", str(e))
            return
        if d := self.pick("Move matching files to…"):
            rule["dest"] = d
            self.cfg["rules"].append(rule)
            self.value.clear()
            self.refresh_rules()

    def remove_rule(self):
        for r in sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True):
            del self.cfg["rules"][r]
        self.refresh_rules()

    def refresh_rules(self):
        self.table.setRowCount(len(self.cfg["rules"]))
        for i, r in enumerate(self.cfg["rules"]):
            kind = "Extension is" if r["type"] == "ext" else "Name contains"
            for j, text in enumerate([kind, r["value"], pretty(r["dest"])]):
                self.table.setItem(i, j, QTableWidgetItem(text))
        self.table.resizeColumnsToContents()


class Handler(FileSystemEventHandler):
    def __init__(self, app):
        self.app = app

    def on_created(self, event):
        self.app.consider(event.src_path)

    def on_moved(self, event):  # browsers rename "x.pdf.crdownload" -> "x.pdf" when done
        self.app.consider(event.dest_path)


class App(QObject):
    ready = Signal(str)

    def __init__(self, qapp):
        super().__init__()
        self.qapp = qapp
        self.cfg = sorter.load_config()
        self.watch = Path(self.cfg["watch"]).expanduser().resolve()
        self.paused, self.asking = False, False
        self.busy, self.restored, self.pending = set(), set(), []
        self.history = []  # shortcut: undo covers this session only; persist it if that proves annoying
        self.observer = None
        self.ready.connect(self.handle, Qt.QueuedConnection)  # watcher threads -> GUI thread

        menu = QMenu()
        pause = menu.addAction("Pause sorting")
        pause.setCheckable(True)
        pause.toggled.connect(lambda on: setattr(self, "paused", on))
        menu.addAction("Sort existing files now", self.sort_existing)
        self.undo_action = menu.addAction("Undo last move", self.undo_last)
        self.undo_action.setEnabled(False)
        menu.addAction("Open watched folder", lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.watch))))
        menu.addSeparator()
        menu.addAction("Settings…", self.open_settings)
        menu.addAction("Quit SortDrop", self.quit)
        self.menu = menu  # keep a reference; the tray does not own it

        if sys.platform == "darwin":  # black template icon that macOS tints for light/dark menu bars
            icon = QIcon(str(ASSETS / "tray.png"))
            icon.setIsMask(True)
        else:
            icon = QIcon(str(ASSETS / "icon.png"))
        self.tray = QSystemTrayIcon(icon)
        self.tray.setToolTip("SortDrop")
        self.tray.setContextMenu(menu)
        self.tray.show()

        if self.cfg["setup_done"]:
            if login.enabled():
                login.set_enabled(True)  # refresh the path in case the app was moved
            self.start_watching()
        else:  # nothing moves until the user has confirmed where things go
            QTimer.singleShot(0, self.open_settings)

    def notify(self, text):
        self.tray.showMessage("SortDrop", text)

    def start_watching(self):
        if self.observer:
            self.observer.stop()  # no join: keeps the menu responsive
        self.watch = Path(self.cfg["watch"]).expanduser().resolve()  # real path, matches watcher events
        self.observer = Observer()
        self.observer.schedule(Handler(self), str(self.watch), recursive=False)
        self.observer.start()

    # Runs on the watcher thread; one waiter thread per file so a slow download never blocks the rest.
    def consider(self, p):
        path = Path(p)
        if self.paused or path in self.restored or path in self.busy or sorter.should_ignore(path, self.watch):
            return
        self.busy.add(path)
        threading.Thread(target=self.wait_then_sort, args=(path,), daemon=True).start()

    def wait_then_sort(self, path):
        if sorter.wait_until_stable(path):
            self.ready.emit(str(path))
        else:
            self.busy.discard(path)

    # Everything below runs on the GUI thread.
    def handle(self, p):
        if self.asking:  # one question at a time; the answer may already cover the queued files
            self.pending.append(p)
            return
        path = Path(p)
        try:
            self.sort(path)
        finally:
            self.busy.discard(path)
        self.drain()

    def drain(self):
        while self.pending and not self.asking:
            self.handle(self.pending.pop(0))

    def sort(self, path):
        if not path.exists():
            return
        dest = sorter.destination(path.name, self.cfg)
        if dest is None:
            dest = self.ask(path)
        if not dest:
            return
        try:
            target = sorter.move_file(path, dest)
        except OSError as e:  # e.g. file locked by antivirus on Windows
            self.notify(f"Couldn't move {path.name}: {e}")
            return
        self.history.append((path, target))
        self.undo_action.setText(f"Undo: {target.name} → {target.parent.name}")
        self.undo_action.setEnabled(True)

    def ask(self, path):
        ext = path.suffix.lower()
        box = QMessageBox(QMessageBox.Question, "SortDrop",
                          f"<b>{html.escape(path.name)}</b><br><br>"
                          + (f"Where should <b>{ext}</b> files go?" if ext else "Where should this file go?"))
        box.setIconPixmap(QPixmap(str(ASSETS / "icon.png")).scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        box.setWindowFlag(Qt.WindowStaysOnTopHint)
        others = box.addButton("Move to Others", QMessageBox.AcceptRole)
        choose = box.addButton("Choose folder…", QMessageBox.ActionRole)
        box.addButton(LEAVE, QMessageBox.RejectRole)
        box.setDefaultButton(others)
        always = QCheckBox(f"Always do this for {ext} files")
        always.setChecked(True)
        if ext:
            box.setCheckBox(always)
        self.asking = True
        try:
            box.exec()
            clicked = box.clickedButton()
            if clicked is others:
                dest = sorter.others_dir(self.cfg)
            elif clicked is choose:
                dest = QFileDialog.getExistingDirectory(None, f"Where should {ext or path.name} go?", str(self.watch))
            else:
                dest = ""
        finally:
            self.asking = False
        if ext and always.isChecked() and not (clicked is choose and not dest):  # cancelled picker saves nothing
            self.cfg["rules"].append(sorter.make_rule("ext", ext, dest))
            sorter.save_config(self.cfg)
        return dest

    def sort_existing(self):
        if not self.cfg["setup_done"]:
            self.open_settings()
            return
        for path in sorted(self.watch.iterdir()):
            if path not in self.busy and not sorter.should_ignore(path, self.watch) and not sorter.downloading(path):
                self.busy.add(path)
                self.handle(str(path))

    def undo_last(self):
        if not self.history:
            return
        src, target = self.history.pop()
        back = sorter.unique_path(src.parent, src.name)
        # Ignore watcher events for it for a few seconds (some systems report the move twice).
        self.restored.add(back)
        QTimer.singleShot(5000, lambda: self.restored.discard(back))
        try:
            sorter.undo(target, back)
            self.notify(f"Moved {back.name} back.")
        except OSError as e:
            self.notify(f"Couldn't undo: {e}")
        last = self.history[-1][1] if self.history else None
        self.undo_action.setText(f"Undo: {last.name} → {last.parent.name}" if last else "Undo last move")
        self.undo_action.setEnabled(bool(last))

    def open_settings(self):
        if self.asking:  # a question or Settings is already open
            return
        first_run = not self.cfg["setup_done"]
        dlg = Settings(self.cfg, first_run)
        self.asking = True  # hold new files until Settings closes, so a pop-up rule isn't overwritten by Save
        try:
            saved = dlg.exec()
        finally:
            self.asking = False
        if saved:
            watch_changed = dlg.cfg["watch"] != self.cfg["watch"]
            self.cfg = dlg.cfg
            self.cfg["setup_done"] = True
            sorter.save_config(self.cfg)
            if login.supported() and dlg.at_login.isChecked() != login.enabled():
                login.set_enabled(dlg.at_login.isChecked())
            if watch_changed or not self.observer:
                self.start_watching()
        elif first_run:
            self.notify("Not sorting yet. Open Settings from the SortDrop icon to finish setup.")
        self.drain()

    def quit(self):
        if self.observer:
            self.observer.stop()
        self.qapp.quit()


def main():
    qapp = QApplication(sys.argv)
    qapp.setApplicationName("SortDrop")
    qapp.setQuitOnLastWindowClosed(False)
    sorter.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(sorter.CONFIG_DIR / "sortdrop.lock"))
    if not lock.tryLock(100):  # two copies would both grab the same downloads
        QMessageBox.information(None, "SortDrop", "SortDrop is already running. Look for its icon in the menu bar (system tray on Windows).")
        return
    _app = App(qapp)
    sys.exit(qapp.exec())


if __name__ == "__main__":
    main()
