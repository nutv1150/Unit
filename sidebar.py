import customtkinter as ctk

class Sidebar(ctk.CTkFrame):
    def __init__(self, master, callback):
        super().__init__(master, width=220, fg_color="#5f6475")
        self.callback = callback
        self.grid_rowconfigure(10, weight=1)
        
        self.buttons = {}

        title = ctk.CTkLabel(
            self,
            text="Unified Toolkit",
            text_color="white",
            font=("Arial", 16, "bold"),
        )
        title.grid(row=0, column=0, pady=20, padx=20)

        items = [
            "Dashboard", "Data Hashing", "File Inspection", 
            "Pipeline", "Gemini CLI", "App Portal", "My Tools", "Challenge",
        ]

        for i, name in enumerate(items, start=1):
            btn = ctk.CTkButton(
                self,
                text=name,
                anchor="w",
                fg_color="transparent",
                text_color="white",
                hover_color="#4a4f60",
                command=lambda n=name: self.on_click(n),
            )
            btn.grid(row=i, column=0, sticky="ew", padx=10, pady=4)
            self.buttons[name] = btn

    def update_button_styles(self, selected_name):
        """ เปลี่ยนสีไฮไลท์ปุ่มตามชื่อหน้า """
        for name, btn in self.buttons.items():
            if name == selected_name:
                btn.configure(fg_color="#4a4f60") # สีเมื่อถูกเลือก
            else:
                btn.configure(fg_color="transparent")

    def on_click(self, name):
        # ไฮไลท์ปุ่มก่อน
        self.update_button_styles(name)
        
        # ⭐ แก้ไขแล้ว: เพิ่ม "Dashboard" เข้าไปในลิสต์หน้าต่างที่อนุญาตให้สลับได้
        if name in ["Dashboard", "Data Hashing", "File Inspection", "Pipeline", "Gemini CLI"]:
            self.callback(name)