import customtkinter as ctk

class Sidebar(ctk.CTkFrame):
    def __init__(self, master, callback):
        super().__init__(master, width=190, fg_color="#15151E", corner_radius=0)
        self.grid_columnconfigure(0, weight=1)
        self.callback = callback
        self.grid_rowconfigure(12, weight=1)
        
        self.buttons = {}

        title = ctk.CTkLabel(
            self,
            text=">_ UNIT",
            text_color="#00FFFF",
            font=("Consolas", 24, "bold"),
        )
        title.grid(row=0, column=0, pady=(26, 4), padx=20, sticky="w")
        ctk.CTkLabel(
            self, text="UNIFIED TOOLKIT", text_color="#8892B0",
            font=("Consolas", 10),
        ).grid(row=1, column=0, padx=20, pady=(0, 22), sticky="w")
        ctk.CTkFrame(self, height=1, fg_color="#333344").grid(
            row=2, column=0, sticky="ew", padx=16, pady=(0, 16)
        )

        items = [
            "Dashboard", "Data Hashing", "File Inspection", 
            "Pipeline", "Gemini CLI", "App Portal", "My Tools", "Challenge",
        ]

        for i, name in enumerate(items, start=3):
            btn = ctk.CTkButton(
                self,
                text=f"  {name}",
                height=38, width=158, corner_radius=5,
                font=("Consolas", 12),
                border_width=1, border_color="#15151E",
                anchor="w",
                fg_color="transparent",
                text_color="#8892B0",
                hover_color="#1E1E2A",
                command=lambda n=name: self.on_click(n),
            )
            btn.grid(row=i, column=0, sticky="ew", padx=12, pady=4)
            self.buttons[name] = btn

    def update_button_styles(self, selected_name):
        """ เปลี่ยนสีไฮไลท์ปุ่มตามชื่อหน้า """
        for name, btn in self.buttons.items():
            if name == selected_name:
                btn.configure(
                    fg_color="#093035", text_color="#00FFFF",
                    border_color="#00FFFF", hover_color="#104047",
                    font=("Consolas", 12, "bold"),
                )
            else:
                btn.configure(
                    fg_color="transparent", text_color="#8892B0",
                    border_color="#15151E", hover_color="#1E1E2A",
                    font=("Consolas", 12),
                )

    def on_click(self, name):
        # ไฮไลท์ปุ่มก่อน
        self.update_button_styles(name)
        
        # ⭐ ยิง callback ส่งชื่อหน้าไปให้ app.py จัดการเปลี่ยนหน้าได้เลย
        self.callback(name)