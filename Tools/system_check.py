"""Read-only optional tool discovery. Never run or install a discovered tool."""
import json
import shlex
import shutil
from pathlib import Path
from Tools.app_paths import RESOURCE_ROOT, writable_path


# หน้าที่: ตรวจ executables ใน PATH จากรายการหลักและ Pipeline config แล้วสร้างรายงาน
# ที่มา: Tools/system_check.py::main (เรียกตรง)
# ที่มา: Tools/system_check.py::open_window.refresh (อ้างอิง/callback)
# Input: ไม่มีพารามิเตอร์ที่ส่งเข้ามาโดยตรง
# อ่านภายใน: PATH (str) จาก environment และ Pipeline/custom_tools.json (dict หลัง parse JSON)
def report():
    path = writable_path('Pipeline/custom_tools.json')
    if not path.exists():
        path = RESOURCE_ROOT / 'defaults/Pipeline/custom_tools.json'
    if not path.exists():
        path = RESOURCE_ROOT / 'packaging/defaults/Pipeline/custom_tools.json'
    required = {'file', 'exiftool', 'zsteg', 'gemini', 'node', 'x-terminal-emulator',
                'bash', 'wireshark', 'ghidra', 'nmap', 'hashcat', 'burpsuite', 'msfconsole'}
    problems = []
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        from Pipeline.pipeline_engine import PipelineEngine
        PipelineEngine.validate_tools(data)
        for rows in data.values():
            for tool in rows:
                required.add(shlex.split(tool['command'])[0])
    except (OSError, ValueError, TypeError, KeyError, IndexError) as error:
        problems.append(f'Cannot inspect Pipeline configuration: {error}')
    lines = ['UNIT — SYSTEM CHECK', '',
             'Local codec/hash tools are included. External tools below are optional.',
             'FOUND means executable is on PATH, not that all features/version/auth work.',
             'Missing tools affect only the operations that use them. Nothing is installed.', '']
    for command in sorted(required):
        location = shutil.which(command)
        lines.append(f'{"FOUND  " if location else "MISSING"}  {command}' + (f'  {location}' if location else ''))
    lines.extend(['', f'User data: {writable_path(".")}', *problems])
    return '\n'.join(lines)


# หน้าที่: พิมพ์รายงาน System Check ทาง stdout
# ที่มา: entry point ของ CLI/launcher; รับข้อมูลจาก command line หรือระบบ
# Input: ไม่มีพารามิเตอร์ที่ส่งเข้ามาโดยตรง
# อ่านภายใน: report() (str) จากการตรวจ PATH/config ของโปรแกรม
def main():
    print(report())
    return 0


# หน้าที่: เปิดหน้าต่างแสดง System Check พร้อมปุ่มรีเฟรช
# ที่มา: pages/dashboard.py::DashboardPage._build_header (เรียกตรง)
# Input: parent (tkinter.Misc (widget ของ Tk/CustomTkinter)) — หน้าต่างหรือ widget ที่ผู้เรียกสร้างไว้
def open_window(parent):
    import customtkinter as ctk
    from Tools.text_view import background
    from Tools.window_layout import fit_window
    win = ctk.CTkToplevel(parent)
    win.title('UNIT — System Check')
    fit_window(win, '1000x700')
    box = ctk.CTkTextbox(win, wrap='none')
    box.pack(fill='both', expand=True, padx=15, pady=15)
    # หน้าที่: เริ่มงานตรวจ executables เบื้องหลังและปิดปุ่มชั่วคราว
    # ที่มา: Tools/system_check.py::open_window (เรียกตรง)
    # ที่มา: Tools/system_check.py::open_window (อ้างอิง/callback)
    # Input: ไม่มีพารามิเตอร์ที่ส่งเข้ามาโดยตรง
    # Closure: button (ctk.CTkButton) — รับจาก scope open_window
    # Closure: win (ctk.CTkToplevel) — รับจาก scope open_window
    def refresh():
        button.configure(state='disabled')
        # หน้าที่: นำรายงานหรือ error จากงานเบื้องหลังมาแสดงและเปิดปุ่มอีกครั้ง
        # ที่มา: Tools/system_check.py::open_window.refresh (อ้างอิง/callback)
        # Input: value (str | None) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
        # Input: error (Exception | None) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
        # Closure: box (ctk.CTkTextbox) — รับจาก scope open_window
        # Closure: button (ctk.CTkButton) — รับจาก scope open_window
        def done(value, error):
            box.configure(state='normal')
            box.delete('1.0', 'end')
            box.insert('1.0', str(error) if error else value)
            box.configure(state='disabled')
            button.configure(state='normal')
        background(win, report, done)
    button = ctk.CTkButton(win, text='Refresh', command=refresh)
    button.pack(pady=(0, 15))
    refresh()
    return win
