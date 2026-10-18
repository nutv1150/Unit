"""Build a versioned, reproducible-ish Linux onedir artifact.

This script never installs dependencies and never replaces an existing output
directory.  PyInstaller is resolved from the interpreter running this script.
"""
from __future__ import annotations

import argparse
import platform
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile


ROOT = Path(__file__).resolve().parents[1]


# หน้าที่: อ่านเลขรุ่นจาก UNIT_VERSION หรือใช้ค่าเริ่มต้น
# ที่มา: packaging/build.py::build (เรียกตรง)
# Input: ไม่มีพารามิเตอร์ที่ส่งเข้ามาโดยตรง
# อ่านภายใน: UNIT_VERSION (str | None) จาก environment; fallback เป็นเลขรุ่นเริ่มต้น (str)
def _version() -> str:
    return os.environ.get("UNIT_VERSION", "0.1.0")


# หน้าที่: ตรวจเลขรุ่นให้ใช้เป็นชื่อไฟล์และโฟลเดอร์ได้อย่างปลอดภัย
# ที่มา: packaging/build.py::build (เรียกตรง)
# Input: version (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
def _safe_version(version: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,63}", version):
        raise ValueError("version must contain only safe filename characters")
    return version


# หน้าที่: เก็บเวอร์ชันแอป runtime ระบบ และ dependencies ลง manifest ของ bundle
# ที่มา: packaging/build.py::build (เรียกตรง)
# Input: out (Path) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
# Input: version (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
def _manifest(out: Path, version: str) -> None:
    packages = []
    for name in ("customtkinter", "tkinterdnd2", "puremagic", "PyInstaller"):
        try:
            from importlib.metadata import version as package_version
            packages.append({"name": name, "version": package_version(name)})
        except Exception:
            packages.append({"name": name, "version": "unavailable"})
    payload = {
        "application": "UNIT", "version": version,
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version.split()[0], "os": platform.system(),
        "machine": platform.machine(), "glibc": platform.libc_ver()[1] or None,
        "packages": packages,
    }
    (out / "manifest.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


# หน้าที่: สร้างแพ็กเกจ Linux x86_64 ด้วย PyInstaller และ archive ตามตัวเลือก
# ที่มา: packaging/build.py::main (เรียกตรง)
# Input: output_root (Path) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
# Input: version (str | None) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
# Input: archive (bool) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
def build(output_root: Path, version: str | None = None, archive: bool = True) -> Path:
    version = version or _version()
    version = _safe_version(version)
    if platform.system() != "Linux" or platform.machine().lower() not in {"x86_64", "amd64"}:
        raise RuntimeError("Linux x86_64 is required for this build")
    output_root = output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    target = output_root / f"UNIT-{version}-linux-x86_64"
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite existing build: {target}")
    spec = ROOT / "packaging" / "unit.spec"
    staging = output_root / f".build-dist-{version}-{os.getpid()}"
    workpath = output_root / f".build-work-{version}-{os.getpid()}"
    if staging.exists() or workpath.exists():
        raise FileExistsError(f"Refusing to overwrite staging directory: {staging}")
    staging.mkdir()
    build_env = dict(os.environ, PYINSTALLER_CONFIG_DIR=str(workpath / 'cache'))
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm",
                    "--distpath", str(staging),
                    "--workpath", str(workpath),
                    str(spec)], check=True, cwd=ROOT, env=build_env)
    generated = staging / "UNIT"
    if generated.exists():
        generated.rename(target)
    else:
        raise RuntimeError("PyInstaller did not produce the UNIT onedir directory")
    _manifest(target, version)
    shutil.copy2(ROOT / 'packaging/install-user.sh', target / 'install-user.sh')
    (target / 'install-user.sh').chmod(0o755)
    shutil.copy2(ROOT / 'docs/linux-package.md', target / 'README.md')
    for name in ('install_dependencies.sh', 'Install UNIT Dependencies.desktop'):
        shutil.copy2(ROOT / name, target / name)
        (target / name).chmod(0o755)
    shutil.copy2(ROOT / 'packaging/install_dependencies.py', target / 'install_dependencies.py')
    if archive:
        archive_path = output_root / f"UNIT-{version}-linux-x86_64.tar.gz"
        if archive_path.exists():
            raise FileExistsError(f"Refusing to overwrite archive: {archive_path}")
        with tarfile.open(archive_path, "x:gz", dereference=False) as tar:
            tar.add(target, arcname=target.name, recursive=True)
    shutil.rmtree(workpath, ignore_errors=True)
    shutil.rmtree(staging, ignore_errors=True)
    return target


# หน้าที่: อ่าน CLI arguments แล้วเรียก build พร้อมพิมพ์ path ผลลัพธ์
# ที่มา: packaging/build.py::<module> (เรียกตรง)
# Input: argv (list[str] | None) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build UNIT Linux onedir")
    parser.add_argument("--output-root", type=Path, default=ROOT / "dist")
    parser.add_argument("--version", default=None)
    parser.add_argument("--no-archive", action="store_true")
    args = parser.parse_args(argv)
    path = build(args.output_root, args.version, archive=not args.no_archive)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
