import customtkinter as ctk
import subprocess
import os

# ==========================================
# ธีมสีหลัก (Cyberpunk / Terminal)
# ==========================================
BG_COLOR = "#0D0D12"        
PANEL_COLOR = "#15151E"     
ACCENT_CYAN = "#00FFFF"     
ACCENT_GREEN = "#00FF41"    
TEXT_DIM = "#8892B0"        
ALERT_RED = "#FF3366"       

class AppPortalPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.configure(fg_color=BG_COLOR)
        
        # ฐานข้อมูลแอปพลิเคชัน (เพิ่ม/ลด/แก้ไข คำสั่งเปิดแอปได้ตรงนี้)
        # เคล็ดลับ: ถ้าแอปไหนไม่มี GUI ให้ครอบด้วย x-terminal-emulator -e "คำสั่ง"
        self.tools = [
            {"name": "Wireshark", "cmd": "wireshark", "desc": "Network Protocol Analyzer", "icon": "🦈"},
            {"name": "Burp Suite", "cmd": "burpsuite", "desc": "Web Vulnerability Scanner", "icon": "🕸️"},
            {"name": "Ghidra", "cmd": "ghidra", "desc": "Software Reverse Engineering", "icon": "🐉"},
            {"name": "Nmap", "cmd": "x-terminal-emulator -e 'nmap -h; bash'", "desc": "Network Mapper (CLI)", "icon": "🗺️"},
            {"name": "Metasploit", "cmd": "x-terminal-emulator -e 'msfconsole'", "desc": "Penetration Testing Framework", "icon": "Ⓜ️"},
            {"name": "Hashcat", "cmd": "x-terminal-emulator -e 'hashcat -h; bash'", "desc": "Advanced Password Recovery", "icon": "🔐"},
            {"name": "CyberChef", "cmd": "firefox https://gchq.github.io/CyberChef/", "desc": "The Cyber Swiss Army Knife", "icon": "👨‍🍳"},
            {"name": "Terminal", "cmd": "x-terminal-emulator", "desc": "Open a new root shell", "icon": "💻"}
        ]

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1) 

        # 1. Header (HUD Style)
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=30, pady=(20, 5))
        ctk.CTkLabel(header_frame, text=">_ APP_PORTAL :: [QUICK_LAUNCH]", font=("Consolas", 28, "bold"), text_color=ACCENT_CYAN).pack(side="left")

        # 2. Status Bar (แสดงสถานะการรันแอป)
        status_frame = ctk.CTkFrame(self, fg_color=PANEL_COLOR, height=45, corner_radius=4, border_width=1, border_color="#333344")
        status_frame.grid(row=1, column=0, sticky="ew", padx=30, pady=5)
        status_frame.pack_propagate(False)
        
        self.status_label = ctk.CTkLabel(status_frame, text="[SYSTEM]: AWAITING COMMAND...", font=("Consolas", 12, "bold"), text_color=TEXT_DIM)
        self.status_label.pack(side="left", padx=15, pady=10)

        # 3. Grid Container (Scrollable Frame สำหรับวางการ์ด)
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="#0A0A0F", border_width=1, border_color="#333344", corner_radius=4)
        self.scroll_frame.grid(row=2, column=0, sticky="nsew", padx=30, pady=(10, 20))
        
        # จัดให้คอลัมน์ขยายตามพื้นที่ (ทำเป็น 2 คอลัมน์)
        self.scroll_frame.grid_columnconfigure(0, weight=1)
        self.scroll_frame.grid_columnconfigure(1, weight=1)

        # ทำการลูปสร้างการ์ดแอป
        row_idx = 0
        col_idx = 0
        for tool in self.tools:
            self.create_app_card(self.scroll_frame, tool, row_idx, col_idx)
            col_idx += 1
            if col_idx > 1: # ถ้าครบ 2 คอลัมน์ให้ขึ้นบรรทัดใหม่
                col_idx = 0
                row_idx += 1

    def create_app_card(self, parent, tool, r, c):
        # Card Frame
        card = ctk.CTkFrame(parent, fg_color=PANEL_COLOR, corner_radius=6, border_width=1, border_color="#333344")
        card.grid(row=r, column=c, padx=10, pady=10, sticky="nsew")
        
        # จัด Layout ด้านในการ์ด (Icon ซ้าย, ข้อมูลกลาง, ปุ่มเปิดล่าง)
        top_frame = ctk.CTkFrame(card, fg_color="transparent")
        top_frame.pack(fill="x", padx=15, pady=(15, 5))
        
        # Icon
        ctk.CTkLabel(top_frame, text=tool["icon"], font=("Segoe UI Emoji", 32)).pack(side="left", padx=(0, 15))
        
        # ข้อมูล Text
        text_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        text_frame.pack(side="left", fill="x", expand=True)
        
        ctk.CTkLabel(text_frame, text=tool["name"], font=("Consolas", 18, "bold"), text_color="white", anchor="w").pack(fill="x")
        ctk.CTkLabel(text_frame, text=tool["desc"], font=("Consolas", 11), text_color=TEXT_DIM, anchor="w").pack(fill="x")

        # ปุ่ม Launch
        btn = ctk.CTkButton(
            card, text="[ LAUNCH_MODULE ]", font=("Consolas", 12, "bold"),
            fg_color="transparent", border_width=1, border_color=ACCENT_CYAN, text_color=ACCENT_CYAN,
            hover_color="#003344", height=35,
            command=lambda cmd=tool["cmd"], name=tool["name"]: self.launch_app(cmd, name)
        )
        btn.pack(fill="x", padx=15, pady=(5, 15))

    def launch_app(self, cmd, name):
        self.status_label.configure(text=f"[SYSTEM]: INITIATING {name.upper()}...", text_color="#FFB800")
        self.update_idletasks() # บังคับอัปเดตหน้าจอก่อนรัน
        
        try:
            # ใช้ subprocess.Popen พร้อม shell=True 
            # และโยน output ลง DEVNULL เพื่อไม่ให้มารบกวนโปรแกรมหลักของเรา และไม่ล็อก UI
            subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # อัปเดตสถานะเป็นสำเร็จ
            self.status_label.configure(text=f"[+] SUCCESS: {name.upper()} MODULE IS ACTIVE.", text_color=ACCENT_GREEN)
        except Exception as e:
            # กรณีเกิด Error เช่น ไม่มีโปรแกรมในเครื่อง
            self.status_label.configure(text=f"[!] ERROR LAUNCHING {name.upper()}: {e}", text_color=ALERT_RED)