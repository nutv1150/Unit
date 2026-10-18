"""Initial window sizes that leave room for desktop panels and decorations."""


# หน้าที่: ปรับขนาดหน้าต่างตามค่าที่ขอโดยไม่ให้ใหญ่เกินพื้นที่หน้าจอ
# ที่มา: Tools/system_check.py::open_window (เรียกตรง)
# ที่มา: Tools/text_view.py::open_text_view (เรียกตรง)
# ที่มา: app.py::UNITApp.__init__ (เรียกตรง)
# ที่มาเพิ่มเติม: อีก 15 จุดเรียก/อ้างอิงในโปรเจกต์
# Input: window (tkinter.Misc (widget ของ Tk/CustomTkinter)) — หน้าต่างหรือ widget ที่ผู้เรียกสร้างไว้
# Input: geometry (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
def fit_window(window, geometry):
    """Set a preferred logical size, capped to the screen; keep manual resizing."""
    width, height = (int(value) for value in geometry.split('x'))
    # CTk geometry is logical, while Tk screen dimensions are physical pixels.
    scaling = getattr(window, '_get_window_scaling', lambda: 1.0)()
    width = min(width, max(1, int((window.winfo_screenwidth() - 80) / scaling)))
    height = min(height, max(1, int((window.winfo_screenheight() - 100) / scaling)))
    window.geometry(f'{width}x{height}')
    return width, height
