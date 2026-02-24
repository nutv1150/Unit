import customtkinter as ctk
from tkinter import filedialog, Menu
import puremagic
import os
import re
import subprocess

class FileInspectionPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        # อ้างอิงถึงคลาสหลัก UNITApp (ลำดับชั้น: Page -> Container -> App)
        self.app_root = master.master 
        
        self.selected_file_path = ""
        self.wordlist_path = ""
        
        # ⭐ ไม่บังคับเลือก Regex (ค่าเริ่มต้นเป็นค่าว่าง)
        self.regex_var = ctk.StringVar(value="") 
        self.regex_radios = [] 

        # --- Header Section ---
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=15)
        ctk.CTkLabel(header_frame, text="📁 Advanced File Inspection", font=("Segoe UI", 20, "bold")).pack(side="left")

        # --- File Browser ---
        browse_frame = ctk.CTkFrame(self, fg_color="transparent")
        browse_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkButton(browse_frame, text="Browse", width=80, command=self.browse_file).pack(side="left")
        self.file_entry = ctk.CTkEntry(browse_frame, placeholder_text="Select file to analyze...", font=("Segoe UI", 12))
        self.file_entry.pack(side="left", fill="x", expand=True, padx=10)

        # --- Tools & Actions ---
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.pack(fill="x", padx=20, pady=5)
        self.tool_menu = ctk.CTkOptionMenu(
            action_frame, 
            values=["Magic Check", "Executable Check", "Strings", "Steghide Extract"], 
            width=180
        )
        self.tool_menu.pack(side="left", padx=(0, 10))
        ctk.CTkButton(action_frame, text="Analyze", width=100, fg_color="#E67E22", command=self.run_analysis).pack(side="left")

        # --- Status Label ---
        self.warning_label = ctk.CTkLabel(
            self, text="⚠️ Ready", text_color="#E67E22", fg_color="#34495E", 
            height=35, corner_radius=5, font=("Segoe UI", 13, "bold")
        )
        self.warning_label.pack(fill="x", padx=20, pady=10)

        # --- Regex Selection Section ---
        regex_manager_frame = ctk.CTkFrame(self, fg_color="#2C3E50", corner_radius=8)
        regex_manager_frame.pack(fill="x", padx=20, pady=5)
        
        # ส่วนเพิ่ม Pattern ใหม่
        custom_input_frame = ctk.CTkFrame(regex_manager_frame, fg_color="transparent")
        custom_input_frame.pack(fill="x", padx=10, pady=5)
        self.custom_regex_entry = ctk.CTkEntry(custom_input_frame, placeholder_text="Enter Custom Regex...", height=30)
        self.custom_regex_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(custom_input_frame, text="Add", width=60, command=self.add_custom_regex).pack(side="left")

        # รายการ RadioButtons
        self.radio_container = ctk.CTkScrollableFrame(regex_manager_frame, height=100, fg_color="#1A1A1A")
        self.radio_container.pack(fill="x", padx=10, pady=5)
        
        for p in [r"FLAG\{.*?\}", r"(flag|ctf|picoCTF)\{[^}]+\}", r"\{[0-9a-fA-F]{16,}\}"]:
            self.create_radio(p)

        # ⭐ ปุ่ม Clear Regex Selection
        ctk.CTkButton(
            regex_manager_frame, text="Clear Regex Selection", width=120, height=20, 
            fg_color="#5f6475", font=("Arial", 11), command=self.clear_regex_selection
        ).pack(pady=5)

        # --- Output Terminal ---
        self.output = ctk.CTkTextbox(self, height=250, fg_color="#000000", text_color="#00FF00", font=("Consolas", 12))
        self.output.pack(fill="both", expand=True, padx=20, pady=10)
        self.output.tag_config("found", background="#FFFF00", foreground="#000000")

        # ⭐ Right-Click Context Menu
        self.context_menu = Menu(self, tearoff=0, bg="#2C3E50", fg="white", activebackground="#E67E22")
        self.context_menu.add_command(label="🚀 Send Selection to Data Hashing", command=self.send_selection)
        self.output.bind("<Button-3>", self.show_context_menu)

    # --- Utility Functions ---
    def show_context_menu(self, event):
        try:
            if self.output.tag_ranges("sel"):
                self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def send_selection(self):
        try:
            selected_text = self.output.get("sel.first", "sel.last").strip()
            if selected_text and hasattr(self.app_root, "send_to_hashing"):
                self.app_root.send_to_hashing(selected_text)
        except: pass

    def clear_regex_selection(self):
        self.regex_var.set("")
        for rb in self.regex_radios: rb.deselect()
        self.log("[*] Regex Selection Cleared.")

    def create_radio(self, pattern):
        rb = ctk.CTkRadioButton(self.radio_container, text=pattern, variable=self.regex_var, value=pattern, font=("Consolas", 11), text_color="#95A5A6")
        rb.pack(anchor="w", padx=15, pady=5)
        self.regex_radios.append(rb)

    def add_custom_regex(self):
        p = self.custom_regex_entry.get().strip()
        if p:
            try:
                re.compile(p)
                self.create_radio(p)
                self.custom_regex_entry.delete(0, "end")
            except: self.log("[!] Invalid Regex Pattern")

    def log(self, message):
        self.output.insert("end", message + "\n")
        self.output.see("end")

    def browse_file(self):
        path = filedialog.askopenfilename()
        if path:
            self.selected_file_path = path
            self.file_entry.delete(0, "end")
            self.file_entry.insert(0, path)

    def browse_wordlist(self):
        path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if path: self.wordlist_path = path

    # --- Core Analysis Functions ---
    def run_analysis(self):
        if not self.selected_file_path: return
        self.output.delete("1.0", "end") # ล้างหน้าจอทุกครั้งที่กด Analyze
        choice = self.tool_menu.get()
        if choice == "Magic Check": self.inspect_file_header()
        elif choice == "Executable Check": self.check_if_executable()
        elif choice == "Strings": self.extract_all_strings()
        elif choice == "Steghide Extract": self.run_steghide_extract()

    def inspect_file_header(self):
        """ ตรวจสอบประเภทไฟล์ให้แม่นยำขึ้น (PDF, Text, Binary) """
        try:
            with open(self.selected_file_path, 'rb') as f:
                header_16 = f.read(16)
                h_hex = header_16.hex().upper()

            # 1. ขยายฐานข้อมูล Manual Signature
            signatures = {
                "504B0304": "ZIP / MS Office (Docx, Pptx)",
                "FFD8FF": "JPEG Image",
                "89504E47": "PNG Image",
                "25504446": "PDF Document",
                "4D5A": "Windows Executable (EXE/DLL)",
                "7F454C46": "Linux Executable (ELF)",
                "47494638": "GIF Image",
                "3C3F786D6C": "XML Document",
                "66747970": "MP4 Video"
            }
            
            res = next((v for k, v in signatures.items() if h_hex.startswith(k)), None)
            
            # 2. ถ้าไม่เจอ ให้ใช้ puremagic
            if not res:
                try:
                    exts = puremagic.from_file(self.selected_file_path)
                    if exts: res = f"{exts[0].name} ({exts[0].extension})"
                except: pass

            # 3. ถ้ายังไม่เจอ ให้ลองเช็คว่าเป็น Plain Text (txt) หรือไม่
            if not res:
                try:
                    header_16.decode('utf-8')
                    res = "Plain Text (.txt / Source Code)"
                except UnicodeDecodeError:
                    res = "Unknown Binary Data"
            
            self.log(f"[✔] Detected Type: {res}")
            self.warning_label.configure(text=f"Magic: {res}", text_color="#2ECC71")
        except Exception as e: self.log(f"[Error] {str(e)}")

    def check_if_executable(self):
        """ ตรวจสอบความสามารถในการรัน (EXE, ELF, Scripts) """
        try:
            with open(self.selected_file_path, 'rb') as f:
                header = f.read(16)
            
            if header.startswith(b'\x7fELF'): res = "Linux Executable (ELF Binary)"
            elif header.startswith(b'MZ'): res = "Windows Executable (PE Binary)"
            elif header.startswith(b'#!'): 
                line = header.decode('utf-8', errors='ignore').split('\n')[0]
                res = f"Script File ({line})"
            elif header.startswith(b'\xCA\xFE\xBA\xBE'): res = "Java Class / Mach-O"
            elif header.startswith(b'\x42\x0d\x0d\x0a'): res = "Python Compiled (pyc)"
            else: res = "Non-Executable / Data File"
                
            self.log(f"[✔] Result: {res}")
            self.warning_label.configure(text=f"Analysis: {res}", text_color="#3498DB")
        except Exception as e: self.log(f"[Error] {str(e)}")

    def extract_all_strings(self):
        """ ดึง String และรองรับการ Highlight """
        pattern = self.regex_var.get()
        try:
            with open(self.selected_file_path, "rb") as f: content = f.read()
            found = re.findall(rb"[ -~]{4,}", content)
            matches_count = 0
            for s in found:
                line = s.decode(errors="ignore")
                if pattern:
                    matches = list(re.finditer(pattern, line, re.IGNORECASE))
                    if matches:
                        matches_count += len(matches)
                        self.output.insert("end", "🚩 [MATCH]: ")
                        last_pos = 0
                        for m in matches:
                            start, end = m.span()
                            self.output.insert("end", line[last_pos:start])
                            self.output.insert("end", line[start:end], "found")
                            last_pos = end
                        self.output.insert("end", line[last_pos:] + "\n")
                else: self.log(f"  {line}")
            if pattern: self.warning_label.configure(text=f"🚩 Found {matches_count} matches", text_color="#2ECC71")
        except Exception as e: self.log(f"[Error] {str(e)}")

    def run_steghide_extract(self):
        self.log(f"[*] Processing Steghide...")
        pwd = self.pass_entry.get()
        cmd = ["steghide", "extract", "-sf", self.selected_file_path, "-p", pwd, "-f"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True)
            self.log(res.stdout if "wrote" in res.stdout else f"[!] Fail: {res.stderr}")
        except: self.log("[!] Steghide command not found.")