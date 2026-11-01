"""Run: python test_sorter.py  (no extra libraries needed)."""
import tempfile
import threading
import time
from pathlib import Path

import sorter


def main():
    tmp = Path(tempfile.mkdtemp())
    sorter.LOG_FILE = tmp / "moves.log"
    watch = tmp / "Downloads"
    watch.mkdir()

    cfg = sorter.default_config()
    cfg["watch"] = str(watch)
    cfg["categories"]["Images"] = ""  # user chose "Leave in Downloads"
    cfg["rules"] = [sorter.make_rule("ext", "PDF", str(tmp / "AllPdfs")),
                    sorter.make_rule("name", "invoice", str(tmp / "Finance"))]

    # rules and categories
    assert cfg["rules"][0]["value"] == ".pdf"
    assert sorter.destination("Invoice_March.PDF", cfg) == str(tmp / "Finance")  # name beats ext
    assert sorter.destination("paper.pdf", cfg) == str(tmp / "AllPdfs")
    assert sorter.destination("notes.docx", cfg) == cfg["categories"]["Documents"]
    assert sorter.destination("photo.png", cfg) == ""
    assert sorter.destination("book.epub", cfg) is None
    assert sorter.destination("README", cfg) is None
    assert sorter.others_dir(cfg) == str(watch / "Others")
    loop = dict(cfg, rules=[sorter.make_rule("ext", "mp3", str(watch))])
    assert sorter.destination("song.mp3", loop) == ""  # never "move" into the watched folder itself
    try:
        sorter.make_rule("ext", "  ", "")
        raise AssertionError("empty rule accepted")
    except ValueError:
        pass

    # config round-trip
    sorter.save_config(cfg, tmp / "c.json")
    assert sorter.load_config(tmp / "c.json") == cfg

    # ignore list
    (watch / "a.pdf.crdownload").write_text("x")
    (watch / ".DS_Store").write_text("x")
    (watch / "Documents").mkdir()
    (watch / "Documents" / "inner.pdf").write_text("x")
    assert sorter.should_ignore(watch / "a.pdf.crdownload", watch)
    assert sorter.should_ignore(watch / ".DS_Store", watch)
    assert sorter.should_ignore(watch / "Documents", watch)
    assert sorter.should_ignore(watch / "Documents" / "inner.pdf", watch)
    assert not sorter.should_ignore(watch / "fresh.pdf", watch)

    # duplicates never overwrite
    for _ in range(2):
        (watch / "report.pdf").write_text("data")
        sorter.move_file(watch / "report.pdf", tmp / "Out")
    assert {p.name for p in (tmp / "Out").iterdir()} == {"report.pdf", "report (1).pdf"}

    # undo puts it back, renaming if the name is taken again
    (watch / "report.pdf").write_text("new")
    back = sorter.unique_path(watch, "report.pdf")
    sorter.undo(tmp / "Out" / "report (1).pdf", back)
    assert back.name == "report (1).pdf" and back.exists()
    assert sorter.LOG_FILE.read_text().count("\n") == 3

    # waits while Firefox-style placeholder has a .part sibling, then settles
    ph = watch / "big.zip"
    ph.write_text("")
    part = watch / "big.zip.part"
    part.write_text("x")
    threading.Timer(0.3, part.unlink).start()
    t = time.monotonic()
    assert sorter.wait_until_stable(ph, interval=0.1)
    assert time.monotonic() - t >= 0.3
    assert not sorter.wait_until_stable(watch / "gone.zip", interval=0.1)

    print("all sorter tests passed")


if __name__ == "__main__":
    main()
