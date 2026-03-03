import customtkinter as ctk
from tkinter import filedialog, Menu, Toplevel
import puremagic
import os
import re
import subprocess

class FileInspectionPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.app_root = master.master 
        
        self.selected_file_path = ""
        self.wordlist_path = ""
        self.regex_var = ctk.StringVar(value="") 
        self.regex_radios = [] 

        # ⭐ ฐานข้อมูล Smart Patterns สำหรับตรวจสอบและตั้งชื่อปุ่มอัตโนมัติ
        self.smart_db = {
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}": "📧 Email Address",
            r"(?:\d{1,3}\.){3}\d{1,3}": "🌐 IPv4 Address",
            r"https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}": "🔗 URL / Website",
            r"[a-fA-F0-9]{32}": "🔑 MD5 Hash",
            r"[a-fA-F0-9]{40}": "🔑 SHA-1 Hash",
            r"[a-fA-F0-9]{64}": "🔑 SHA-256 Hash",
            r"(?:[A-Za-z0-9+/]{4}){2,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?": "📦 Base64 String",
            r"FLAG\{.*?\}": "🚩 Standard Flag",
            r"(flag|ctf|picoCTF)\{[^}]+\}": "🚩 Common CTF Formats",
            r"\{[0-9a-fA-F]{16,}\}": "🔐 Hex in Brackets"
        }

        # คำอธิบาย Preview (Hover)
        self.regex_previews = {
            r"FLAG\{.*?\}": "🎯 Standard Flag\nใช้หา Flag รูปแบบมาตรฐาน\nตัวอย่าง: FLAG{y0ur_fl4g_h3r3}",
            r"(flag|ctf|picoCTF)\{[^}]+\}": "🌐 Multi-Platform CTF\nใช้หา Flag ของหลายสนาม (pico, HTB, etc.)",
            r"\{[0-9a-fA-F]{16,}\}": "🔑 Hex / Hash Strings\nใช้หาค่า Hash หรือเลขฐาน 16 ในปีกกา",
            "": "💡 นำเมาส์ไปชี้ที่ตัวเลือกด้านล่างเพื่อดูรายละเอียด"
        }

        # --- ⭐ Layout Configuration (ขยายพื้นที่ Output) ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1) # แถวที่ 4 (Output Terminal) จะกินพื้นที่มากที่สุด

        # 1. Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 5))
        ctk.CTkLabel(header_frame, text="📁 Advanced File Inspection & Forensic Tools", font=("Segoe UI", 20, "bold")).pack(side="left")

        # 2. File Browser
        browse_frame = ctk.CTkFrame(self, fg_color="transparent")
        browse_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=5)
        ctk.CTkButton(browse_frame, text="Browse", width=80, command=self.browse_file).pack(side="left")
        self.file_entry = ctk.CTkEntry(browse_frame, placeholder_text="Select file to analyze...", font=("Segoe UI", 12))
        self.file_entry.pack(side="left", fill="x", expand=True, padx=10)

        # 3. Action Panel
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=5)
        self.tool_menu = ctk.CTkOptionMenu(action_frame, values=["Magic Check", "Executable Check", "Strings", "Steghide Extract"], width=180)
        self.tool_menu.pack(side="left", padx=(0, 10))
        ctk.CTkButton(action_frame, text="Analyze", width=100, fg_color="#E67E22", command=self.run_analysis).pack(side="left")
        
        # ช่อง Status Label
        self.warning_label = ctk.CTkLabel(action_frame, text="⚠️ Ready", text_color="#E67E22", fg_color="#34495E", height=35, corner_radius=5, font=("Segoe UI", 13, "bold"))
        self.warning_label.pack(side="right", fill="x", expand=True, padx=(10, 0))

        # 4. ⭐ Regex Selection Section (ลดขนาดลงเพื่อประหยัดพื้นที่) ---
        regex_manager_frame = ctk.CTkFrame(self, fg_color="#2C3E50", corner_radius=8)
        regex_manager_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=5)
        
        # กรอบ Preview ล็อกความสูงเพื่อกันภาพเขย่า
        self.preview_container = ctk.CTkFrame(regex_manager_frame, fg_color="#1A1A1A", height=65, corner_radius=5)
        self.preview_container.pack(fill="x", padx=10, pady=(8, 2))
        self.preview_container.pack_propagate(False) 

        self.hover_info_label = ctk.CTkLabel(self.preview_container, text=self.regex_previews[""], text_color="#3498db", font=("Segoe UI", 11, "italic"), wraplength=800)
        self.hover_info_label.pack(expand=True, fill="both")

        custom_input_frame = ctk.CTkFrame(regex_manager_frame, fg_color="transparent")
        custom_input_frame.pack(fill="x", padx=10, pady=2)
        self.custom_regex_entry = ctk.CTkEntry(custom_input_frame, placeholder_text="Enter Custom Regex Pattern...", height=30)
        self.custom_regex_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(custom_input_frame, text="Add", width=50, command=self.add_custom_regex).pack(side="left", padx=2)
        
        # ปุ่ม i พร้อมคืนค่าฟังก์ชันช่วยเหลือ
        ctk.CTkButton(custom_input_frame, text="ℹ️", width=30, fg_color="#34495E", command=self.show_regex_info).pack(side="left", padx=2)
        ctk.CTkButton(custom_input_frame, text="Clear", width=50, fg_color="#5f6475", command=self.clear_regex_selection).pack(side="left", padx=2)

        # ลดความสูงรายการปุ่มลงเพื่อเพิ่มพื้นที่ให้ส่วนล่าง
        self.radio_container = ctk.CTkScrollableFrame(regex_manager_frame, height=80, fg_color="#1A1A1A")
        self.radio_container.pack(fill="x", padx=10, pady=(2, 8))
        
        for p in [r"FLAG\{.*?\}", r"(flag|ctf|picoCTF)\{[^}]+\}", r"\{[0-9a-fA-F]{16,}\}"]:
            self.create_preview_radio(p)

        # 5. ⭐ Output Terminal (ส่วนที่ขยายพื้นที่ได้มากที่สุด) ---
        self.output = ctk.CTkTextbox(self, fg_color="#000000", text_color="#00FF00", font=("Consolas", 12), border_width=1, border_color="#34495E")
        self.output.grid(row=4, column=0, sticky="nsew", padx=20, pady=(5, 15))
        self.output.tag_config("found", background="#FFFF00", foreground="#000000")

        self.context_menu = Menu(self, tearoff=0, bg="#2C3E50", fg="white", activebackground="#E67E22")
        self.context_menu.add_command(label="🚀 Send Selection to Data Hashing", command=self.send_selection)
        self.output.bind("<Button-3>", self.show_context_menu)

    # --- ⭐ Smart & Hover Functions ⭐ ---
    def on_hover_regex(self, pattern):
        """ ดึงคำอธิบายมาโชว์เมื่อเอาเมาส์ชี้ """
        txt = self.regex_previews.get(pattern)
        if not txt:
            friendly = self.smart_db.get(pattern)
            txt = f"✨ ตรวจพบ: {friendly}\nRegex: {pattern}" if friendly else f"🛠 Custom: {pattern}"
        self.hover_info_label.configure(text=txt, text_color="#f1c40f")

    def on_leave_regex(self):
        self.hover_info_label.configure(text=self.regex_previews[""], text_color="#3498db")

    def create_preview_radio(self, pattern):
        """ สร้างปุ่ม Radio พร้อมเช็คชื่อจาก Smart DB """
        name = self.smart_db.get(pattern, pattern)
        rb = ctk.CTkRadioButton(self.radio_container, text=name, variable=self.regex_var, value=pattern, font=("Consolas", 11), text_color="#95A5A6")
        rb.pack(anchor="w", padx=15, pady=5)
        rb.bind("<Enter>", lambda e: self.on_hover_regex(pattern))
        rb.bind("<Leave>", lambda e: self.on_leave_regex())
        self.regex_radios.append(rb)

    def add_custom_regex(self):
        """ เพิ่ม Custom Regex และตั้งชื่ออัตโนมัติ """
        p = self.custom_regex_entry.get().strip()
        if p:
            try:
                re.compile(p)
                self.create_preview_radio(p)
                self.custom_regex_entry.delete(0, "end")
            except: self.log(f"[!] Invalid Regex Pattern")

    def show_regex_info(self):
        """ หน้าต่างช่วยเหลือการใช้งาน Regex """
        info_window = Toplevel(self)
        info_window.title("Regex Usage Guide")
        info_window.geometry("500x450")
        info_window.configure(bg="#212121")
        info_window.transient(self)
        container = ctk.CTkFrame(info_window, fg_color="#1A1A1A", corner_radius=10)
        container.pack(fill="both", expand=True, padx=20, pady=20)
        ctk.CTkLabel(container, text="How to use Regular Expressions", font=("Segoe UI", 16, "bold"), text_color="#E67E22").pack(pady=15)
        guide_text = "• [a-z] : พิมพ์เล็ก\n• [0-9] : ตัวเลข\n• .*? : อะไรก็ได้\n• | : แทน 'หรือ'\n\nตัวอย่าง: FLAG\{.*?\} หาธง CTF"
        ctk.CTkLabel(container, text=guide_text, justify="left", font=("Segoe UI", 12), text_color="white").pack(padx=20, pady=10)
        ctk.CTkButton(container, text="Close", width=100, command=info_window.destroy).pack(pady=15)

    # --- ⭐ Core Analysis (Fixed TXT & EXE) ⭐ ---
    def run_analysis(self):
        if not self.selected_file_path: return
        self.output.delete("1.0", "end")
        self.log(f"[*] Analyzing: {os.path.basename(self.selected_file_path)}\n" + "-"*60)
        choice = self.tool_menu.get()
        if choice == "Magic Check": self.inspect_file_header()
        elif choice == "Executable Check": self.check_if_executable()
        elif choice == "Strings": self.extract_all_strings()
        elif choice == "Steghide Extract": self.run_steghide_extract()

    def inspect_file_header(self):
        """ ตรวจสอบ Magic Number และไฟล์ประเภทข้อความ """
        try:
            with open(self.selected_file_path, 'rb') as f:
                header_data = f.read(16)
                h_hex = header_data.hex().upper()
            
            signatures = {
                "4D5A": "Windows Executable (EXE/DLL)",
                "7F454C46": "Linux Executable (ELF)",
                "504B0304": "ZIP / MS Office (Docx, Pptx)",
                "FFD8FF": "JPEG Image",
                "89504E47": "PNG Image",
                "25504446": "PDF Document"
            }
            
            res = next((v for k, v in signatures.items() if h_hex.startswith(k)), None)
            
            if not res:
                try:
                    exts = puremagic.from_file(self.selected_file_path)
                    if exts: res = f"{exts[0].name} ({exts[0].extension})"
                except: pass
            
            if not res:
                try:
                    header_data.decode('utf-8')
                    res = "Plain Text (.txt / Source Code)"
                except: res = "Unknown Binary Data"
            
            self.log(f"[✔] Detected Type: {res}")
            self.warning_label.configure(text=f"Magic: {res}", text_color="#2ECC71")
        except: self.log("[!] Error reading file magic")

    def check_if_executable(self):
        try:
            with open(self.selected_file_path, 'rb') as f: h = f.read(4)
            if h.startswith(b'\x7fELF'): res = "Linux Executable (ELF Binary)"
            elif h.startswith(b'MZ'): res = "Windows Executable (PE Binary)"
            elif h.startswith(b'#!'): res = "Script File (Shebang Detected)"
            else: res = "Non-Executable / Data File"
            self.log(f"[✔] Result: {res}")
            self.warning_label.configure(text=f"Analysis: {res}", text_color="#3498DB")
        except: pass

    def extract_all_strings(self):
        p = self.regex_var.get()
        try:
            with open(self.selected_file_path, "rb") as f: content = f.read()
            found = re.findall(rb"[ -~]{4,}", content)
            mc = 0
            for s in found:
                line = s.decode(errors="ignore")
                if p:
                    matches = list(re.finditer(p, line, re.IGNORECASE))
                    if matches:
                        mc += len(matches)
                        self.output.insert("end", "🚩 [MATCH]: ")
                        lp = 0
                        for m in matches:
                            st, en = m.span()
                            self.output.insert("end", line[lp:st])
                            self.output.insert("end", line[st:en], "found")
                            lp = en
                        self.output.insert("end", line[lp:] + "\n")
                else: self.log(f"  {line}")
            if p: self.warning_label.configure(text=f"🚩 Found {mc} matches", text_color="#2ECC71")
        except: self.log("[!] Error extracting strings")

    def run_steghide_extract(self):
        self.log(f"[*] Processing Steghide...")
        pwd = self.pass_entry.get()
        cmd = ["steghide", "extract", "-sf", self.selected_file_path, "-p", pwd, "-f"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True)
            self.log(res.stdout if "wrote" in res.stdout else f"[!] Fail: {res.stderr}")
        except: self.log("[!] Steghide command not found.")

    # --- Utilities ---
    def log(self, msg): self.output.insert("end", msg + "\n"); self.output.see("end")
    def browse_file(self):
        p = filedialog.askopenfilename()
        if p: self.selected_file_path = p; self.file_entry.delete(0, "end"); self.file_entry.insert(0, p)
    def clear_regex_selection(self):
        self.regex_var.set(""); 
        for rb in self.regex_radios: rb.deselect()
    def send_selection(self):
        try:
            sel = self.output.get("sel.first", "sel.last").strip()
            if sel and hasattr(self.app_root, "send_to_hashing"): self.app_root.send_to_hashing(sel)
        except: pass
    def show_context_menu(self, e):
        if self.output.tag_ranges("sel"): self.context_menu.tk_popup(e.x_root, e.y_root)