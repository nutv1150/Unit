import customtkinter as ctk
from tkinterdnd2 import TkinterDnD  # 1. Import ไลบรารีสำหรับ Drag & Drop

from sidebar import Sidebar
from pages.data_hash import DataHashPage
from pages.file_inspection import FileInspectionPage
from pages.pipeline import PipelinePage
from pages.gemini import GeminiPage
from pages.dashboard import DashboardPage

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

# 2. เพิ่ม TkinterDnD.DnDWrapper เข้ามาสืบทอดร่วมกับ ctk.CTk
class UNITApp(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()

        # 3. บรรทัดนี้สำคัญมาก! เป็นการสั่งเปิดใช้งานระบบ Drag & Drop ของแอปหลัก
        self.TkdndVersion = TkinterDnD._require(self)

        self.title("Unified Toolkit")
        self.geometry("1200x720")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = Sidebar(self, self.switch_page)
        self.sidebar.grid(row=0, column=0, sticky="ns")

        self.container = ctk.CTkFrame(self, fg_color="#f5f6f8")
        self.container.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        # ---------------- จุดที่ 1: เพิ่ม Dashboard เข้าไประบบ Pages ----------------
        self.pages = {
            "Dashboard": DashboardPage(self.container),
            "Data Hashing": DataHashPage(self.container),
            "File Inspection": FileInspectionPage(self.container),
            "Pipeline": PipelinePage(self.container),
            "Gemini CLI": GeminiPage(self.container),
        }

        self.current_page = None
        
        # ---------------- จุดที่ 2: เปลี่ยนหน้าเริ่มต้นเป็น Dashboard ----------------
        self.switch_page("Dashboard")

    #  แก้ไขฟังก์ชันนี้ใหม่ทั้งหมด
    def switch_page(self, name):
        # 1. ปริ้นท์เช็คเลยว่า Sidebar ส่งคำว่าอะไรมา (ดูใน Terminal สีดำตอนรันโปรแกรม)
        print(f"[DEBUG] ปุ่มที่กดส่งค่ามาคือ: '{name}'")

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
                
            print(f"[DEBUG] เปลี่ยนหน้าสำเร็จ -> '{target_page_key}'")
        else:
            # ถ้ายังพังอีก มันจะปริ้นท์บอกชัดเจนเลยว่าหาไม่เจอ
            print(f"[ERROR] ❌ เปลี่ยนหน้าไม่ได้! ไม่พบ '{name}' ในระบบเลย")

    def send_to_hashing(self, text):
        # 1. สลับไปหน้า Data Hashing
        self.switch_page("Data Hashing")
        # 2. ใส่ข้อความลง input_box
        page = self.pages["Data Hashing"]
        page.input_box.delete("1.0", "end")
        page.input_box.insert("1.0", text)
        # 3. trigger process_data ทันที
        page.process_data()

if __name__ == "__main__":
    app = UNITApp()
    app.mainloop()