import customtkinter as ctk
from tkinter import filedialog
import puremagic
import os
import re
import subprocess

class FileInspectionPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.selected_file_path = ""
        self.wordlist_path = ""
        self.regex_checkboxes = [] 

        # --- Header Section ---
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=15)
        ctk.CTkLabel(header_frame, text="📁 File Inspection", font=("Segoe UI", 20, "bold")).pack(side="left")

        # --- File Browser ---
        browse_frame = ctk.CTkFrame(self, fg_color="transparent")
        browse_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkButton(browse_frame, text="Browse", width=80, command=self.browse_file, font=("Segoe UI", 12)).pack(side="left")
        self.file_entry = ctk.CTkEntry(browse_frame, placeholder_text="Path to file...", font=("Segoe UI", 12))
        self.file_entry.pack(side="left", fill="x", expand=True, padx=10)

        # --- Steghide & Wordlist Section ---
        steg_control_frame = ctk.CTkFrame(self, fg_color="transparent")
        steg_control_frame.pack(fill="x", padx=20, pady=5)
        self.pass_entry = ctk.CTkEntry(steg_control_frame, placeholder_text="Passphrase (Optional)", width=200)
        self.pass_entry.pack(side="left", padx=(0, 10))
        self.wordlist_btn = ctk.CTkButton(steg_control_frame, text="Select Wordlist", fg_color="#4A4F60", command=self.browse_wordlist)
        self.wordlist_btn.pack(side="left")

        # --- Tools & Actions ---
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.pack(fill="x", padx=20, pady=5)
        self.tool_menu = ctk.CTkOptionMenu(
            action_frame, 
            values=["Magic Check", "Executable Check", "Strings", "Steghide Extract"], 
            width=180, font=("Segoe UI", 12)
        )
        self.tool_menu.pack(side="left", padx=(0, 10))
        ctk.CTkButton(action_frame, text="Analyze", width=80, command=self.run_analysis, font=("Segoe UI", 12)).pack(side="left")

        # --- Warning Label ---
        self.warning_label = ctk.CTkLabel(
            self, text="⚠️ Ready to Analyze", text_color="#E67E22", fg_color="#34495E", 
            height=35, corner_radius=5, font=("Segoe UI", 13, "bold")
        )
        self.warning_label.pack(fill="x", padx=20, pady=10)

        # --- Regex Pattern Selection ---
        regex_container = ctk.CTkFrame(self, fg_color="#2C3E50", corner_radius=8)
        regex_container.pack(fill="x", padx=20, pady=10)
        patterns_list = [r"FLAG\{.*?\}", r"(flag|ctf|picoCTF|HTB|THM)\{[^}]+\}", r"\{[0-9a-fA-F]{16,}\}(Hex)"]
        for p in patterns_list:
            cb = ctk.CTkCheckBox(regex_container, text=p, font=("Consolas", 11), text_color="#95A5A6")
            cb.pack(anchor="w", padx=15, pady=5)
            self.regex_checkboxes.append((cb, p))

        # --- Output Terminal ---
        self.output = ctk.CTkTextbox(self, height=250, fg_color="#1A1A1A", text_color="#00FF00", font=("Consolas", 12))
        self.output.pack(fill="both", expand=True, padx=20, pady=10)

    # --- Core Logic Functions ---

    def browse_file(self):
        path = filedialog.askopenfilename()
        if path:
            self.selected_file_path = path
            self.file_entry.delete(0, "end")
            self.file_entry.insert(0, path)
            self.log(f"[+] Selected: {os.path.basename(path)}")

    def browse_wordlist(self):
        path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if path:
            self.wordlist_path = path
            self.wordlist_btn.configure(text=os.path.basename(path), fg_color="#2ECC71")
            self.log(f"[+] Wordlist loaded: {path}")

    def run_analysis(self):
        if not self.selected_file_path:
            self.log("[!] Please select a file first.")
            return
        choice = self.tool_menu.get()
        if choice == "Magic Check": self.inspect_file_header()
        elif choice == "Executable Check": self.check_if_executable()
        elif choice == "Strings": self.extract_all_strings()
        elif choice == "Steghide Extract": self.run_steghide_extract()

    def inspect_file_header(self):
        """ ตรวจสอบ Magic Bytes แบบรวมไฟล์ ZIP และไฟล์ภาพ/เอกสารอื่นๆ """
        try:
            self.log(f"\n[*] Analyzing: {os.path.basename(self.selected_file_path)}")
            
            # อ่าน Header 12 bytes เพื่อเช็ค Magic Bytes
            with open(self.selected_file_path, 'rb') as f:
                h_bytes = f.read(12)
                h_hex = h_bytes.hex().upper()
            
            # ตารางตรวจสอบ Magic Bytes (ลำดับความสำคัญสูง)
            manual_map = {
                "504B0304": "ZIP Archive or MS Office (.zip/.docx/.xlsx)",
                "FFD8FF": "JPEG Image (.jpg / .jpeg)",
                "89504E47": "Portable Network Graphics (.png)",
                "25504446": "Adobe Portable Document Format (.pdf)",
                "4D5A": "Windows Executable (.exe / .dll)",
                "7F454C46": "Linux ELF Executable (Binary)",
                "47494638": "GIF Image (.gif)"
            }
            
            res = None
            for sig, name in manual_map.items():
                if h_hex.startswith(sig):
                    res = name
                    break
            
            # ถ้ายังไม่เจอ ให้ลองเช็คว่าเป็น Plain Text หรือใช้ Library
            if not res:
                try:
                    with open(self.selected_file_path, 'r', encoding='utf-8') as f:
                        f.read(512)
                    res = "Plain Text (.txt)"
                except:
                    exts = puremagic.from_file(self.selected_file_path)
                    res = exts[0].name if exts else "Unknown Type"
            
            self.log(f"[✔] Result: {res}")
            self.warning_label.configure(text=f"✅ Identified: {res}", text_color="#2ECC71")
        except Exception as e:
            self.log(f"[Error] {str(e)}")

    def check_if_executable(self):
        """ ตรวจสอบความปลอดภัยของไฟล์รัน """
        with open(self.selected_file_path, 'rb') as f:
            h = f.read(4)
        if h == b'\x7fELF':
            self.log("[✔] Type: Linux ELF Binary")
            self.warning_label.configure(text="⚠️ Warning: Linux Binary Detected", text_color="#E67E22")
        elif h[:2] == b'MZ':
            self.log("[✔] Type: Windows PE Binary (.exe)")
            self.warning_label.configure(text="⚠️ Warning: Windows Executable Detected", text_color="#E67E22")
        else:
            self.log("[x] Not a binary executable.")
            self.warning_label.configure(text="✅ Safe: Not a Binary File", text_color="#2ECC71")

    def run_steghide_extract(self):
        """ ระบบสกัดไฟล์ Steganography """
        self.log(f"[*] Starting Steghide on: {os.path.basename(self.selected_file_path)}")
        user_pass = self.pass_entry.get()
        
        # ลองรันด้วย Passphrase ที่ระบุ
        cmd = ["steghide", "extract", "-sf", self.selected_file_path, "-p", user_pass, "-f"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if "wrote extracted data to" in result.stdout:
            self.log(f"[✔] Success: {result.stdout.strip()}")
            self.warning_label.configure(text="✅ Extraction Successful", text_color="#2ECC71")
            return

        if self.wordlist_path:
            self.log("[!] Starting Wordlist Brute-force...")
            try:
                with open(self.wordlist_path, 'r', errors='ignore') as f:
                    for line in f:
                        pwd = line.strip()
                        res = subprocess.run(["steghide", "extract", "-sf", self.selected_file_path, "-p", pwd, "-f"], capture_output=True, text=True)
                        if "wrote extracted data to" in res.stdout:
                            self.log(f"🚩 [FOUND] Passphrase: {pwd}")
                            self.warning_label.configure(text=f"✅ Found: {pwd}", text_color="#2ECC71")
                            return
                self.log("[x] Brute-force failed.")
            except Exception as e: self.log(f"[Error] {str(e)}")
        
        self.log("[!] Extraction failed.")
        self.warning_label.configure(text="❌ Extraction Failed", text_color="#E74C3C")

    def extract_all_strings(self):
        """ สกัดข้อความ ASCII ทั้งหมด """
        self.log("[*] Extracting all printable strings...")
        try:
            with open(self.selected_file_path, "rb") as f:
                content = f.read()
            found = re.findall(rb"[ -~]{4,}", content)
            decoded = [s.decode(errors="ignore") for s in found]
            active_p = [p for cb, p in self.regex_checkboxes if cb.get()]
            matches = 0
            for line in decoded:
                is_m = any(re.search(p, line, re.IGNORECASE) for p in active_p)
                if is_m:
                    self.log(f"🚩 [MATCH]: {line}")
                    matches += 1
                else:
                    self.log(f"  {line}")
            if matches > 0: self.warning_label.configure(text=f"🚩 Found {matches} matches!", text_color="#2ECC71")
        except Exception as e: self.log(f"[Error] {str(e)}")

    def log(self, message):
        self.output.insert("end", message + "\n")
        self.output.see("end")