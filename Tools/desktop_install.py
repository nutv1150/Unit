"""Opt-in user-menu shortcut for the current extracted bundle; never use sudo."""
import os
from pathlib import Path
import sys
from Tools.app_paths import data_root
from Tools.app_icon import ICON_PATH


# หน้าที่: escape ค่าข้อความใน desktop entry และปฏิเสธ control character ที่ไม่รองรับ
# ที่มา: Tools/desktop_install.py::executable_value (เรียกตรง)
# ที่มา: Tools/desktop_install.py::install (เรียกตรง)
# Input: text (str | Path) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
def value(text):
    text = str(text)
    if any(c in text for c in '\r\n\x00'):
        raise ValueError('Unsupported control character in shortcut path')
    return text.replace('\\', '\\\\').replace('\t', '\\t')


# หน้าที่: quote path ของ executable ให้ใช้ในฟิลด์ Exec ของ desktop entry ได้
# ที่มา: Tools/desktop_install.py::install (เรียกตรง)
# Input: path (str | PathLike[str]) — path ที่ผู้เรียกส่งจากการเลือกไฟล์/config หรือค่าเริ่มต้นของฟังก์ชัน
def executable_value(path):
    text = str(path)
    if '=' in text:
        raise ValueError('Desktop executable paths cannot contain an equals sign')
    # Exec quoting, followed by desktop-entry string escaping (two layers).
    quoted = ''.join('\\'+c if c in '\\"`$' else c for c in text)
    return '"' + value(quoted.replace('%', '%%')) + '"'


# หน้าที่: ตรวจ bundle และสร้าง shortcut ของผู้ใช้โดยไม่เขียนทับ shortcut ที่ต่างจากเดิม
# ที่มา: Tools/desktop_install.py::main (เรียกตรง)
# Input: executable (str | PathLike[str]) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
# Input: icon (str | PathLike[str]) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
# Input: applications (str | PathLike[str]) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
# Input: working_directory (str | PathLike[str]) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
def install(executable, icon, applications, working_directory):
    executable, icon = Path(executable).resolve(), Path(icon).resolve()
    if not executable.is_file() or not icon.is_file():
        raise ValueError('Extract the entire UNIT folder before installing the shortcut')
    content = ('[Desktop Entry]\nType=Application\nVersion=1.0\nName=UNIT\n'
               'Comment=Unified security and CTF toolkit\n'
               f'Exec={executable_value(executable)}\nIcon={value(icon)}\n'
               f'Path={value(working_directory)}\nTerminal=false\nCategories=Utility;Development;\n')
    target = Path(applications) / 'unit-toolkit.desktop'
    if target.exists() or target.is_symlink():
        if not target.is_symlink() and target.read_text(encoding='utf-8') == content:
            return target
        raise FileExistsError(f'Shortcut already exists: {target}. Keep it, or remove it explicitly before installing a different build.')
    Path(working_directory).mkdir(parents=True, exist_ok=True, mode=0o700)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('x', encoding='utf-8') as stream:
        stream.write(content)
    return target


# หน้าที่: สร้าง desktop shortcut จาก executable ของ packaged app และ XDG data directory
# ที่มา: entry point ของ CLI/launcher; รับข้อมูลจาก command line หรือระบบ
# Input: ไม่มีพารามิเตอร์ที่ส่งเข้ามาโดยตรง
# อ่านภายใน: sys.executable (str), sys.frozen (bool), XDG_DATA_HOME (str | None) และ ICON_PATH (Path)
def main():
    if not getattr(sys, 'frozen', False):
        raise RuntimeError('Use --install-shortcut from the built UNIT executable')
    base = Path(os.environ.get('XDG_DATA_HOME', '')).expanduser()
    if not base.is_absolute():
        base = Path.home() / '.local/share'
    path = install(sys.executable, ICON_PATH, base/'applications', data_root()/'workspace')
    print(f'Shortcut created: {path}\nKeep the extracted UNIT folder in this location.')
    return 0
