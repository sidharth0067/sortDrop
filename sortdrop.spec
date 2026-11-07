# Build the standalone app (bundles its own Python): pyinstaller --noconfirm sortdrop.spec
import sys

VERSION = "1.1.0"

a = Analysis(["app.py"], datas=[("assets", "assets")])
pyz = PYZ(a.pure)

if sys.platform == "darwin":
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="SortDrop", console=False,
              icon="assets/icon.png")
    coll = COLLECT(exe, a.binaries, a.datas, name="SortDrop")
    app = BUNDLE(coll, name="SortDrop.app", icon="assets/icon.png", bundle_identifier="com.sortdrop.app",
                 version=VERSION,
                 info_plist={"LSUIElement": True,  # menu-bar only, no Dock icon
                             "NSHighResolutionCapable": True,
                             "NSDownloadsFolderUsageDescription": "SortDrop moves new downloads into your folders."})
else:
    # One .exe, nothing to install.
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="SortDrop", console=False,
              icon="assets/icon.png", upx=False)
