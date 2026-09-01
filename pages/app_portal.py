import customtkinter as ctk
import subprocess
import os
import shutil
import json
import glob

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
        
        self.default_tools = [
            {"name": "Wireshark", "check": "wireshark", "cmd": "wireshark", "desc": "Network Protocol Analyzer", "icon": "🦈"},
            {"name": "Burp Suite", "check": "burpsuite", "cmd": "burpsuite", "desc": "Web Vulnerability Scanner", "icon": "🕸️"},
            {"name": "Ghidra", "check": "ghidra", "cmd": "ghidra", "desc": "Software Reverse Engineering", "icon": "🐉"},
            
            {"name": "Nmap", "check": "nmap", "cmd": "x-terminal-emulator -e bash -c 'echo -e \"\\e[1;36m[+] NMAP MODULE READY\\e[0m\"; read -e -i \"nmap \" -p \"root@kali:~# \" cmd; eval \"$cmd\"; exec bash'", "desc": "Network Mapper (CLI)", "icon": "🗺️"},
            {"name": "Metasploit", "check": "msfconsole", "cmd": "x-terminal-emulator -e bash -c 'msfconsole; exec bash'", "desc": "Penetration Testing Framework", "icon": "Ⓜ️"},
            {"name": "Hashcat", "check": "hashcat", "cmd": "x-terminal-emulator -e bash -c 'echo -e \"\\e[1;36m[+] HASHCAT MODULE READY\\e[0m\"; read -e -i \"hashcat \" -p \"root@kali:~# \" cmd; eval \"$cmd\"; exec bash'", "desc": "Advanced Password Recovery", "icon": "🔐"},
            
            {"name": "CyberChef", "check": "firefox", "cmd": "firefox https://gchq.github.io/CyberChef/", "desc": "The Cyber Swiss Army Knife", "icon": "👨‍🍳"},
            {"name": "Terminal", "check": "x-terminal-emulator", "cmd": "x-terminal-emulator", "desc": "Open a new root shell", "icon": "💻"}
        ]

        self.custom_tools_file = "custom_tools.json"
        self.custom_tools = self.load_custom_tools()
        self.tools = self.default_tools + self.custom_tools

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1) 

        # --- Header & Search & Add Button ---
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=30, pady=(20, 5))
        
        ctk.CTkLabel(header_frame, text=">_ APP_PORTAL :: [QUICK_LAUNCH]", font=("Consolas", 28, "bold"), text_color=ACCENT_CYAN).pack(side="left")
        
        self.btn_add_tool = ctk.CTkButton(
            header_frame, text="[ + ADD ]", font=("Consolas", 12, "bold"),
            fg_color="transparent", border_width=1, border_color=ACCENT_GREEN, text_color=ACCENT_GREEN,
            hover_color="#003311", height=35, width=90, command=self.open_add_tool_popup
        )
        self.btn_add_tool.pack(side="right", padx=(10, 0))

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.refresh_grid())
        
        self.search_entry = ctk.CTkEntry(
            header_frame, textvariable=self.search_var, placeholder_text="🔍 SEARCH MODULES...",
            font=("Consolas", 12), width=220, height=35,
            fg_color="#0A0A0F", border_color="#333344", text_color="white"
        )
        self.search_entry.pack(side="right")

        # --- Status Bar ---
        status_frame = ctk.CTkFrame(self, fg_color=PANEL_COLOR, height=45, corner_radius=4, border_width=1, border_color="#333344")
        status_frame.grid(row=1, column=0, sticky="ew", padx=30, pady=5)
        status_frame.pack_propagate(False)
        
        self.status_label = ctk.CTkLabel(status_frame, text="[SYSTEM]: AWAITING COMMAND...", font=("Consolas", 12, "bold"), text_color=TEXT_DIM)
        self.status_label.pack(side="left", padx=15, pady=10)

        # --- Grid Container ---
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="#0A0A0F", border_width=1, border_color="#333344", corner_radius=4)
        self.scroll_frame.grid(row=2, column=0, sticky="nsew", padx=30, pady=(10, 20))
        self.scroll_frame.grid_columnconfigure(0, weight=1)
        self.scroll_frame.grid_columnconfigure(1, weight=1)

        self.refresh_grid()

    def load_custom_tools(self):
        if os.path.exists(self.custom_tools_file):
            try:
                with open(self.custom_tools_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return []
        return []

    def save_custom_tools(self):
        try:
            with open(self.custom_tools_file, "w", encoding="utf-8") as f:
                json.dump(self.custom_tools, f, indent=4, ensure_ascii=False)
        except Exception as e:
            self.status_label.configure(text=f"[!] ERROR SAVING TOOL: {e}", text_color=ALERT_RED)

    def refresh_grid(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        keyword = self.search_var.get().strip().lower()
        filtered_tools = [
            t for t in self.tools 
            if keyword in t["name"].lower() or keyword in t.get("desc", "").lower()
        ]

        row_idx = 0
        col_idx = 0
        for tool in filtered_tools:
            self.create_app_card(self.scroll_frame, tool, row_idx, col_idx)
            col_idx += 1
            if col_idx > 1: 
                col_idx = 0
                row_idx += 1

    def create_app_card(self, parent, tool, r, c):
        card = ctk.CTkFrame(parent, fg_color=PANEL_COLOR, corner_radius=6, border_width=1, border_color="#333344")
        card.grid(row=r, column=c, padx=10, pady=10, sticky="nsew")
        
        top_frame = ctk.CTkFrame(card, fg_color="transparent")
        top_frame.pack(fill="x", padx=15, pady=(15, 5))
        
        ctk.CTkLabel(top_frame, text=tool.get("icon", "🔧"), font=("Segoe UI Emoji", 32)).pack(side="left", padx=(0, 15))
        
        text_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        text_frame.pack(side="left", fill="x", expand=True)
        
        display_name = tool["name"]
        if tool in self.custom_tools:
            display_name = f"{tool['name']} [USER]"
            
        ctk.CTkLabel(text_frame, text=display_name, font=("Consolas", 18, "bold"), text_color="white", anchor="w").pack(fill="x")
        ctk.CTkLabel(text_frame, text=tool.get("desc", "User added tool"), font=("Consolas", 11), text_color=TEXT_DIM, anchor="w").pack(fill="x")

        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=(5, 15))
        
        btn_launch = ctk.CTkButton(
            btn_frame, text="[ LAUNCH ]", font=("Consolas", 12, "bold"),
            fg_color="transparent", border_width=1, border_color=ACCENT_CYAN, text_color=ACCENT_CYAN,
            hover_color="#003344", height=35,
            command=lambda t=tool: self.launch_app(t)
        )
        btn_launch.pack(side="left", fill="x", expand=True, padx=(0, 5))

        if tool in self.custom_tools:
            btn_del = ctk.CTkButton(
                btn_frame, text="🗑️", font=("Consolas", 14), width=40,
                fg_color="transparent", border_width=1, border_color=ALERT_RED, text_color=ALERT_RED,
                hover_color="#4A0011", height=35,
                command=lambda t=tool: self.delete_tool(t)
            )
            btn_del.pack(side="right")
            
            # 🌟 เพิ่มปุ่ม Edit (แก้ไข)
            btn_edit = ctk.CTkButton(
                btn_frame, text="✏️", font=("Consolas", 14), width=40,
                fg_color="transparent", border_width=1, border_color="#FFB800", text_color="#FFB800",
                hover_color="#4A3300", height=35,
                command=lambda t=tool: self.open_edit_tool_popup(t)
            )
            btn_edit.pack(side="right", padx=(0, 5))

    def delete_tool(self, tool):
        if tool in self.custom_tools:
            self.custom_tools.remove(tool)
            self.tools = self.default_tools + self.custom_tools
            self.save_custom_tools()
            self.refresh_grid()
            self.status_label.configure(text=f"[-] TOOL '{tool['name']}' REMOVED.", text_color=ALERT_RED)

    def launch_app(self, tool):
        name = tool["name"]
        check_cmd = tool["check"]
        cmd = tool["cmd"]
        
        if shutil.which(check_cmd) is None:
            self.status_label.configure(text=f"[!] ERROR: '{name.upper()}' IS NOT INSTALLED.", text_color=ALERT_RED)
            return

        self.status_label.configure(text=f"[SYSTEM]: INITIATING {name.upper()}...", text_color="#FFB800")
        self.update_idletasks()
        
        try:
            subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.status_label.configure(text=f"[+] SUCCESS: {name.upper()} MODULE IS ACTIVE.", text_color=ACCENT_GREEN)
        except Exception as e:
            self.status_label.configure(text=f"[!] ERROR LAUNCHING {name.upper()}: {e}", text_color=ALERT_RED)

    def open_add_tool_popup(self):
        popup = ctk.CTkToplevel(self)
        popup.title("ADD CUSTOM TOOL :: [CONFIG]")
        popup.geometry("500x620")
        popup.configure(fg_color=BG_COLOR)
        
        ctk.CTkLabel(popup, text=">_ DEPLOY_NEW_MODULE", font=("Consolas", 18, "bold"), text_color=ACCENT_CYAN).pack(pady=(15,5))
        
        btn_browse_sys = ctk.CTkButton(
            popup, text="[ 🔍 BROWSE INSTALLED APPS ]", font=("Consolas", 11, "bold"),
            fg_color="transparent", border_width=1, border_color=ACCENT_CYAN, text_color=ACCENT_CYAN,
            hover_color="#003344", height=30, command=lambda: self.open_system_apps_picker(ent_name, ent_check, ent_cmd)
        )
        btn_browse_sys.pack(padx=30, pady=(0, 10), fill="x")

        frame = ctk.CTkFrame(popup, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=30, pady=5)

        ctk.CTkLabel(frame, text="MODULE NAME:", font=("Consolas", 12, "bold"), text_color="white").pack(anchor="w")
        ent_name = ctk.CTkEntry(frame, font=("Consolas", 12), fg_color="#0A0A0F", border_color="#333344", text_color="white")
        ent_name.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(frame, text="DESCRIPTION:", font=("Consolas", 12, "bold"), text_color="white").pack(anchor="w")
        ent_desc = ctk.CTkEntry(frame, font=("Consolas", 12), fg_color="#0A0A0F", border_color="#333344", text_color="white")
        ent_desc.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(frame, text="ICON (EMOJI):", font=("Consolas", 12, "bold"), text_color="white").pack(anchor="w")
        ent_icon = ctk.CTkEntry(frame, font=("Segoe UI Emoji", 12), fg_color="#0A0A0F", border_color="#333344", text_color="white")
        ent_icon.insert(0, "🛠️")
        ent_icon.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(frame, text="CHECK COMMAND (e.g. sqlmap):", font=("Consolas", 12, "bold"), text_color="white").pack(anchor="w")
        ent_check = ctk.CTkEntry(frame, font=("Consolas", 12), fg_color="#0A0A0F", border_color="#333344", text_color="white")
        ent_check.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(frame, text="EXECUTE COMMAND:", font=("Consolas", 12, "bold"), text_color="white").pack(anchor="w")
        ent_cmd = ctk.CTkEntry(frame, font=("Consolas", 12), fg_color="#0A0A0F", border_color="#333344", text_color="white")
        ent_cmd.insert(0, "x-terminal-emulator -e bash -c 'YOUR_CMD; exec bash'")
        ent_cmd.pack(fill="x", pady=(0, 15))

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x")
        
        def save_new_tool():
            name = ent_name.get().strip()
            check = ent_check.get().strip()
            cmd = ent_cmd.get().strip()
            if not name or not check or not cmd:
                return 
                
            new_tool = {
                "name": name,
                "desc": ent_desc.get().strip() or "Custom Module",
                "icon": ent_icon.get().strip() or "🛠️",
                "check": check,
                "cmd": cmd
            }
            
            self.custom_tools.append(new_tool)
            self.tools = self.default_tools + self.custom_tools
            self.save_custom_tools()
            self.refresh_grid()
            self.status_label.configure(text=f"[+] ADDED NEW TOOL: {name.upper()}", text_color=ACCENT_GREEN)
            popup.destroy()

        ctk.CTkButton(btn_frame, text="[ SAVE MODULE ]", font=("Consolas", 12, "bold"), fg_color=ACCENT_GREEN, text_color="black", hover_color="#00CC33", command=save_new_tool).pack(side="left", fill="x", expand=True, padx=(0,5))
        ctk.CTkButton(btn_frame, text="CANCEL", font=("Consolas", 12, "bold"), fg_color="transparent", border_width=1, border_color=ALERT_RED, text_color=ALERT_RED, hover_color="#4A0011", command=popup.destroy).pack(side="right", fill="x", expand=True, padx=(5,0))

        popup.update_idletasks()
        popup.focus()
        popup.grab_set()

    # 🌟 ฟังก์ชันสำหรับ Edit แอปเดิม
    def open_edit_tool_popup(self, tool):
        popup = ctk.CTkToplevel(self)
        popup.title("EDIT CUSTOM TOOL :: [CONFIG]")
        popup.geometry("500x620")
        popup.configure(fg_color=BG_COLOR)
        
        ctk.CTkLabel(popup, text=">_ EDIT_MODULE", font=("Consolas", 18, "bold"), text_color="#FFB800").pack(pady=(15,5))
        
        btn_browse_sys = ctk.CTkButton(
            popup, text="[ 🔍 BROWSE INSTALLED APPS ]", font=("Consolas", 11, "bold"),
            fg_color="transparent", border_width=1, border_color=ACCENT_CYAN, text_color=ACCENT_CYAN,
            hover_color="#003344", height=30, command=lambda: self.open_system_apps_picker(ent_name, ent_check, ent_cmd)
        )
        btn_browse_sys.pack(padx=30, pady=(0, 10), fill="x")

        frame = ctk.CTkFrame(popup, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=30, pady=5)

        # 🌟 ดึงข้อมูลเดิมจาก tool มาใส่ใน Entry
        ctk.CTkLabel(frame, text="MODULE NAME:", font=("Consolas", 12, "bold"), text_color="white").pack(anchor="w")
        ent_name = ctk.CTkEntry(frame, font=("Consolas", 12), fg_color="#0A0A0F", border_color="#333344", text_color="white")
        ent_name.insert(0, tool.get("name", ""))
        ent_name.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(frame, text="DESCRIPTION:", font=("Consolas", 12, "bold"), text_color="white").pack(anchor="w")
        ent_desc = ctk.CTkEntry(frame, font=("Consolas", 12), fg_color="#0A0A0F", border_color="#333344", text_color="white")
        ent_desc.insert(0, tool.get("desc", ""))
        ent_desc.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(frame, text="ICON (EMOJI):", font=("Consolas", 12, "bold"), text_color="white").pack(anchor="w")
        ent_icon = ctk.CTkEntry(frame, font=("Segoe UI Emoji", 12), fg_color="#0A0A0F", border_color="#333344", text_color="white")
        ent_icon.insert(0, tool.get("icon", "🛠️"))
        ent_icon.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(frame, text="CHECK COMMAND (e.g. sqlmap):", font=("Consolas", 12, "bold"), text_color="white").pack(anchor="w")
        ent_check = ctk.CTkEntry(frame, font=("Consolas", 12), fg_color="#0A0A0F", border_color="#333344", text_color="white")
        ent_check.insert(0, tool.get("check", ""))
        ent_check.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(frame, text="EXECUTE COMMAND:", font=("Consolas", 12, "bold"), text_color="white").pack(anchor="w")
        ent_cmd = ctk.CTkEntry(frame, font=("Consolas", 12), fg_color="#0A0A0F", border_color="#333344", text_color="white")
        ent_cmd.insert(0, tool.get("cmd", ""))
        ent_cmd.pack(fill="x", pady=(0, 15))

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x")
        
        def save_edited_tool():
            name = ent_name.get().strip()
            check = ent_check.get().strip()
            cmd = ent_cmd.get().strip()
            if not name or not check or not cmd:
                return 
                
            # 🌟 อัปเดตข้อมูลทับตัวเดิม
            tool["name"] = name
            tool["desc"] = ent_desc.get().strip() or "Custom Module"
            tool["icon"] = ent_icon.get().strip() or "🛠️"
            tool["check"] = check
            tool["cmd"] = cmd
            
            # อัปเดตลิสต์และเซฟ
            self.tools = self.default_tools + self.custom_tools
            self.save_custom_tools()
            self.refresh_grid()
            self.status_label.configure(text=f"[+] UPDATED TOOL: {name.upper()}", text_color=ACCENT_GREEN)
            popup.destroy()

        ctk.CTkButton(btn_frame, text="[ SAVE CHANGES ]", font=("Consolas", 12, "bold"), fg_color="#FFB800", text_color="black", hover_color="#CC9900", command=save_edited_tool).pack(side="left", fill="x", expand=True, padx=(0,5))
        ctk.CTkButton(btn_frame, text="CANCEL", font=("Consolas", 12, "bold"), fg_color="transparent", border_width=1, border_color=ALERT_RED, text_color=ALERT_RED, hover_color="#4A0011", command=popup.destroy).pack(side="right", fill="x", expand=True, padx=(5,0))

        popup.update_idletasks()
        popup.focus()
        popup.grab_set()

    # ==========================================
    # ⭐ ระบบสแกนและกรองเฉพาะแอปที่มี GUI + มีช่อง Search
    # ==========================================
    def open_system_apps_picker(self, ent_name, ent_check, ent_cmd):
        picker = ctk.CTkToplevel(self)
        picker.title("SELECT INSTALLED APP")
        picker.geometry("480x560")
        picker.configure(fg_color=BG_COLOR)
        
        ctk.CTkLabel(picker, text=">_ SELECT_SYSTEM_APPLICATION", font=("Consolas", 16, "bold"), text_color=ACCENT_CYAN).pack(pady=(15, 10))
        
        # ⭐ เพิ่มช่อง Search Bar ในหน้าต่างเลือกแอป
        picker_search_var = ctk.StringVar()
        picker_search_var.trace_add("write", lambda *args: filter_picker_list())
        
        picker_search_entry = ctk.CTkEntry(
            picker, textvariable=picker_search_var, placeholder_text="🔍 FILTER APPS...",
            font=("Consolas", 12), height=35, fg_color="#0A0A0F", border_color="#333344", text_color="white"
        )
        picker_search_entry.pack(fill="x", padx=20, pady=(0, 10))

        scroll_apps = ctk.CTkScrollableFrame(picker, fg_color="#0A0A0F", border_width=1, border_color="#333344")
        scroll_apps.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # ดึงไฟล์ .desktop ทั้งหมด
        desktop_files = glob.glob("/usr/share/applications/*.desktop") + glob.glob(os.path.expanduser("~/.local/share/applications/*.desktop"))
        
        raw_app_list = []
        for file_path in desktop_files:
            try:
                name, exec_cmd, no_display, terminal = "", "", False, False
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if line.startswith("Name=") and not name:
                            name = line.strip().split("=", 1)[1]
                        elif line.startswith("Exec=") and not exec_cmd:
                            raw_exec = line.strip().split("=", 1)[1]
                            # ตัดสัญลักษณ์อาร์กิวเมนต์เช่น %f, %U ออกให้เหลือแต่คำสั่งเพียวๆ
                            clean_exec = raw_exec.split('%')[0].strip()
                            exec_cmd = clean_exec.split()[0].replace('"', '').replace("'", "")
                        elif line.startswith("NoDisplay=true"):
                            no_display = True
                        elif line.startswith("Terminal=true"):
                            terminal = True
                
                # ⭐ กรองเงื่อนไข: เอาเฉพาะแอปที่มีชื่อ มีคำสั่ง ไม่ซ่อน (NoDisplay) และไม่ใช่แอปเทอร์มินัลล้วนๆ (เน้นแอป GUI แบบ Wireshark)
                if name and exec_cmd and not no_display and not terminal:
                    raw_app_list.append((name, exec_cmd))
            except:
                continue

        # เรียงลำดับตามตัวอักษรและตัดตัวซ้ำ
        app_list = sorted(list(set(raw_app_list)), key=lambda x: x[0])
        app_buttons = []

        def render_list(filtered_items):
            for w in scroll_apps.winfo_children():
                w.destroy()
            app_buttons.clear()

            for app_name, app_cmd in filtered_items:
                btn_app = ctk.CTkButton(
                    scroll_apps, text=f"📦 {app_name} ({app_cmd})", anchor="w",
                    font=("Consolas", 11), fg_color="transparent", text_color="white",
                    hover_color="#2B2B36", height=30,
                    command=lambda n=app_name, c=app_cmd: self.select_system_app(n, c, ent_name, ent_check, ent_cmd, picker)
                )
                btn_app.pack(fill="x", padx=5, pady=2)
                app_buttons.append((app_name, btn_app))

        def filter_picker_list():
            kw = picker_search_var.get().strip().lower()
            matched = [item for item in app_list if kw in item[0].lower() or kw in item[1].lower()]
            render_list(matched)

        render_list(app_list)

        picker.update_idletasks()
        picker.focus()
        picker.grab_set()

    def select_system_app(self, name, cmd, ent_name, ent_check, ent_cmd, picker):
        ent_name.delete(0, "end")
        ent_name.insert(0, name)
        
        ent_check.delete(0, "end")
        ent_check.insert(0, cmd)
        
        # สำหรับแอป GUI ทั่วไป ให้รันตรงๆ ได้เลยโดยไม่ต้องครอบ Terminal ซ้อน
        ent_cmd.delete(0, "end")
        ent_cmd.insert(0, cmd)
        
        picker.destroy()