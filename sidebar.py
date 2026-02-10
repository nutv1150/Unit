# ui/sidebar.py 777777777775555
import customtkinter as ctk

class Sidebar(ctk.CTkFrame):
    def __init__(self, master, callback):
        super().__init__(master, width=220, fg_color="#5f6475")
        self.callback = callback
        self.grid_rowconfigure(10, weight=1)
        
        # สร้างตัวแปรไว้เก็บ object ของปุ่มทั้งหมด
        self.buttons = {}

        title = ctk.CTkLabel(
            self,
            text="Unified Toolkit",
            text_color="white",
            font=("Arial", 16, "bold"),
        )
        title.grid(row=0, column=0, pady=20, padx=20)

        items = [
            "Dashboard",
            "Data Hashing",
            "File Inspection",
            "Pipeline",
            "Gemini CLI",
            "App Portal",
            "My Tools",
            "Challenge",
        ]

        for i, name in enumerate(items, start=1):
            btn = ctk.CTkButton(
                self,
                text=name,
                anchor="w",
                fg_color="transparent", # เริ่มต้นเป็นสีโปร่งใส
                text_color="white",
                hover_color="#4a4f60",
                command=lambda n=name: self.on_click(n),
            )
            btn.grid(row=i, column=0, sticky="ew", padx=10, pady=4)
            # เก็บปุ่มไว้ใน dictionary โดยใช้ชื่อเป็น key
            self.buttons[name] = btn

    def update_button_styles(self, selected_name):
        """ ฟังก์ชันสำหรับเปลี่ยนสีไฮไลท์ปุ่ม """
        for name, btn in self.buttons.items():
            if name == selected_name:
                # สีเมื่อถูกเลือก (เช่น สีน้ำเงินของ theme หรือสีที่คุณต้องการ)
                btn.configure(fg_color="#4a4f60") 
            else:
                # สีปกติเมื่อไม่ได้เลือก
                btn.configure(fg_color="transparent")

    def on_click(self, name):
        # เรียกใช้ฟังก์ชันไฮไลท์
        self.update_button_styles(name)
        
        # เงื่อนไขการสลับหน้าเดิมของคุณ
        if name in ["Data Hashing", "File Inspection", "Pipeline", "Gemini CLI"]:
            self.callback(name)