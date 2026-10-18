"""Optional GUI hooks: history failures must not change tool results."""
from tkinter import messagebox


# หน้าที่: เก็บสถานะ error ของ History และแจ้งเตือนเมื่อเป็นข้อความผิดพลาดใหม่
# ที่มา: Tools/history_hooks.py::begin (เรียกตรง)
# ที่มา: Tools/history_hooks.py::finish (เรียกตรง)
# ที่มา: Tools/history_hooks.py::attach_file (เรียกตรง)
# Input: root (tkinter.Misc (widget ของ Tk/CustomTkinter)) — หน้าต่างหรือ widget ที่ผู้เรียกสร้างไว้
# Input: error (Exception | str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
def _failed(root, error):
    message = str(error)
    first = getattr(root, '_history_notified_error', '') != message
    root.history_error = message
    if first:
        root._history_notified_error = message
        messagebox.showwarning('History unavailable',
                               'History could not be saved. Tool results are unaffected.\n' + message,
                               parent=root)


# หน้าที่: เริ่มบันทึก operation ลง History และติดตาม event ที่ยังทำงาน
# ที่มา: pages/data_hash.py::DataHashPage.process_data (เรียกตรง)
# ที่มา: pages/file_inspection.py::FileInspectionPage.start_analysis_thread (เรียกตรง)
# ที่มา: pages/pipeline.py::PipelinePage.open_step_window.run_tool (เรียกตรง)
# Input: root (tkinter.Misc (widget ของ Tk/CustomTkinter)) — หน้าต่างหรือ widget ที่ผู้เรียกสร้างไว้
# Input: **event (dict[str, Any]) — keyword arguments เพิ่มเติมจากผู้เรียก ส่งต่อไปยัง API ภายใน
def begin(root, **event):
    store = getattr(root, 'history_store', None)
    if store is None:
        if getattr(root, 'history_error', ''):
            _failed(root, root.history_error)
        return None
    try:
        event_id = store.begin(**event)
        if not hasattr(root, 'history_active'):
            root.history_active = set()
        root.history_active.add(event_id)
        root.history_error = ''
        root._history_notified_error = ''
        return event_id
    except Exception as error:
        _failed(root, error)
        return None


# หน้าที่: อัปเดตผล History และถอน event ออกจากรายการงานที่กำลังทำ
# ที่มา: app.py::UNITApp.on_close (เรียกตรง)
# ที่มา: pages/data_hash.py::DataHashPage._show_result (เรียกตรง)
# ที่มา: pages/data_hash.py::DataHashPage._job_done (เรียกตรง)
# ที่มาเพิ่มเติม: อีก 5 จุดเรียก/อ้างอิงในโปรเจกต์
# Input: root (tkinter.Misc (widget ของ Tk/CustomTkinter)) — หน้าต่างหรือ widget ที่ผู้เรียกสร้างไว้
# Input: event_id (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
# Input: status (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
# Input: **result (dict[str, Any]) — keyword arguments เพิ่มเติมจากผู้เรียก ส่งต่อไปยัง API ภายใน
def finish(root, event_id, status, **result):
    if not event_id or getattr(root, 'history_store', None) is None:
        return
    try:
        root.history_store.finish(event_id, status, **result)
        root.history_active.discard(event_id)
    except Exception as error:
        _failed(root, error)


# หน้าที่: เปิดหน้าต่าง History หรือปรับตัวกรองและแสดงหน้าต่างเดิม
# ที่มา: pages/dashboard.py::DashboardPage._build_header (เรียกตรง)
# ที่มา: pages/data_hash.py::DataHashPage.__init__ (เรียกตรง)
# ที่มา: pages/file_inspection.py::FileInspectionPage.__init__ (เรียกตรง)
# ที่มาเพิ่มเติม: อีก 1 จุดเรียก/อ้างอิงในโปรเจกต์
# Input: root (tkinter.Misc (widget ของ Tk/CustomTkinter)) — หน้าต่างหรือ widget ที่ผู้เรียกสร้างไว้
# Input: category (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
def open_history(root, category='All'):
    from pages.solve_history import HistoryWindow
    existing = getattr(root, '_history_window', None)
    if existing is not None and existing.winfo_exists():
        existing.set_category(category)
        existing.deiconify()
        existing.lift()
        return existing
    window = HistoryWindow(root, category)
    root._history_window = window
    return window


# หน้าที่: เพิ่ม path ของไฟล์ที่เลือกหรือบันทึกลง event เดิมโดยไม่อ่านเนื้อหาไฟล์
# ที่มา: pages/data_hash.py::DataHashPage.save_raw_output (เรียกตรง)
# ที่มา: pages/file_inspection.py::ResultBox.save_full_output (เรียกตรง)
# ที่มา: pages/pipeline.py::PipelinePage.open_step_window.browse_result_file (เรียกตรง)
# ที่มาเพิ่มเติม: อีก 1 จุดเรียก/อ้างอิงในโปรเจกต์
# Input: root (tkinter.Misc (widget ของ Tk/CustomTkinter)) — หน้าต่างหรือ widget ที่ผู้เรียกสร้างไว้
# Input: event_id (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
# Input: path (str | PathLike[str]) — path ที่ผู้เรียกส่งจากการเลือกไฟล์/config หรือค่าเริ่มต้นของฟังก์ชัน
def attach_file(root, event_id, path):
    """Record an explicit saved/selected file reference, never read its contents."""
    if not event_id or getattr(root, 'history_store', None) is None:
        return
    try:
        event = root.history_store.get_event(event_id)
        if event is not None:
            files = list(dict.fromkeys(event['files'] + [str(path)]))
            root.history_store.finish(event_id, event['status'], output_data=event['output'],
                                      error=event['error'], files=files)
    except Exception as error:
        _failed(root, error)
