"""Shared dark colors and CTk-only dialogs for personal workspace pages."""
import customtkinter as ctk
from Tools.window_layout import fit_window

# ใช้โทนเข้มคงที่เหมือน Dashboard แม้ appearance mode ของแอปเป็น Light
THEME_COLORS = {
    'bg': '#0D0D12', 'panel': '#15151E',
    'card': '#1E1E2A', 'border': '#333344',
    'text': '#E6EAF3', 'muted': '#8892B0',
    'accent': '#378ADD', 'green': '#1D9E75',
    'amber': '#EF9F27', 'purple': '#7F77DD',
    'error': '#FF5378', 'hover': '#20304A',
}
COLORS = {name: THEME_COLORS[key] for name, key in
          [('blue', 'accent'), ('green', 'green'), ('amber', 'amber'), ('purple', 'purple')]}
FONT = ('Consolas', 12)
ENTRY_STYLE = dict(fg_color='#0A0A0F', border_color=THEME_COLORS['border'],
                   text_color=THEME_COLORS['text'], placeholder_text_color=THEME_COLORS['muted'])


# หน้าที่: สร้าง label ธีมร่วมโดยรับตัวเลือก widget เพิ่มเติมจากผู้เรียก
# ที่มา: pages/challenge.py::ChallengePage._open_editor (เรียกตรง)
# ที่มา: pages/challenge.py::ChallengePage._build_ui (เรียกตรง)
# ที่มา: pages/challenge.py::ChallengePage._render_rows (เรียกตรง)
# ที่มาเพิ่มเติม: อีก 4 จุดเรียก/อ้างอิงในโปรเจกต์
# Input: parent (tkinter.Misc (widget ของ Tk/CustomTkinter)) — หน้าต่างหรือ widget ที่ผู้เรียกสร้างไว้
# Input: text (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
# Input: **kwargs (dict[str, Any]) — keyword options ของ widget ที่ผู้เรียกส่งเพิ่มมา
def label(parent, text, **kwargs):
    return ctk.CTkLabel(parent, text=text, font=FONT, text_color=THEME_COLORS['text'], **kwargs)


# หน้าที่: สร้างหน้าต่างย่อยพร้อม title/geometry และการจัดตำแหน่งมาตรฐาน
# ที่มา: pages/challenge.py::ChallengePage._open_editor (เรียกตรง)
# ที่มา: pages/my_tools.py::MyToolsPage._open_dialog (เรียกตรง)
# Input: parent (tkinter.Misc (widget ของ Tk/CustomTkinter)) — หน้าต่างหรือ widget ที่ผู้เรียกสร้างไว้
# Input: title (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
# Input: geometry (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
def dialog(parent, title, geometry='460x600'):
    window = ctk.CTkToplevel(parent)
    window.title(title)
    fit_window(window, geometry)
    window.configure(fg_color=THEME_COLORS['bg'])
    window.transient(parent.winfo_toplevel())
    window.after(100, lambda: window.grab_set() if window.winfo_exists() else None)
    return window


class CTkMessagebox(ctk.CTkToplevel):
    """Small CTk-only confirmation, with no additional third-party dependency."""
    # หน้าที่: สร้างกล่องยืนยัน action พร้อมข้อความและ callback เมื่อผู้ใช้ยืนยัน
    # ที่มา: pages/challenge.py::ChallengePage._delete (เรียกตรง)
    # ที่มา: pages/my_tools.py::MyToolsPage._delete (เรียกตรง)
    # Input: self (CTkMessagebox) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: parent (tkinter.Misc (widget ของ Tk/CustomTkinter)) — หน้าต่างหรือ widget ที่ผู้เรียกสร้างไว้
    # Input: message (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: on_confirm (Callable[[], None]) — callable ที่ผู้เรียกลงทะเบียนไว้ให้เรียกต่อ
    def __init__(self, parent, message, on_confirm):
        super().__init__(parent)
        self.title('Confirm delete')
        fit_window(self, '460x210')
        self.configure(fg_color=THEME_COLORS['bg'])
        self.transient(parent.winfo_toplevel())
        previous_grab = parent.grab_current()
        # หน้าที่: ปล่อย grab และปิดกล่องยืนยันโดยไม่เรียก action
        # ที่มา: pages/workspace_ui.py::CTkMessagebox.__init__ (อ้างอิง/callback)
        # ที่มา: pages/workspace_ui.py::CTkMessagebox.__init__.confirm (เรียกตรง)
        # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
        # Closure: previous_grab (tkinter.Misc | None) — รับจาก scope CTkMessagebox.__init__
        # Closure: self (CTkMessagebox) — รับจาก scope CTkMessagebox.__init__
        def close():
            self.destroy()
            if previous_grab is not None and previous_grab.winfo_exists():
                previous_grab.grab_set()
        # หน้าที่: ปิดกล่องยืนยันแล้วเรียก on_confirm ที่ผู้เรียกส่งไว้
        # ที่มา: pages/workspace_ui.py::CTkMessagebox.__init__ (อ้างอิง/callback)
        # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
        # Closure: on_confirm (Callable[[], None]) — รับจาก scope CTkMessagebox.__init__
        def confirm():
            close()
            on_confirm()
        label(self, message, wraplength=350).pack(padx=20, pady=24)
        buttons = ctk.CTkFrame(self, fg_color='transparent')
        buttons.pack(padx=20, fill='x')
        ctk.CTkButton(buttons, text='Cancel', command=close).pack(side='left')
        ctk.CTkButton(buttons, text='Delete', fg_color=THEME_COLORS['error'], command=confirm).pack(side='right')
        self.protocol('WM_DELETE_WINDOW', close)
        self.after(100, lambda: self.grab_set() if self.winfo_exists() else None)
