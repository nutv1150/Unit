import customtkinter as ctk
from tkinterdnd2 import TkinterDnD  # 1. Import ไลบรารีสำหรับ Drag & Drop

from sidebar import Sidebar
from pages.data_hash import DataHashPage
from pages.file_inspection import FileInspectionPage
from pages.pipeline import PipelinePage
from pages.gemini import GeminiPage
from pages.dashboard import DashboardPage
from pages.app_portal import AppPortalPage
from pages.my_tools import MyToolsPage
from pages.challenge import ChallengePage
from Tools.dashboard_store import DashboardStore
from Tools.solve_history import SolveHistoryStore
from Tools.window_layout import fit_window
from Tools.app_paths import initialize_user_data
from Tools.mousewheel import MouseWheelRouter
from Tools.app_icon import set_app_icon

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

# 2. เพิ่ม TkinterDnD.DnDWrapper เข้ามาสืบทอดร่วมกับ ctk.CTk
class UNITApp(ctk.CTk, TkinterDnD.DnDWrapper):
    # หน้าที่: สร้างหน้าต่างหลัก ระบบข้อมูล sidebar และหน้าเครื่องมือทั้งหมด
    # ที่มา: Tools/package_smoke.py::main (เรียกตรง)
    # ที่มา: app.py::<module> (เรียกตรง)
    # ที่มา: packaging/launcher.py::main (เรียกตรง)
    # ที่มาเพิ่มเติม: อีก 2 จุดเรียก/อ้างอิงในโปรเจกต์
    # Input: self (UNITApp) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def __init__(self):
        initialize_user_data()
        super().__init__()
        set_app_icon(self)
        self.mousewheel_router = MouseWheelRouter(self)

        # 3. บรรทัดนี้สำคัญมาก! เป็นการสั่งเปิดใช้งานระบบ Drag & Drop ของแอปหลัก
        self.TkdndVersion = TkinterDnD._require(self)

        self.title("Unified Toolkit")
        fit_window(self, "1360x820")
        self.configure(fg_color="#0D0D12")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = Sidebar(self, self.switch_page)
        self.sidebar.grid(row=0, column=0, sticky="ns")

        self.container = ctk.CTkFrame(self, fg_color="#0D0D12")
        self.container.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        # DashboardStore เป็นแหล่งข้อมูลกลางของกิจกรรมทุกหน้า
        # บันทึกข้ามการเปิด/ปิดโปรแกรมที่ ~/.unit/dashboard_state.json
        self.dashboard_store = DashboardStore()
        self.history_error = ''
        self.history_active = set()
        try:
            self.history_store = SolveHistoryStore()
        except Exception as error:
            self.history_store = None
            self.history_error = f'History unavailable: {error}'

        # ---------------- จุดที่ 1: เพิ่ม Dashboard เข้าไประบบ Pages ----------------
        self.pages = {
            "Dashboard": DashboardPage(self.container),
            "Data Hashing": DataHashPage(self.container),
            "File Inspection": FileInspectionPage(self.container),
            "Pipeline": PipelinePage(self.container),
            "Gemini CLI": GeminiPage(self.container),
            "App Portal": AppPortalPage(self.container),
            "My Tools": MyToolsPage(self.container, navigate_callback=self.navigate_to),
            "Challenge": ChallengePage(self.container),
        }

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.current_page = None
        
        # ---------------- จุดที่ 2: เปลี่ยนหน้าเริ่มต้นเป็น Dashboard ----------------
        self.switch_page("Dashboard")

    #  แก้ไขฟังก์ชันนี้ใหม่ทั้งหมด
    # หน้าที่: ซ่อนหน้าเดิมแล้วแสดงหน้าที่ชื่อตรงกัน พร้อมเรียก on_show และไฮไลต์ sidebar
    # ที่มา: Tools/package_smoke.py::main (เรียกตรง)
    # ที่มา: app.py::UNITApp.__init__ (อ้างอิง/callback)
    # ที่มา: app.py::UNITApp.__init__ (เรียกตรง)
    # ที่มาเพิ่มเติม: อีก 6 จุดเรียก/อ้างอิงในโปรเจกต์
    # Input: self (UNITApp) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: name (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def switch_page(self, name):
        # 1. ปริ้นท์เช็คเลยว่า Sidebar ส่งคำว่าอะไรมา (ดูใน Terminal สีดำตอนรันโปรแกรม)
        print(f"[DEBUG] Requested page: '{name}'")

        # 2. สั่งซ่อนทุกหน้าที่มี
        for page_name, page_frame in self.pages.items():
            page_frame.grid_forget()
        
        # 3. ค้นหาหน้าแบบ Case-insensitive (แปลงเป็นตัวเล็กให้หมดแล้วเทียบกัน)
        # วิธีนี้จะแก้ปัญหา "Dashboard" กับ "dashboard" ไม่ตรงกันได้ 100%
        target_page_key = None
        for key in self.pages.keys():
            if key.strip().lower() == name.strip().lower():
                target_page_key = key
                break
                
        # 4. โชว์หน้าที่หาเจอ
        if target_page_key:
            self.current_page = self.pages[target_page_key]
            self.current_page.grid(row=0, column=0, sticky="nsew")
            
            if hasattr(self.current_page, "on_show"):
                self.current_page.on_show()

            if hasattr(self, "sidebar"):
                self.sidebar.update_button_styles(target_page_key)
                
            print(f"[DEBUG] Switched page -> '{target_page_key}'")
        else:
            # ถ้ายังพังอีก มันจะปริ้นท์บอกชัดเจนเลยว่าหาไม่เจอ
            print(f"[ERROR] Cannot switch page: '{name}' was not found")

    # หน้าที่: เปิดหน้าและเลือก tool ย่อยหรือเพิ่ม Pipeline node ตามทางลัด My Tools
    # ที่มา: app.py::UNITApp.__init__ (อ้างอิง/callback)
    # ที่มา: tests/test_my_tools_catalog.py::NavigationTests.test_shortcuts_select_requested_tools (เรียกตรง)
    # ที่มา: tests/test_my_tools_catalog.py::NavigationTests.test_legacy_xor_shortcut_still_opens_xor_mask (เรียกตรง)
    # Input: self (UNITApp) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: name (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: sub (str | None) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: mode (str | None) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def navigate_to(self, name, sub=None, mode=None):
        """เปิดหน้าพร้อมเครื่องมือย่อย โดยไม่ launch โปรแกรมภายนอกทันที"""
        self.switch_page(name)
        page = self.pages.get(name)
        if page is None or sub is None:
            return
        if name == "Data Hashing":
            # ``XOR`` is retained for groups saved by older UNIT versions.
            selected_mode = mode or ("Bitwise" if sub == "XOR" else "Decode")
            selected_algo = "XOR Mask" if sub == "XOR" else sub
            page.set_mode(selected_mode)
            page.select_quick_algo(selected_algo)
        elif name == "File Inspection":
            page.tool_menu.set(sub)
            page.on_tool_change(sub)
        elif name == "Pipeline":
            page.add_tool_node(sub)
        elif name == "App Portal":
            page.search_var.set(sub)

    # หน้าที่: บันทึก timer ยกเลิกงานที่กำลังรัน ปิด History และทำลายหน้าต่างหลัก
    # ที่มา: Tools/package_smoke.py::main (เรียกตรง)
    # ที่มา: app.py::UNITApp.__init__ (อ้างอิง/callback)
    # Input: self (UNITApp) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def on_close(self):
        try:
            self.pages["Challenge"].save_before_close()
        except (OSError, ValueError) as error:
            self.switch_page("Challenge")
            self.pages["Challenge"].status.configure(text=f"Could not save timer before closing: {error}")
            return
        pipeline = self.pages.get("Pipeline")
        if pipeline is not None:
            pipeline.cancel_active_runs()
        gemini = self.pages.get("Gemini CLI")
        if gemini is not None:
            gemini.request_stop()
        if getattr(self, 'history_store', None) is not None:
            from Tools.history_hooks import finish
            for event_id in tuple(getattr(self, 'history_active', ())):
                finish(self, event_id, 'Failed', error='Application closed before the operation completed.')
            self.history_store.close()
        self.destroy()

    # หน้าที่: ส่งข้อความที่เลือกจากหน้าอื่นเข้า Data Hashing พร้อม reference ของ History
    # ที่มา: pages/file_inspection.py::ResultBox.send_selection (เรียกตรง)
    # ที่มา: pages/gemini.py::GeminiPage.send_selection_to_hashing (เรียกตรง)
    # ที่มา: pages/pipeline.py::PipelinePage.open_step_window.send_selected_to_hashing (เรียกตรง)
    # Input: self (UNITApp) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: text (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: source_history_id (str | None) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def send_to_hashing(self, text, source_history_id=None):
        # 1. สลับไปหน้า Data Hashing
        self.switch_page("Data Hashing")
        # 2. ใส่ข้อความลง input_box
        page = self.pages["Data Hashing"]
        page.current_file_path = None
        page.history_source = (text, source_history_id)
        page.input_box.delete("1.0", "end")
        page.input_box.insert("1.0", text)
        # 3. trigger process_data ทันที
        page.process_data()

    # หน้าที่: ส่งข้อความที่เลือกจากหน้าอื่นเข้าช่อง prompt ของ Gemini
    # ที่มา: pages/data_hash.py::DataHashPage.send_selection_to_gemini (เรียกตรง)
    # ที่มา: pages/file_inspection.py::ResultBox.send_selection_to_gemini (เรียกตรง)
    # ที่มา: pages/pipeline.py::PipelinePage.open_step_window.send_selected_to_gemini (เรียกตรง)
    # Input: self (UNITApp) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: text (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def send_to_gemini(self, text):
        # 1. สลับไปหน้า Gemini CLI
        self.switch_page("Gemini CLI")
        # 2. ใส่ข้อความลง input_field
        page = self.pages["Gemini CLI"]
        page.input_field.delete(0, "end")
        page.input_field.insert(0, text)
        # 3. trigger send_message ทันที (ถ้ายังไม่ได้ connect CLI จะโชว์คำเตือนให้เอง)
        page.send_message()

    # หน้าที่: ส่งข้อมูลกิจกรรมจากหน้าเครื่องมือให้ DashboardStore บันทึกและรีเฟรช Dashboard
    # ที่มา: pages/app_portal.py::AppPortalPage._record_activity (เรียกตรง)
    # ที่มา: pages/dashboard.py::DashboardPage.launch_favorite (เรียกตรง)
    # ที่มา: pages/data_hash.py::DataHashPage._record_activity (เรียกตรง)
    # ที่มาเพิ่มเติม: อีก 2 จุดเรียก/อ้างอิงในโปรเจกต์
    # Input: self (UNITApp) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: **event (dict[str, Any]) — keyword arguments เพิ่มเติมจากผู้เรียก ส่งต่อไปยัง API ภายใน
    def record_activity(self, **event):
        """ให้ทุกหน้าเขียนสถิติ Dashboard ผ่านจุดเดียวกัน"""
        try:
            return self.dashboard_store.record_event(**event)
        except Exception as error:
            print(f"[DASHBOARD] Could not record activity: {error}")
            return None

if __name__ == "__main__":
    app = UNITApp()
    app.mainloop()
