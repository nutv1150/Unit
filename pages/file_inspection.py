import customtkinter as ctk
from tkinter import filedialog, Menu
from tkinterdnd2 import DND_FILES
import puremagic
import os
import re
import subprocess
import threading
import hashlib
import mmap

# --- ⭐ คลาสหน้าต่าง Popup สำหรับเลือก Regex ---
class RegexSelectionPopup(ctk.CTkToplevel):
    def __init__(self, parent, current_regex, callback):
        super().__init__(parent)
        
        self.withdraw()

        self.title("Select Regex Pattern")
        self.geometry("600x550")
        
        self.callback = callback
        self.parent = parent

        self.smart_db = parent.smart_db
        self.regex_previews = parent.regex_previews
        self.regex_var = ctk.StringVar(value=current_regex)
        self.regex_radios = []

        label = ctk.CTkLabel(self, text="🎯 Choose a Pattern for Analysis", font=("Segoe UI", 16, "bold"))
        label.pack(pady=15)

        self.preview_box = ctk.CTkFrame(self, fg_color="#1A1A1A", height=65, corner_radius=5)
        self.preview_box.pack(fill="x", padx=20, pady=5)
        self.preview_box.pack_propagate(False)
        self.hover_label = ctk.CTkLabel(self.preview_box, text="💡 นำเมาส์ไปชี้ที่ตัวเลือกเพื่อดูรายละเอียด", text_color="#3498db")
        self.hover_label.pack(expand=True)

        custom_frame = ctk.CTkFrame(self, fg_color="transparent")
        custom_frame.pack(fill="x", padx=20, pady=5)

        row1 = ctk.CTkFrame(custom_frame, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 5))
        self.custom_name_entry = ctk.CTkEntry(row1, placeholder_text="Regex Name (Optional)", width=160, height=30)
        self.custom_name_entry.pack(side="left", padx=(0, 5))
        self.custom_regex_entry = ctk.CTkEntry(row1, placeholder_text="Enter Custom Regex Pattern (*Required)", height=30)
        self.custom_regex_entry.pack(side="left", fill="x", expand=True)

        row2 = ctk.CTkFrame(custom_frame, fg_color="transparent")
        row2.pack(fill="x")
        self.custom_desc_entry = ctk.CTkEntry(row2, placeholder_text="Description (Optional)", height=30)
        self.custom_desc_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(row2, text="Add", width=50, command=self.add_custom_regex).pack(side="left", padx=2)
        ctk.CTkButton(row2, text="ℹ️", width=30, fg_color="#34495E", command=parent.show_regex_info).pack(side="left", padx=2)

        self.scroll_frame = ctk.CTkScrollableFrame(self, height=180, fg_color="#2C3E50")
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

        for p in self.smart_db.keys():
            self.create_preview_radio(p)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=15)
        ctk.CTkButton(btn_frame, text="Confirm", fg_color="#2ECC71", command=self.confirm).pack(side="right", padx=5)
        ctk.CTkButton(btn_frame, text="Clear", fg_color="#5f6475", command=self.clear_selection).pack(side="right", padx=5)
        ctk.CTkButton(btn_frame, text="Cancel", fg_color="#E74C3C", command=self.destroy).pack(side="right", padx=5)

        self.update_idletasks() 
        self.deiconify()        
        self.lift()             
        self.focus_force()      

    def create_preview_radio(self, p):
        n = self.smart_db.get(p, p)
        rb = ctk.CTkRadioButton(self.scroll_frame, text=n, variable=self.regex_var, value=p)
        rb.pack(anchor="w", padx=15, pady=5)
        rb.bind("<Enter>", lambda e, p=p: self.show_preview(p))
        rb.bind("<Leave>", lambda e: self.hide_preview())
        self.regex_radios.append(rb)

    def add_custom_regex(self):
        p = self.custom_regex_entry.get().strip()
        name = self.custom_name_entry.get().strip()
        desc = self.custom_desc_entry.get().strip()
        if p:
            try: 
                re.compile(p)
                display_name = name if name else f"🛠 Custom Pattern"
                self.smart_db[p] = display_name
                desc_text = f"{desc}\n" if desc else ""
                self.regex_previews[p] = f"🛠 {display_name}\n{desc_text}Regex: {p}"
                self.create_preview_radio(p)
                self.custom_regex_entry.delete(0, "end")
                self.custom_name_entry.delete(0, "end")
                self.custom_desc_entry.delete(0, "end")
            except: pass

    def clear_selection(self):
        self.regex_var.set("")
        for rb in self.regex_radios: rb.deselect()

    def show_preview(self, p):
        txt = self.regex_previews.get(p, f"Custom: {p}")
        self.hover_label.configure(text=txt, text_color="#f1c40f")

    def hide_preview(self):
        self.hover_label.configure(text="💡 นำเมาส์ไปชี้ที่ตัวเลือกเพื่อดูรายละเอียด", text_color="#3498db")

    def confirm(self):
        self.callback(self.regex_var.get())
        self.destroy()


# --- ⭐ หน้าหลัก File Inspection ---
class FileInspectionPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.app_root = master.master 
        
        self.selected_file_path = ""
        self.regex_var = ctk.StringVar(value="") 

        # ⭐ ฐานข้อมูล Smart Patterns
        self.smart_db = {
            r"(?:0|\+66)[689]\d[- \.]?\d{3}[- \.]?\d{4}": "📱 Thai Mobile Number",
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}": "📧 Email Address",
            r"(?:\d{1,3}\.){3}\d{1,3}": "🌐 IPv4 Address",
            r"https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}": "🔗 URL / Website",
            r"[a-fA-F0-9]{32}": "🔑 MD5 Hash",
            r"FLAG\{.*?\}": "🚩 Standard Flag",
            r"(flag|ctf|picoCTF)\{[^}]+\}": "🚩 Common CTF Formats"
        }

        self.regex_previews = {
            r"(?:0|\+66)[689]\d[- \.]?\d{3}[- \.]?\d{4}": "📱 Thai Mobile Number\nหาเบอร์มือถือไทย (08x, 09x, 06x) รองรับ +66",
            r"FLAG\{.*?\}": "🎯 Standard Flag\nใช้หา Flag รูปแบบมาตรฐาน",
            r"(flag|ctf|picoCTF)\{[^}]+\}": "🌐 Multi-Platform CTF\nใช้หา Flag ของหลายสนาม (pico, HTB, etc.)",
            "": "💡 นำเมาส์ไปชี้ที่ตัวเลือกด้านล่างเพื่อดูรายละเอียด"
        }

        # --- Layout Configuration ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1) 

        # 1. Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 5))
        ctk.CTkLabel(header_frame, text="📁 File Inspection ", font=("Segoe UI", 20, "bold")).pack(side="left")

        # 2. 🚀 Drag & Drop Zone + Browse
        self.drop_zone = ctk.CTkFrame(self, fg_color="#1A1A1A", corner_radius=10, border_width=2, border_color="#34495E")
        self.drop_zone.grid(row=1, column=0, sticky="ew", padx=20, pady=5)
        
        self.drop_zone.drop_target_register(DND_FILES)
        self.drop_zone.dnd_bind('<<Drop>>', self.on_drop)

        drop_inner = ctk.CTkFrame(self.drop_zone, fg_color="transparent")
        drop_inner.pack(pady=15)
        
        self.file_icon_label = ctk.CTkLabel(drop_inner, text="📥", font=("Segoe UI", 24))
        self.file_icon_label.pack(side="left", padx=10)
        self.file_label = ctk.CTkLabel(drop_inner, text="Drag & Drop a file here, or click to Browse", text_color="gray", font=("Segoe UI", 12))
        self.file_label.pack(side="left", padx=10)
        ctk.CTkButton(drop_inner, text="Browse File", width=100, command=self.browse_file).pack(side="left", padx=10)

        # 3. 📊 File Metadata Card
        self.meta_frame = ctk.CTkFrame(self, fg_color="#212121", height=40, corner_radius=8)
        self.meta_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=5)
        self.meta_frame.grid_remove() 

        self.meta_size = ctk.CTkLabel(self.meta_frame, text="📦 Size: --", font=("Segoe UI", 11, "bold"), text_color="#3498db")
        self.meta_size.pack(side="left", padx=15, pady=8)
        self.meta_ext = ctk.CTkLabel(self.meta_frame, text="🏷️ Ext: --", font=("Segoe UI", 11, "bold"), text_color="#e67e22")
        self.meta_ext.pack(side="left", padx=15, pady=8)
        self.meta_md5 = ctk.CTkLabel(self.meta_frame, text="🔑 MD5: --", font=("Consolas", 11), text_color="#95a5a6")
        self.meta_md5.pack(side="left", padx=15, pady=8)

        # 4. Action Panel
        action_frame = ctk.CTkFrame(self, fg_color="#2C3E50", corner_radius=8)
        action_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=10)

        self.tool_menu = ctk.CTkOptionMenu(action_frame, values=["Magic Check", "Executable Check", "Strings", "zsteg Analysis"], width=180, state="disabled", command=self.toggle_regex_button)
        self.tool_menu.pack(side="left", padx=15, pady=10)

        self.btn_analyze = ctk.CTkButton(action_frame, text="Analyze", width=100, fg_color="#E67E22", state="disabled", command=self.start_analysis_thread)
        self.btn_analyze.pack(side="left", padx=5)

        self.btn_regex_popup = ctk.CTkButton(action_frame, text="⚙️ Select Regex", fg_color="#34495E", state="disabled", command=self.open_regex_popup)
        self.btn_regex_popup.pack(side="left", padx=5)

        # ⭐ ปุ่มใหม่: Clear Regex (หน้าหลัก)
        self.btn_clear_regex = ctk.CTkButton(action_frame, text="❌", width=30, fg_color="#E74C3C", hover_color="#C0392B", state="disabled", command=self.clear_main_regex)
        self.btn_clear_regex.pack(side="left", padx=(0, 5))

        self.progress_bar = ctk.CTkProgressBar(action_frame, mode="indeterminate", width=100)
        self.progress_bar.pack(side="left", padx=15)
        self.progress_bar.pack_forget() 

        self.warning_label = ctk.CTkLabel(action_frame, text="⚠️ Ready", text_color="#E67E22", font=("Segoe UI", 13, "bold"))
        self.warning_label.pack(side="right", padx=(10, 20))

        self.regex_status_label = ctk.CTkLabel(action_frame, text="Regex: None", font=("Segoe UI", 11, "italic"), text_color="#3498db")
        self.regex_status_label.pack(side="right", padx=10)

        # 5. ⭐ Output Header & Terminal
        output_header = ctk.CTkFrame(self, fg_color="transparent")
        output_header.grid(row=4, column=0, sticky="ew", padx=20, pady=(5, 0))
        ctk.CTkLabel(output_header, text="💻 Terminal Output", font=("Segoe UI", 12, "bold"), text_color="gray").pack(side="left")
        
        ctk.CTkButton(output_header, text="🗑️ Clear Terminal", width=60, height=24, fg_color="#E74C3C", hover_color="#C0392B", command=self.clear_terminal).pack(side="right")

        self.output = ctk.CTkTextbox(self, fg_color="#000000", text_color="#00FF00", font=("Consolas", 12), border_width=1, border_color="#34495E")
        self.output.grid(row=5, column=0, sticky="nsew", padx=20, pady=(5, 15))
        self.output.tag_config("found", background="#FFFF00", foreground="#000000")
        self.output.tag_config("error", foreground="#FF5555")

        self.context_menu = Menu(self, tearoff=0, bg="#2C3E50", fg="white", activebackground="#E67E22")
        self.context_menu.add_command(label="🚀 Send Selection to Data Hashing", command=self.send_selection)
        self.output.bind("<Button-3>", self.show_context_menu)

    # --- UI Events & Metadata ---
    def on_drop(self, event):
        file_path = event.data
        if file_path.startswith('{') and file_path.endswith('}'):
            file_path = file_path[1:-1]
        self.load_file(file_path)

    def browse_file(self):
        p = filedialog.askopenfilename()
        if p: self.load_file(p)

    def load_file(self, path):
        if not os.path.exists(path): return
        self.selected_file_path = path
        
        self.drop_zone.configure(border_color="#2ECC71")
        self.file_icon_label.configure(text="📄")
        self.file_label.configure(text=f"Loaded: {os.path.basename(path)}", text_color="#2ECC71")
        
        self.tool_menu.configure(state="normal")
        self.btn_analyze.configure(state="normal")
        self.toggle_regex_button(self.tool_menu.get())

        self.update_metadata_card(path)

    def update_metadata_card(self, path):
        self.meta_frame.grid() 
        
        size_bytes = os.path.getsize(path)
        if size_bytes < 1024: size_str = f"{size_bytes} B"
        elif size_bytes < 1024**2: size_str = f"{size_bytes/1024:.2f} KB"
        else: size_str = f"{size_bytes/(1024**2):.2f} MB"
        
        ext = os.path.splitext(path)[1].lower() or "Unknown"

        threading.Thread(target=self._calc_md5, args=(path, size_str, ext), daemon=True).start()

    def _calc_md5(self, path, size_str, ext):
        md5 = hashlib.md5()
        try:
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    md5.update(chunk)
            result = md5.hexdigest()
        except:
            result = "Error"
            
        self.after(0, lambda: self._update_meta_ui(size_str, ext, result))
        
    def _update_meta_ui(self, size_str, ext, md5_str):
        self.meta_size.configure(text=f"📦 Size: {size_str}")
        self.meta_ext.configure(text=f"🏷️ Ext: {ext}")
        self.meta_md5.configure(text=f"🔑 MD5: {md5_str}")

    def clear_terminal(self):
        self.output.delete("1.0", "end")

    # --- Regex Controls ---
    def toggle_regex_button(self, mode):
        # ⭐ เปิดใช้งานทั้งปุ่มเลือก Regex และปุ่ม Clear Regex พร้อมกัน
        if mode == "Strings": 
            self.btn_regex_popup.configure(state="normal")
            self.btn_clear_regex.configure(state="normal")
        else: 
            self.btn_regex_popup.configure(state="disabled")
            self.btn_clear_regex.configure(state="disabled")

    def open_regex_popup(self):
        RegexSelectionPopup(self, self.regex_var.get(), self.update_selected_regex)

    def update_selected_regex(self, new_regex):
        self.regex_var.set(new_regex)
        name = self.smart_db.get(new_regex, new_regex if new_regex else "None")
        self.regex_status_label.configure(text=f"Regex: {name}", text_color="#F1C40F" if new_regex else "#3498db")

    def clear_main_regex(self):
        """ ⭐ ฟังก์ชันสำหรับปุ่มล้างค่า Regex ที่หน้าหลัก """
        self.regex_var.set("")
        self.regex_status_label.configure(text="Regex: None", text_color="#3498db")
        self.safe_log("[*] Regex pattern cleared.")

    # --- 🚀 Threading & Loading State ---
    def start_analysis_thread(self):
        if not self.selected_file_path: return
        self.output.delete("1.0", "end")
        
        choice = self.tool_menu.get()
        self.log(f"[*] Starting {choice} on: {os.path.basename(self.selected_file_path)}\n" + "-"*60)

        self.btn_analyze.configure(state="disabled")
        self.tool_menu.configure(state="disabled")
        self.warning_label.configure(text="⏳ Processing...", text_color="#F1C40F")
        self.progress_bar.pack(side="left", padx=15)
        self.progress_bar.start()

        threading.Thread(target=self._run_analysis_logic, args=(choice,), daemon=True).start()

    def _run_analysis_logic(self, choice):
        if choice == "Magic Check": self.inspect_file_header()
        elif choice == "Executable Check": self.check_if_executable()
        elif choice == "Strings": self.extract_all_strings()
        elif choice == "zsteg Analysis": self.run_zsteg_analysis()

        self.after(0, self.finish_analysis)

    def finish_analysis(self):
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.btn_analyze.configure(state="normal")
        self.tool_menu.configure(state="normal")
        self.warning_label.configure(text="✔ Done", text_color="#2ECC71")

    # --- ⭐ Core Logic Functions ---
    def inspect_file_header(self):
        try:
            with open(self.selected_file_path, 'rb') as f:
                header_data = f.read(16)
                h_hex = header_data.hex().upper()
            
            signatures = {"4D5A": "Windows EXE", "7F454C46": "Linux ELF", "504B0304": "ZIP/Office", "FFD8FF": "JPEG", "89504E47": "PNG", "25504446": "PDF"}
            res = next((v for k, v in signatures.items() if h_hex.startswith(k)), None)
            
            if not res:
                try: ex = puremagic.from_file(self.selected_file_path); res = ex[0].name if ex else None
                except: res = None
            
            if not res:
                try: header_data.decode('utf-8'); res = "Plain Text (.txt / Code)"
                except: res = "Unknown Binary Data"
            
            self.safe_log(f"[✔] Detected Type: {res}")
        except Exception as e:
            self.safe_log(f"[!] Error: {str(e)}", "error")

    def run_zsteg_analysis(self):
        ext = os.path.splitext(self.selected_file_path)[1].lower()
        if ext not in [".png", ".bmp"]:
            self.safe_log("[!] zsteg Error: รองรับเฉพาะไฟล์ PNG และ BMP เท่านั้น", "error")
            return
        try:
            res = subprocess.run(["zsteg", self.selected_file_path], capture_output=True, text=True)
            self.safe_log(res.stdout if res.stdout else "[?] No hidden data detected.")
        except: self.safe_log("[!] zsteg command not found.", "error")

    def show_regex_info(self):
        info_window = ctk.CTkToplevel(self)
        info_window.withdraw()
        info_window.title("Regex Usage Guide")
        info_window.geometry("520x500")

        container = ctk.CTkFrame(info_window, fg_color="#1A1A1A", corner_radius=10)
        container.pack(fill="both", expand=True, padx=20, pady=20)
        ctk.CTkLabel(container, text="How to use Regular Expressions", font=("Segoe UI", 16, "bold"), text_color="#E67E22").pack(pady=15)
        guide_text = (
            "Regex คือการกำหนดรูปแบบการค้นหาข้อความ:\n\n"
            "• [a-z] : ค้นหาตัวอักษรพิมพ์เล็ก a ถึง z\n"
            "• [0-9] : ค้นหาตัวเลข 0 ถึง 9\n"
            "• .*? : แทนตัวอักษรอะไรก็ได้ (แบบสั้นที่สุด)\n"
            "• \\{..\\} : ค้นหาข้อความที่อยู่ในปีกกา\n"
            "• | : ใช้แทนคำว่า 'หรือ' (เช่น flag|ctf)\n\n"
            "💡 ตัวอย่าง Pattern ยอดนิยม:\n"
            "------------------------------------------\n"
            "1. ค้นหา Flag: FLAG\{.*?\}\n"
            "2. ค้นหาอีเมล: [a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\n"
            "3. ค้นหารหัส Hex: [a-fA-F0-9]{32}\n\n"
            "คุณสามารถก๊อปปี้ไปวางในช่อง 'Custom Regex' ได้ทันที"
        )
        ctk.CTkLabel(container, text=guide_text, justify="left", font=("Segoe UI", 12), text_color="white").pack(padx=20, pady=10)
        ctk.CTkButton(container, text="Close", width=100, command=info_window.destroy).pack(pady=15)
        
        info_window.update_idletasks()
        info_window.deiconify()
        info_window.lift()
        info_window.focus_force()

    def check_if_executable(self):
        try:
            with open(self.selected_file_path, 'rb') as f: h = f.read(4)
            res = "Linux ELF" if h == b'\x7fELF' else "Windows EXE" if h[:2] == b'MZ' else "Data File"
            self.safe_log(f"[✔] Result: {res}")
        except: pass

    def extract_all_strings(self):
        p = self.regex_var.get()
        try:
            # เช็คก่อนว่าไฟล์ว่างเปล่าหรือไม่ ป้องกัน mmap error
            file_size = os.path.getsize(self.selected_file_path)
            if file_size == 0:
                self.safe_log("[!] File is empty.")
                return

            mc = 0
            display_count = 0
            MAX_DISPLAY = 3000  #  จำกัดบรรทัดแสดงผล เพื่อไม่ให้ Tkinter ค้าง

            with open(self.selected_file_path, "rb") as f:
                # ⭐ 1. ใช้ mmap แมปไฟล์แทนการใช้ f.read() (แก้ปัญหา RAM เต็ม)
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                    
                    # ⭐ 2. ใช้ finditer แทน findall เพื่อดึงข้อมูลทีละบรรทัด ไม่สร้าง List ก้อนใหญ่
                    found_iter = re.finditer(rb"[ -~]{4,}", mm)
                    
                    for match in found_iter:
                        # ⭐ 3. หยุดแสดงผลถ้าเกินลิมิต ป้องกันหน้าจอ GUI ค้าง
                        if display_count >= MAX_DISPLAY:
                            self.safe_log(f"\n[⚠️] File is very large. Showing top {MAX_DISPLAY} results to prevent UI freeze...", "error")
                            break

                        s = match.group()
                        line = s.decode(errors="ignore")
                        
                        if p:
                            matches = list(re.finditer(p, line, re.IGNORECASE))
                            if matches:
                                mc += len(matches)
                                
                                self.safe_log("🚩 [MATCH]: ", newline=False)
                                
                                lp = 0
                                for m in matches: 
                                    st, en = m.span()
                                    self.safe_log(line[lp:st], newline=False)
                                    self.safe_log(line[st:en], "found", newline=False)
                                    lp = en
                                self.safe_log(line[lp:])
                                display_count += 1
                        else: 
                            self.safe_log(f"  {line}")
                            display_count += 1
                            
            if p: 
                self.after(0, lambda: self.warning_label.configure(text=f"🚩 Found {mc} matches", text_color="#2ECC71"))
        except Exception as e: 
            self.safe_log(f"[!] Strings Error: {str(e)}", "error")

    # --- UI Updaters ---
    def log(self, msg, tag=None, newline=True):
        self.output.insert("end", msg + ("\n" if newline else ""), tag)
        self.output.see("end")

    def safe_log(self, msg, tag=None, newline=True):
        self.after(0, lambda: self.log(msg, tag, newline))

    def send_selection(self):
        try:
            sel = self.output.get("sel.first", "sel.last").strip()
            if sel and hasattr(self.app_root, "send_to_hashing"): self.app_root.send_to_hashing(sel)
        except: pass
        
    def show_context_menu(self, e):
        if self.output.tag_ranges("sel"): self.context_menu.tk_popup(e.x_root, e.y_root)