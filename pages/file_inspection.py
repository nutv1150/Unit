import customtkinter as ctk

class FileInspectionPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)

        # Header Section1235
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=15)
        ctk.CTkLabel(header_frame, text="📁 File Inspection", font=("Segoe UI", 20, "bold")).pack(side="left")

        # File Browser
        browse_frame = ctk.CTkFrame(self, fg_color="transparent")
        browse_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkButton(browse_frame, text="Browse", width=80, font=("Segoe UI", 12)).pack(side="left")
        ctk.CTkEntry(browse_frame, placeholder_text="File...........", font=("Segoe UI", 12)).pack(side="left", fill="x", expand=True, padx=10)

        # Tools Row (Steghide/Cat)
        tool_frame = ctk.CTkFrame(self, fg_color="transparent")
        tool_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkOptionMenu(tool_frame, values=["steghide", "cat"], width=150, font=("Segoe UI", 12)).pack(side="left")
        
        # Action Group (Password & Shake)
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkEntry(action_frame, placeholder_text="Pass...", width=150, font=("Segoe UI", 12)).pack(side="left")
        ctk.CTkButton(action_frame, text="Shake", width=80, font=("Segoe UI", 12)).pack(side="left", padx=10)

        # --- Warning Label (ปรับสีตามรูปภาพ) ---
        ctk.CTkLabel(
            self, 
            text="⚠️ Warning: Potential Executable Binary Detected", 
            text_color="#E67E22", # สีส้มตามรูป
            fg_color="#34495E",    # พื้นหลังเทาน้ำเงินตามรูป
            height=35,
            corner_radius=5, 
            font=("Segoe UI", 13, "bold")
        ).pack(fill="x", padx=20, pady=10)

        # --- Regex Pattern Selection (ปรับสีและฟอนต์ให้ดูง่ายขึ้น) ---
        regex_container = ctk.CTkFrame(self, fg_color="#2C3E50", corner_radius=8)
        regex_container.pack(fill="x", padx=20, pady=10)
        
        patterns = [
            r"FLAG\{.*?\}",
            r"(flag|ctf|picoCTF|HTB|THM)\{[^}]+\}",
            r"\{[0-9a-fA-F]{16,}\}(Hex)"
        ]
        
        for p in patterns:
            ctk.CTkCheckBox(
                regex_container, 
                text=p, 
                font=("Consolas", 12),      # ใช้ฟอนต์โปรแกรมเมอร์ให้ดูง่าย
                text_color="#95A5A6",       # สีเทาสว่างให้อ่านง่ายบนพื้นเข้ม
                checkbox_width=18,
                checkbox_height=18
            ).pack(anchor="w", padx=15, pady=6)

        # ปุ่มเพิ่ม Pattern แบบโปร่งใส
        ctk.CTkButton(
            regex_container, 
            text="+ Regular Pattern", 
            width=100, 
            height=25, 
            fg_color="transparent", 
            text_color="#3498db", 
            font=("Segoe UI", 12, "bold"),
            hover_color="#34495E"
        ).pack(anchor="w", padx=10, pady=(5, 10))

        # Output Terminal
        self.output = ctk.CTkTextbox(
            self, 
            height=200, 
            fg_color="#1A1A1A", 
            text_color="#00FF00", 
            font=("Consolas", 12)
        )
        self.output.pack(fill="both", expand=True, padx=20, pady=10)