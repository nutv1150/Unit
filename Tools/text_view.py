"""Bounded file viewer and background atomic export for large tool results."""
from pathlib import Path
import os
import queue
import shutil
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from Tools.window_layout import fit_window

PAGE_CHARS = 64 * 1024


# หน้าที่: รัน callable ใน worker แล้วส่งผลหรือ error กลับ UI ผ่านการ poll
# ที่มา: Tools/system_check.py::open_window.refresh (เรียกตรง)
# ที่มา: Tools/text_view.py::save_async (เรียกตรง)
# ที่มา: Tools/text_view.py::open_text_view.show (เรียกตรง)
# ที่มาเพิ่มเติม: อีก 1 จุดเรียก/อ้างอิงในโปรเจกต์
# Input: parent (tkinter.Misc (widget ของ Tk/CustomTkinter)) — หน้าต่างหรือ widget ที่ผู้เรียกสร้างไว้
# Input: operation (Callable[[], Any]) — callable ที่ผู้เรียกลงทะเบียนไว้ให้เรียกต่อ
# Input: complete (Callable[[Any, Exception | None], None]) — callable ที่ผู้เรียกลงทะเบียนไว้ให้เรียกต่อ
def background(parent, operation, complete):
    results = queue.Queue(maxsize=1)
    # หน้าที่: เรียก operation และเก็บผลหรือ exception ลง queue สำหรับ UI
    # ที่มา: Tools/text_view.py::background (อ้างอิง/callback)
    # Input: ไม่มีพารามิเตอร์ที่ส่งเข้ามาโดยตรง
    # Closure: operation (Callable[[], Any]) — รับจาก scope background
    # Closure: results (queue.Queue) — รับจาก scope background
    def worker():
        try:
            results.put((operation(), None))
        except Exception as error:
            results.put((None, error))
    # หน้าที่: ตรวจ queue ตามรอบของ Tk แล้วเรียก completion callback เมื่อมีผล
    # ที่มา: Tools/text_view.py::background (อ้างอิง/callback)
    # Input: ไม่มีพารามิเตอร์ที่ส่งเข้ามาโดยตรง
    # Closure: complete (Callable[[Any, Exception | None], None]) — รับจาก scope background
    # Closure: parent (tkinter.Misc (widget ของ Tk/CustomTkinter)) — รับจาก scope background
    # Closure: results (queue.Queue) — รับจาก scope background
    def poll():
        try:
            if not parent.winfo_exists():
                return
            value, error = results.get_nowait()
        except queue.Empty:
            parent.after(40, poll)
            return
        except tk.TclError:
            return
        complete(value, error)
    threading.Thread(target=worker, daemon=True).start()
    parent.after(40, poll)


# หน้าที่: คัดลอกไฟล์หรือ bytes ผ่านไฟล์ชั่วคราวแล้วแทนที่ destination เมื่อสำเร็จ
# ที่มา: Tools/text_view.py::save_async.copy (เรียกตรง)
# Input: source (Path | bytes) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
# Input: destination (str | PathLike[str]) — path ที่ผู้เรียกส่งจากการเลือกไฟล์/config หรือค่าเริ่มต้นของฟังก์ชัน
def copy_atomic(source, destination):
    destination = Path(destination)
    if isinstance(source, Path) and source.resolve() == destination.resolve():
        raise ValueError('Choose a different path from the source file.')
    name = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix='.unit-export-', delete=False) as output:
            name = output.name
            if isinstance(source, Path):
                with source.open('rb') as incoming:
                    shutil.copyfileobj(incoming, output, 1024 * 1024)
            else:
                output.write(source)
            output.flush()
            os.fsync(output.fileno())
        os.replace(name, destination)
        name = None
    finally:
        if name:
            os.unlink(name)


# หน้าที่: บันทึก output เบื้องหลังและแจ้งผลผ่าน callback บน UI
# ที่มา: Tools/text_view.py::open_text_view.save (เรียกตรง)
# ที่มา: pages/data_hash.py::DataHashPage.save_raw_output (เรียกตรง)
# ที่มา: pages/file_inspection.py::ResultBox.save_full_output (เรียกตรง)
# ที่มาเพิ่มเติม: อีก 1 จุดเรียก/อ้างอิงในโปรเจกต์
# Input: parent (tkinter.Misc (widget ของ Tk/CustomTkinter)) — หน้าต่างหรือ widget ที่ผู้เรียกสร้างไว้
# Input: source (Path | bytes) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
# Input: destination (str | PathLike[str]) — path ที่ผู้เรียกส่งจากการเลือกไฟล์/config หรือค่าเริ่มต้นของฟังก์ชัน
# Input: on_done (Callable[[], None]) — callable ที่ผู้เรียกลงทะเบียนไว้ให้เรียกต่อ
# Input: owner (object (ใช้เก็บ reference ของเจ้าของทรัพยากร) | None) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
def save_async(parent, source, destination, on_done=None, owner=None):
    # หน้าที่: แจ้ง error การบันทึกหรือเรียก callback หลังบันทึกสำเร็จ
    # ที่มา: Tools/text_view.py::save_async (อ้างอิง/callback)
    # Input: _ (None (ผลของงานคัดลอก; ไม่ได้ใช้งาน)) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: error (Exception | None) — exception ที่ background จับจาก worker; None เมื่อสำเร็จ
    # Closure: on_done (Callable[[], None]) — รับจาก scope save_async
    # Closure: parent (tkinter.Misc (widget ของ Tk/CustomTkinter)) — รับจาก scope save_async
    def complete(_, error):
        if error:
            messagebox.showerror('Save output', str(error), parent=parent)
        elif on_done:
            on_done()
    # หน้าที่: รักษา reference ของเจ้าของไฟล์ชั่วคราวระหว่างคัดลอก output
    # ที่มา: Tools/text_view.py::save_async (อ้างอิง/callback)
    # Input: ไม่มีพารามิเตอร์ที่ส่งเข้ามาโดยตรง
    # Closure: destination (str | PathLike[str]) — รับจาก scope save_async
    # Closure: owner (object (ใช้เก็บ reference ของเจ้าของทรัพยากร) | None) — รับจาก scope save_async
    # Closure: source (Path | bytes) — รับจาก scope save_async
    def copy():
        # Keep a temporary source alive if its result panel is replaced meanwhile.
        retained_owner = owner
        copy_atomic(source, destination)
    background(parent, copy, complete)


# หน้าที่: เปิด viewer อ่านไฟล์ทีละหน้าโดยรักษาเจ้าของไฟล์ชั่วคราวไว้
# ที่มา: pages/data_hash.py::DataHashPage.view_full_output (เรียกตรง)
# ที่มา: pages/file_inspection.py::ResultBox.view_full_output (เรียกตรง)
# ที่มา: pages/gemini.py::GeminiPage.__init__ (เรียกตรง)
# ที่มาเพิ่มเติม: อีก 1 จุดเรียก/อ้างอิงในโปรเจกต์
# Input: parent (tkinter.Misc (widget ของ Tk/CustomTkinter)) — หน้าต่างหรือ widget ที่ผู้เรียกสร้างไว้
# Input: path (str | PathLike[str]) — path ที่ผู้เรียกส่งจากการเลือกไฟล์/config หรือค่าเริ่มต้นของฟังก์ชัน
# Input: owner (object (ใช้เก็บ reference ของเจ้าของทรัพยากร) | None) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
def open_text_view(parent, path, owner=None):
    source_owner = owner if owner is not None else path
    path = Path(path)
    win = ctk.CTkToplevel(parent)
    win._source_owner = source_owner
    win.title('Full output — paged view')
    fit_window(win, '1100x760')
    box = ctk.CTkTextbox(win, wrap='none')
    box.pack(fill='both', expand=True, padx=12, pady=12)
    bar = ctk.CTkFrame(win)
    bar.pack(fill='x', padx=12, pady=(0, 12))
    status = ctk.CTkLabel(bar, text='')
    status.pack(side='right', padx=10)
    cookies, current, busy = [0], [0], [False]
    # หน้าที่: เลือกหน้าข้อความและเริ่มโหลดข้อมูลเบื้องหลัง
    # ที่มา: Tools/text_view.py::open_text_view (เรียกตรง)
    # Input: index (int) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Closure: following (ctk.CTkButton) — รับจาก scope open_text_view
    # Closure: previous (ctk.CTkButton) — รับจาก scope open_text_view
    # Closure: status (ctk.CTkLabel) — รับจาก scope open_text_view
    # Closure: win (ctk.CTkToplevel) — รับจาก scope open_text_view
    def show(index):
        if busy[0] or index < 0 or index >= len(cookies):
            return
        busy[0] = True
        status.configure(text='Loading…')
        previous.configure(state='disabled')
        following.configure(state='disabled')
        cookie = cookies[index]
        # หน้าที่: อ่านช่วงข้อความจากตำแหน่ง cookie และตรวจว่ามีหน้าถัดไปหรือไม่
        # ที่มา: Tools/text_view.py::open_text_view.show (อ้างอิง/callback)
        # Input: ไม่มีพารามิเตอร์ที่ส่งเข้ามาโดยตรง
        # Closure: cookie (int) — รับจาก scope open_text_view.show
        # Closure: path (str | PathLike[str]) — รับจาก scope open_text_view
        def load():
            with path.open('r', encoding='utf-8', errors='replace', newline='') as stream:
                stream.seek(cookie)
                text = stream.read(PAGE_CHARS)
                next_cookie = stream.tell()
                has_next = bool(stream.read(1))
            return text, next_cookie, has_next
        # หน้าที่: นำผลการอ่านมาใส่ textbox และอัปเดตปุ่มเปลี่ยนหน้า
        # ที่มา: Tools/text_view.py::open_text_view.show (อ้างอิง/callback)
        # Input: value (tuple[str, int, bool] | None) — ผล load() จาก worker: (ข้อความหนึ่งหน้า, ตำแหน่งหน้าถัดไป, มีหน้าถัดไปหรือไม่)
        # Input: error (Exception | None) — exception ที่ background จับจาก worker; None เมื่อสำเร็จ
        # Closure: index (int) — รับจาก scope open_text_view.show
        # Closure: box (ctk.CTkTextbox) — รับจาก scope open_text_view
        # Closure: following (ctk.CTkButton) — รับจาก scope open_text_view
        # Closure: previous (ctk.CTkButton) — รับจาก scope open_text_view
        # Closure: status (ctk.CTkLabel) — รับจาก scope open_text_view
        def ready(value, error):
            busy[0] = False
            if error:
                status.configure(text=f'Cannot read output: {error}')
                return
            text, next_cookie, has_next = value
            current[0] = index
            if has_next and len(cookies) == index + 1:
                cookies.append(next_cookie)
            box.configure(state='normal')
            box.delete('1.0', 'end')
            box.insert('1.0', text)
            box.configure(state='disabled')
            previous.configure(state='normal' if index else 'disabled')
            following.configure(state='normal' if has_next else 'disabled')
            status.configure(text=f'Page {index + 1} · UTF-8 display; Save keeps exact bytes')
        background(win, load, ready)
    # หน้าที่: รับ destination จาก Save dialog แล้วบันทึกผลเต็มแบบ asynchronous
    # ที่มา: Tools/text_view.py::open_text_view (อ้างอิง/callback)
    # Input: ไม่มีพารามิเตอร์ที่ส่งเข้ามาโดยตรง
    # Closure: path (str | PathLike[str]) — รับจาก scope open_text_view
    # Closure: source_owner (object) — รับจาก scope open_text_view
    # Closure: win (ctk.CTkToplevel) — รับจาก scope open_text_view
    def save():
        destination = filedialog.asksaveasfilename(parent=win, title='Save complete output')
        if destination:
            save_async(win, path, destination, owner=source_owner)
    previous = ctk.CTkButton(bar, text='Previous', command=lambda: show(current[0] - 1))
    previous.pack(side='left', padx=4)
    following = ctk.CTkButton(bar, text='Next', command=lambda: show(current[0] + 1))
    following.pack(side='left', padx=4)
    ctk.CTkButton(bar, text='Save Full Output', command=save).pack(side='left', padx=4)
    show(0)
    return win
