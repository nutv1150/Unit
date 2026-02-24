import customtkinter as ctk
from sidebar import Sidebar
from pages.data_hash import DataHashPage
from pages.file_inspection import FileInspectionPage
from pages.pipeline import PipelinePage
from pages.gemini import GeminiPage

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

class UNITApp(ctk.CTk):
    def __init__(self):
        super().__init__()

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

        self.pages = {
            "Data Hashing": DataHashPage(self.container),
            "File Inspection": FileInspectionPage(self.container),
            "Pipeline": PipelinePage(self.container),
            "Gemini CLI": GeminiPage(self.container),
        }

        self.current_page = None
        self.switch_page("Data Hashing")

    def switch_page(self, name):
        if self.current_page:
            self.current_page.grid_forget()
        
        if name in self.pages:
            self.current_page = self.pages[name]
            self.current_page.grid(row=0, column=0, sticky="nsew")
            
            # ⭐ สั่งให้ Sidebar ไฮไลท์ปุ่มให้ตรงกับชื่อหน้าที่เปลี่ยนไป
            if hasattr(self, "sidebar"):
                self.sidebar.update_button_styles(name)

    def send_to_hashing(self, text):
        """ ฟังก์ชันกลางสำหรับส่งข้อมูลข้ามหน้า """
        # 1. เปลี่ยนหน้าไปยัง Data Hashing (ซึ่งจะเปลี่ยนไฮไลท์ Sidebar ให้อัตโนมัติ)
        self.switch_page("Data Hashing")
        
        # 2. นำข้อมูลไปวางในช่อง Input
        hashing_page = self.pages["Data Hashing"]
        hashing_page.input_box.delete("1.0", "end")
        hashing_page.input_box.insert("1.0", text)
        
        # 3. รันการประมวลผลทันที
        if hasattr(hashing_page, "process_data"):
            hashing_page.process_data()

if __name__ == "__main__":
    app = UNITApp()
    app.mainloop()