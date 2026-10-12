# PyInstaller onedir specification for Linux builds.
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, copy_metadata

ROOT = Path(SPECPATH).parent
datas = [
    (str(ROOT / "packaging" / "defaults"), "defaults"),
    (str(ROOT / "packaging" / "unit.svg"), "."),
]
for package in ("customtkinter", "tkinterdnd2", "puremagic"):
    datas.extend(collect_data_files(package))
    datas.extend(copy_metadata(package))

a = Analysis(
    [str(ROOT / "packaging" / "launcher.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "customtkinter", "tkinterdnd2", "puremagic",
    ],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], [], [],
          name="UNIT", debug=False, bootloader_ignore_signals=False,
          strip=False, upx=False, console=True, exclude_binaries=True)
coll = COLLECT(exe, a.binaries, a.datas, name="UNIT", strip=False, upx=False)
