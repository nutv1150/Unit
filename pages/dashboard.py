import customtkinter as ctk
import platform
import os

class DashboardPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        
        # พื้นหลังสีเทาอ่อนให้เข้ากับหน้าอื่นๆ
        self.configure(fg_color="#ececec")

        # สร้าง Scrollable Frame เผื่อหน้าจอเล็กจะได้เลื่อนลงได้
        self.main_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=30, pady=30)

        # ================= Header Section =================
        header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            header_frame, 
            text="Welcome to UNIT", 
            font=ctk.CTkFont(size=34, weight="bold"), 
            text_color="#2c3e50"
        ).pack(anchor="w", pady=(0, 5))

        ctk.CTkLabel(
            header_frame, 
            text="Unified Toolkit for Cybersecurity & CTF Operations", 
            font=ctk.CTkFont(size=16), 
            text_color="#7f8c8d"
        ).pack(anchor="w")

        # ================= System Info Section =================
        sys_frame = ctk.CTkFrame(self.main_frame, fg_color="white", corner_radius=10)
        sys_frame.pack(fill="x", pady=(0, 30))

        sys_info = f"System: {platform.system()} {platform.release()}  |  Workspace: {os.path.basename(os.getcwd())}"
        
        ctk.CTkLabel(
            sys_frame, 
            text="🚀 Ready for action", 
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#27ae60"
        ).pack(side="left", padx=20, pady=15)

        ctk.CTkLabel(
            sys_frame, 
            text=sys_info, 
            font=ctk.CTkFont(size=13),
            text_color="#95a5a6"
        ).pack(side="right", padx=20, pady=15)

        # ================= Features Grid Section =================
        ctk.CTkLabel(
            self.main_frame, 
            text="Quick Overview", 
            font=ctk.CTkFont(size=20, weight="bold"), 
            text_color="#2c3e50"
        ).pack(anchor="w", pady=(0, 15))

        self.grid_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.grid_frame.pack(fill="x")

        # ตั้งค่าให้ Grid แบ่งเป็น 2 คอลัมน์เท่าๆ กัน
        self.grid_frame.grid_columnconfigure(0, weight=1)
        self.grid_frame.grid_columnconfigure(1, weight=1)

        # ข้อมูลของการ์ดแต่ละใบ (หัวข้อ, รายละเอียด, สีแถบด้านบน)
        features = [
            ("Data Hashing & Encoding", "Encode, decode, and hash data easily. Supports Base64, Hex, and auto-detection.", "#3498db"),
            ("File Inspection", "Analyze file types, extract metadata, and find hidden flags using steganography tools.", "#e74c3c"),
            ("Pipeline Builder", "Create automated workflows. Chain multiple commands together with a drag-and-drop interface.", "#2eb85c"),
            ("Gemini CLI", "Your AI Cybersecurity Assistant. Get help solving challenges, writing scripts, and explaining code.", "#9b59b6")
        ]

        # วนลูปสร้างการ์ด
        for i, (title, desc, color) in enumerate(features):
            row = i // 2
            col = i % 2

            card = ctk.CTkFrame(self.grid_frame, fg_color="white", corner_radius=8)
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

            # แถบสีตกแต่งด้านบนการ์ด
            ctk.CTkFrame(card, fg_color=color, height=4, corner_radius=0).pack(fill="x", side="top")

            ctk.CTkLabel(
                card, 
                text=title, 
                font=ctk.CTkFont(size=16, weight="bold"), 
                text_color="#333333"
            ).pack(anchor="w", padx=20, pady=(15, 5))

            ctk.CTkLabel(
                card, 
                text=desc, 
                font=ctk.CTkFont(size=13), 
                text_color="#7f8c8d", 
                wraplength=350, 
                justify="left"
            ).pack(anchor="w", padx=20, pady=(0, 20))