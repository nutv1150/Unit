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

# ==========================================
# ธีมสีหลัก (Cyberpunk / Terminal)
# ==========================================
BG_COLOR = "#0D0D12"        
PANEL_COLOR = "#15151E"     
ACCENT_CYAN = "#00FFFF"     
ACCENT_GREEN = "#00FF41"    
TEXT_DIM = "#8892B0"        
ALERT_RED = "#FF3366"       

# --- ⭐ 1. คลาสสำหรับการสร้าง "กรอบ" ผลลัพธ์แยกแต่ละไฟล์ ---
class ResultBox(ctk.CTkFrame):
    def __init__(self, master, filename, app_root, **kwargs):
        super().__init__(master, border_width=1, border_color="#333344", corner_radius=6, fg_color="#0A0A0F", **kwargs)
        
        self.header = ctk.CTkFrame(self, fg_color="#1E1E2E", corner_radius=4, height=35)
        self.header.pack(fill="x", padx=1, pady=1)
        self.header.pack_propagate(False)
        
        self.title = ctk.CTkLabel(self.header, text=f" 📄 {filename} ", font=("Consolas", 13, "bold"), text_color=ACCENT_CYAN)
        self.title.pack(side="left", padx=10, pady=5)
        
        self.textbox = ctk.CTkTextbox(
            self, fg_color="#050508", text_color=ACCENT_GREEN, 
            font=("Consolas", 12), height=180, border_width=0
        )
        self.textbox.pack(fill="both", expand=True, padx=2, pady=(0, 2))
        
        self.textbox.tag_config("found", background=ACCENT_CYAN, foreground="#000000")
        self.textbox.tag_config("error", foreground=ALERT_RED)
        
        self.app_root = app_root
        self.context_menu = Menu(self, tearoff=0, bg=PANEL_COLOR, fg="white", activebackground=ACCENT_CYAN, activeforeground="black", font=("Consolas", 10))
        self.context_menu.add_command(label="🚀 FORWARD TO HASHING MODULE", command=self.send_selection)
        self.textbox.bind("<Button-3>", self.show_context_menu)

    def send_selection(self):
        try:
            sel = self.textbox.get("sel.first", "sel.last").strip()
            if sel and hasattr(self.app_root, "send_to_hashing"):
                self.app_root.send_to_hashing(sel)
        except: pass
        
    def show_context_menu(self, e):
        if self.textbox.tag_ranges("sel"):
            self.context_menu.tk_popup(e.x_root, e.y_root)


# --- ⭐ 2. หน้าต่าง Popup สำหรับเลือก Regex ---
class RegexSelectionPopup(ctk.CTkToplevel):
    def __init__(self, parent, current_regex, callback):
        super().__init__(parent)
        self.withdraw()
        self.title("SELECT REGEX PATTERN :: [CONFIG]")
        self.geometry("650x580")
        self.configure(fg_color=BG_COLOR)
        
        self.callback = callback
        self.parent = parent
        self.smart_db = parent.smart_db
        self.regex_previews = parent.regex_previews
        self.regex_var = ctk.StringVar(value=current_regex)
        self.regex_radios = []

        ctk.CTkLabel(self, text=">_ REGEX_PATTERN_SELECTOR", font=("Consolas", 20, "bold"), text_color=ACCENT_CYAN).pack(pady=15)

        self.preview_box = ctk.CTkFrame(self, fg_color=PANEL_COLOR, border_width=1, border_color=ACCENT_CYAN, height=70, corner_radius=4)
        self.preview_box.pack(fill="x", padx=20, pady=5)
        self.preview_box.pack_propagate(False)
        self.hover_label = ctk.CTkLabel(self.preview_box, text="[!] HOVER OVER AN OPTION TO VIEW DETAILS", font=("Consolas", 12), text_color=TEXT_DIM) 
        self.hover_label.pack(expand=True)

        custom_frame = ctk.CTkFrame(self, fg_color="transparent")
        custom_frame.pack(fill="x", padx=20, pady=10)

        row1 = ctk.CTkFrame(custom_frame, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 5))
        self.custom_name_entry = ctk.CTkEntry(row1, placeholder_text="PATTERN_NAME", font=("Consolas", 12), width=160, height=35, fg_color="#0A0A0F", border_color="#333344", text_color=ACCENT_CYAN)
        self.custom_name_entry.pack(side="left", padx=(0, 5))
        self.custom_regex_entry = ctk.CTkEntry(row1, placeholder_text="ENTER CUSTOM REGEX HERE (*REQUIRED)", font=("Consolas", 12), height=35, fg_color="#0A0A0F", border_color="#333344", text_color=ACCENT_CYAN)
        self.custom_regex_entry.pack(side="left", fill="x", expand=True)

        row2 = ctk.CTkFrame(custom_frame, fg_color="transparent")
        row2.pack(fill="x")
        self.custom_desc_entry = ctk.CTkEntry(row2, placeholder_text="DESCRIPTION (OPTIONAL)", font=("Consolas", 12), height=35, fg_color="#0A0A0F", border_color="#333344", text_color=TEXT_DIM)
        self.custom_desc_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        ctk.CTkButton(row2, text="[ ADD ]", font=("Consolas", 12, "bold"), width=70, height=35, fg_color="transparent", border_width=1, border_color=ACCENT_GREEN, text_color=ACCENT_GREEN, hover_color="#003311", command=self.add_custom_regex).pack(side="left", padx=2)
        ctk.CTkButton(row2, text="[ ? ]", font=("Consolas", 12, "bold"), width=40, height=35, fg_color="transparent", border_width=1, border_color=TEXT_DIM, text_color=TEXT_DIM, hover_color="#2B2B36", command=parent.show_regex_info).pack(side="left", padx=2)

        self.scroll_frame = ctk.CTkScrollableFrame(self, height=180, fg_color="#0A0A0F", border_width=1, border_color="#333344", corner_radius=4)
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

        for p in self.smart_db.keys():
            self.create_preview_radio(p)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=15)
        
        ctk.CTkButton(btn_frame, text="CONFIRM", font=("Consolas", 12, "bold"), fg_color=ACCENT_CYAN, text_color="black", hover_color="#00CCCC", command=self.confirm).pack(side="right", padx=5)
        ctk.CTkButton(btn_frame, text="CLEAR", font=("Consolas", 12, "bold"), fg_color="transparent", border_width=1, border_color=TEXT_DIM, text_color=TEXT_DIM, hover_color="#2B2B36", command=self.clear_selection).pack(side="right", padx=5)
        ctk.CTkButton(btn_frame, text="CANCEL", font=("Consolas", 12, "bold"), fg_color="transparent", border_width=1, border_color=ALERT_RED, text_color=ALERT_RED, hover_color="#4A0011", command=self.destroy).pack(side="right", padx=5)

        self.update_idletasks() 
        self.deiconify()        
        self.lift()             
        self.focus_force()      

    def create_preview_radio(self, p):
        n = self.smart_db.get(p, p)
        rb = ctk.CTkRadioButton(
            self.scroll_frame, text=f" {n}", font=("Consolas", 12), variable=self.regex_var, 
            value=p, text_color="white", fg_color=ACCENT_CYAN, hover_color=ACCENT_GREEN
        )
        rb.pack(anchor="w", padx=15, pady=8)
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
                display_name = name if name else "🛠 CUSTOM_PATTERN"
                self.smart_db[p] = display_name
                desc_text = f"{desc}\n" if desc else ""
                self.regex_previews[p] = f"🛠 {display_name}\n{desc_text}Regex: {p}"
                
                self.parent.smart_db[p] = display_name
                self.parent.regex_previews[p] = self.regex_previews[p]
                
                self.create_preview_radio(p)
                self.custom_regex_entry.delete(0, "end")
                self.custom_name_entry.delete(0, "end")
                self.custom_desc_entry.delete(0, "end")
            except Exception as e: pass

    def clear_selection(self):
        self.regex_var.set("")
        for rb in self.regex_radios: rb.deselect()

    def show_preview(self, p):
        txt = self.regex_previews.get(p, f"Custom: {p}")
        self.hover_label.configure(text=txt, text_color=ACCENT_GREEN)

    def hide_preview(self):
        self.hover_label.configure(text="[!] HOVER OVER AN OPTION TO VIEW DETAILS", text_color=TEXT_DIM)

    def confirm(self):
        self.callback(self.regex_var.get())
        self.destroy()


# --- ⭐ 3. หน้าหลัก File Inspection ---
class FileInspectionPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.app_root = master.master 
        self.configure(fg_color=BG_COLOR)
        
        self.selected_files = [] 
        self.regex_var = ctk.StringVar(value="") 

        self.smart_db = {
            r"(?:0|\+66)[689]\d[- \.]?\d{3}[- \.]?\d{4}": "📱 THAI_MOBILE_NUM",
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}": "📧 EMAIL_ADDR",
            r"(?:\d{1,3}\.){3}\d{1,3}": "🌐 IPv4_ADDR",
            r"https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}": "🔗 URL_LINK",
            r"[a-fA-F0-9]{32}": "🔑 MD5_HASH",
            r"FLAG\{.*?\}": "🚩 STD_FLAG",
            r"(flag|ctf|picoCTF)\{[^}]+\}": "🚩 MULTI_CTF_FLAG"
        }

        self.regex_previews = {
            r"(?:0|\+66)[689]\d[- \.]?\d{3}[- \.]?\d{4}": "📱 THAI_MOBILE_NUM\nFind Thai mobile numbers (08x, 09x, 06x)",
            r"FLAG\{.*?\}": "🎯 STD_FLAG\nStandard CTF flag format",
            r"(flag|ctf|picoCTF)\{[^}]+\}": "🌐 MULTI_CTF_FLAG\nCommon CTF platform formats (pico, HTB, etc.)",
            "": "💡 HOVER FOR DETAILS"
        }

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1) 

        # 1. Header 
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=30, pady=(20, 5))
        ctk.CTkLabel(header_frame, text=">_ DATA_INSPECTOR :: [BATCH_SCAN]", font=("Consolas", 28, "bold"), text_color=ACCENT_CYAN).pack(side="left")

        # 2. 🚀 Drag & Drop Zone 
        self.drop_zone = ctk.CTkFrame(self, fg_color="#0A0A0F", corner_radius=4, border_width=1, border_color="#333344")
        self.drop_zone.grid(row=1, column=0, sticky="ew", padx=30, pady=10)
        self.drop_zone.drop_target_register(DND_FILES)
        self.drop_zone.dnd_bind('<<Drop>>', self.on_drop)

        drop_inner = ctk.CTkFrame(self.drop_zone, fg_color="transparent")
        drop_inner.pack(pady=20)
        
        self.file_icon_label = ctk.CTkLabel(drop_inner, text="[ DROP_TARGET ]", font=("Consolas", 14, "bold"), text_color=TEXT_DIM)
        self.file_icon_label.pack(side="left", padx=10)
        self.file_label = ctk.CTkLabel(drop_inner, text="DRAG & DROP FILE(S) HERE OR CLICK TO BROWSE", text_color=TEXT_DIM, font=("Consolas", 12))
        self.file_label.pack(side="left", padx=10)
        ctk.CTkButton(drop_inner, text="[ BROWSE ]", font=("Consolas", 12, "bold"), fg_color="transparent", border_width=1, border_color=ACCENT_CYAN, text_color=ACCENT_CYAN, hover_color="#003344", width=100, command=self.browse_file).pack(side="left", padx=10)

        # 3. 📊 File Metadata Card 
        self.meta_frame = ctk.CTkFrame(self, fg_color=PANEL_COLOR, height=45, corner_radius=4, border_width=1, border_color="#333344")
        self.meta_frame.grid(row=2, column=0, sticky="ew", padx=30, pady=5)
        self.meta_frame.grid_remove() 

        self.meta_size = ctk.CTkLabel(self.meta_frame, text="[SIZE]: --", font=("Consolas", 12, "bold"), text_color=ACCENT_CYAN)
        self.meta_size.pack(side="left", padx=15, pady=10)
        self.meta_ext = ctk.CTkLabel(self.meta_frame, text="[EXT]: --", font=("Consolas", 12, "bold"), text_color="#FFB800")
        self.meta_ext.pack(side="left", padx=15, pady=10)
        self.meta_md5 = ctk.CTkLabel(self.meta_frame, text="[MD5]: --", font=("Consolas", 12), text_color=TEXT_DIM)
        self.meta_md5.pack(side="left", padx=15, pady=10)

        # 4. Action Panel
        action_frame = ctk.CTkFrame(self, fg_color=PANEL_COLOR, corner_radius=4, border_width=1, border_color="#333344")
        action_frame.grid(row=3, column=0, sticky="ew", padx=30, pady=10)

        self.tool_menu = ctk.CTkOptionMenu(
            action_frame, values=["Header Check", "Executable Check", "Strings", "zsteg Analysis"], 
            width=180, height=35, font=("Consolas", 12),
            fg_color="#1E1E2E", button_color="#2B2B36", button_hover_color="#3A3A4A",
            state="disabled", command=self.toggle_regex_button
        )
        self.tool_menu.pack(side="left", padx=15, pady=15)

        self.btn_analyze = ctk.CTkButton(
            action_frame, text="[ EXECUTE ]", width=120, height=35, 
            font=("Consolas", 12, "bold"), fg_color=ACCENT_CYAN, text_color="black", hover_color="#00CCCC",
            state="disabled", command=self.start_analysis_thread
        )
        self.btn_analyze.pack(side="left", padx=5)

        self.btn_regex_popup = ctk.CTkButton(
            action_frame, text="⚙️ CFG_REGEX", width=120, height=35,
            font=("Consolas", 12, "bold"), fg_color="transparent", border_width=1, border_color=ACCENT_GREEN, text_color=ACCENT_GREEN, hover_color="#003311",
            state="disabled", command=self.open_regex_popup
        )
        self.btn_regex_popup.pack(side="left", padx=(15, 5))

        self.btn_clear_regex = ctk.CTkButton(
            action_frame, text="[X]", width=40, height=35, 
            font=("Consolas", 12, "bold"), fg_color="transparent", border_width=1, border_color=ALERT_RED, text_color=ALERT_RED, hover_color="#4A0011",
            state="disabled", command=self.clear_main_regex
        )
        self.btn_clear_regex.pack(side="left", padx=0)

        self.progress_bar = ctk.CTkProgressBar(action_frame, mode="indeterminate", width=120, progress_color=ACCENT_CYAN, fg_color="#2B2B36")
        self.progress_bar.pack(side="left", padx=15)
        self.progress_bar.pack_forget() 

        self.warning_label = ctk.CTkLabel(action_frame, text="STATUS: IDLE", text_color=TEXT_DIM, font=("Consolas", 12, "bold"))
        self.warning_label.pack(side="right", padx=(10, 20))

        self.regex_status_label = ctk.CTkLabel(
            action_frame, text=" 🔍 REGEX: NONE ", font=("Consolas", 12, "bold"), 
            fg_color="#0A0A0F", text_color=TEXT_DIM, corner_radius=4, width=150, height=30
        )
        self.regex_status_label.pack(side="right", padx=10)

        # =========================================================================
        # 5. Output Container (Split View)
        # =========================================================================
        output_header = ctk.CTkFrame(self, fg_color="transparent")
        output_header.grid(row=4, column=0, sticky="ew", padx=30, pady=(5, 0))
        ctk.CTkLabel(output_header, text=">_ ANALYSIS_OUTPUT", font=("Consolas", 14, "bold"), text_color=ALERT_RED).pack(side="left")
        ctk.CTkButton(output_header, text="[ CLEAR_ALL ]", font=("Consolas", 12, "bold"), width=100, height=28, fg_color="transparent", border_width=1, border_color=ALERT_RED, text_color=ALERT_RED, hover_color="#4A0011", command=self.clear_terminal).pack(side="right")

        self.output_container = ctk.CTkFrame(self, fg_color="transparent")
        self.output_container.grid(row=5, column=0, sticky="nsew", padx=30, pady=(5, 20))
        self.output_container.grid_columnconfigure(1, weight=1)
        self.output_container.grid_rowconfigure(0, weight=1)

        self.file_nav_panel = ctk.CTkScrollableFrame(self.output_container, width=220, fg_color=PANEL_COLOR, border_width=1, border_color="#333344", corner_radius=4)
        self.file_nav_panel.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        ctk.CTkLabel(self.file_nav_panel, text="[ OUTPUT_FILTER ]", font=("Consolas", 12, "bold"), text_color=TEXT_DIM).pack(pady=(5, 10))

        self.results_scroll = ctk.CTkScrollableFrame(self.output_container, fg_color="#050508", border_width=1, border_color="#333344", corner_radius=4)
        self.results_scroll.grid(row=0, column=1, sticky="nsew")

        self.result_boxes = {}  
        self.nav_buttons = {}   
        self.current_view_id = "ALL"


    # ==================================================================
    # ⬇️ MULTI-VIEW TERMINAL LOGIC (สร้างกรอบแยก) ⬇️
    # ==================================================================

    def populate_file_nav(self):
        for widget in self.file_nav_panel.winfo_children():
            if isinstance(widget, ctk.CTkButton): widget.destroy()
                
        for box in self.result_boxes.values(): box.destroy()
        
        self.result_boxes.clear()
        self.nav_buttons.clear()

        btn_all = ctk.CTkButton(
            self.file_nav_panel, text="🌟 [ ALL_RESULTS ]", anchor="w", font=("Consolas", 12, "bold"),
            fg_color="transparent", hover_color="#2B2B36", text_color=TEXT_DIM,
            command=lambda: self.switch_view("ALL")
        )
        btn_all.pack(fill="x", pady=2, padx=5)
        self.nav_buttons["ALL"] = btn_all

        for path in self.selected_files:
            filename = os.path.basename(path)
            
            btn = ctk.CTkButton(
                self.file_nav_panel, text=f"📄 {filename}", anchor="w", font=("Consolas", 11),
                fg_color="transparent", hover_color="#2B2B36", text_color="white",
                command=lambda p=path: self.switch_view(p)
            )
            btn.pack(fill="x", pady=2, padx=5)
            self.nav_buttons[path] = btn
            
            box = ResultBox(self.results_scroll, filename, self.app_root)
            self.result_boxes[path] = box

        for btn in self.nav_buttons.values():
            btn.bind("<Button-4>", lambda e: self.file_nav_panel._parent_canvas.yview_scroll(-1, "units"))
            btn.bind("<Button-5>", lambda e: self.file_nav_panel._parent_canvas.yview_scroll(1, "units"))
            btn.bind("<MouseWheel>", lambda e: self.file_nav_panel._parent_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        self.switch_view("ALL")

    def switch_view(self, target_id):
        self.current_view_id = target_id
        
        for t_id, btn in self.nav_buttons.items():
            if t_id == target_id:
                btn.configure(fg_color=ACCENT_CYAN, text_color="black")
            else:
                btn.configure(fg_color="transparent", text_color="white" if t_id != "ALL" else TEXT_DIM)
                
        for path, box in self.result_boxes.items():
            if target_id == "ALL" or target_id == path:
                box.pack(fill="x", padx=10, pady=(10, 5)) 
            else:
                box.pack_forget() 

        try:
            self.results_scroll._parent_canvas.yview_moveto(0)
        except:
            pass

    def log(self, msg, tag=None, newline=True, target_file=None):
        txt = msg + ("\n" if newline else "")
        if target_file and target_file in self.result_boxes:
            tb = self.result_boxes[target_file].textbox
            tb.insert("end", txt, tag)
            tb.see("end")

    def safe_log(self, msg, tag=None, newline=True, target_file=None):
        self.after(0, lambda: self.log(msg, tag, newline, target_file))

    def clear_terminal(self):
        for box in self.result_boxes.values():
            box.textbox.delete("1.0", "end")

    # ==================================================================
    # ⬇️ BATCH LOGIC FUNCTIONS (รองรับหลายไฟล์) ⬇️
    # ==================================================================

    def on_drop(self, event):
        raw_paths = self.tk.splitlist(event.data)
        self.load_files(raw_paths)

    def browse_file(self):
        paths = filedialog.askopenfilenames()
        if paths: self.load_files(paths)

    def load_files(self, paths):
        valid_paths = [p for p in paths if os.path.exists(p)]
        if not valid_paths: return
        
        self.selected_files = valid_paths
        self.drop_zone.configure(border_color=ACCENT_CYAN)
        
        if len(self.selected_files) == 1:
            self.file_icon_label.configure(text="[ TARGET_LOCKED ]", text_color=ACCENT_CYAN)
            self.file_label.configure(text=f"{os.path.basename(self.selected_files[0])}", text_color="white")
        else:
            self.file_icon_label.configure(text="[ BATCH_LOCKED ]", text_color=ACCENT_CYAN)
            self.file_label.configure(text=f"[ {len(self.selected_files)} FILES SELECTED ]", text_color="white")
        
        self.tool_menu.configure(state="normal")
        self.btn_analyze.configure(state="normal")
        self.toggle_regex_button(self.tool_menu.get())

        self.update_metadata_card()

    def format_size(self, size_bytes):
        if size_bytes < 1024: return f"{size_bytes} B"
        elif size_bytes < 1024**2: return f"{size_bytes/1024:.2f} KB"
        else: return f"{size_bytes/(1024**2):.2f} MB"

    def update_metadata_card(self):
        self.meta_frame.grid() 
        if len(self.selected_files) == 1:
            path = self.selected_files[0]
            size_bytes = os.path.getsize(path)
            size_str = self.format_size(size_bytes)
            ext = os.path.splitext(path)[1].lower() or "Unknown"
            threading.Thread(target=self._calc_md5, args=(path, size_str, ext), daemon=True).start()
        else:
            total_bytes = sum(os.path.getsize(p) for p in self.selected_files)
            size_str = self.format_size(total_bytes)
            self.meta_size.configure(text=f"[TOTAL_SIZE]: {size_str}")
            self.meta_ext.configure(text=f"[MODE]: BATCH_PROCESSING")
            self.meta_md5.configure(text=f"[MD5]: N/A (MULTIPLE FILES)")

    def _calc_md5(self, path, size_str, ext):
        md5 = hashlib.md5()
        try:
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""): md5.update(chunk)
            result = md5.hexdigest()
        except: result = "Error"
        self.after(0, lambda: self._update_meta_ui(size_str, ext, result))
        
    def _update_meta_ui(self, size_str, ext, md5_str):
        self.meta_size.configure(text=f"[SIZE]: {size_str}")
        self.meta_ext.configure(text=f"[EXT]: {ext}")
        self.meta_md5.configure(text=f"[MD5]: {md5_str}")

    def toggle_regex_button(self, mode):
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
        if new_regex:
            self.regex_status_label.configure(text=f" 🎯 FILTER: {name} ", fg_color=ACCENT_CYAN, text_color="black")
        else:
            self.regex_status_label.configure(text=" 🔍 REGEX: NONE ", fg_color="#0A0A0F", text_color=TEXT_DIM)

    def clear_main_regex(self):
        self.regex_var.set("")
        self.regex_status_label.configure(text=" 🔍 REGEX: NONE ", fg_color="#0A0A0F", text_color=TEXT_DIM)

    def start_analysis_thread(self):
        if not self.selected_files: return
        
        self.populate_file_nav()
        
        choice = self.tool_menu.get()
        self.btn_analyze.configure(state="disabled")
        self.tool_menu.configure(state="disabled")
        self.warning_label.configure(text="STATUS: PROCESSING...", text_color="#FFB800")
        self.progress_bar.pack(side="left", padx=15)
        self.progress_bar.start()

        threading.Thread(target=self._run_analysis_logic, args=(choice,), daemon=True).start()

    def _run_analysis_logic(self, choice):
        state = {'match_count': 0, 'display_count': 0, 'max_display': 3000, 'warned': False}

        for path in self.selected_files:
            if choice == "Strings" and not self.regex_var.get() and state['warned']:
                break
            
            if choice == "Header Check": self.inspect_file_header(path)
            elif choice == "Executable Check": self.check_if_executable(path)
            elif choice == "Strings": self.extract_all_strings(path, state)
            elif choice == "zsteg Analysis": self.run_zsteg_analysis(path)

        self.after(0, lambda: self.finish_analysis(choice, state['match_count']))

    def check_if_executable(self, path):
        try:
            with open(path, 'rb') as f: h = f.read(4)
            if h == b'\x7fELF': res = "Linux ELF (Executable)"
            elif h[:2] == b'MZ': res = "Windows EXE (Executable)"
            else: res = "Data File (Non-Executable)"
            self.safe_log(f"[+] RESULT: {res}", target_file=path)
        except Exception as e:
            self.safe_log(f"[!] EXECUTABLE CHECK ERROR: {str(e)}", "error", target_file=path)

    def inspect_file_header(self, path):
        try:
            with open(path, 'rb') as f:
                header_data = f.read(16)
                h_hex = header_data.hex().upper()
            
            signatures = {"4D5A": "Windows EXE", "7F454C46": "Linux ELF", "504B0304": "ZIP/Office", "FFD8FF": "JPEG", "89504E47": "PNG", "25504446": "PDF"}
            res = next((v for k, v in signatures.items() if h_hex.startswith(k)), None)
            
            if not res:
                try: ex = puremagic.from_file(path); res = ex[0].name if ex else None
                except: res = None
            if not res:
                try: header_data.decode('utf-8'); res = "Plain Text (.txt / Code)"
                except: res = "Unknown Binary Data"
            
            self.safe_log(f"[+] DETECTED TYPE: {res}", target_file=path)
        except Exception as e:
            self.safe_log(f"[!] ERROR: {str(e)}", "error", target_file=path)

    def run_zsteg_analysis(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext not in [".png", ".bmp"]:
            self.safe_log("[!] ZSTEG ERROR: TARGET MUST BE PNG OR BMP", "error", target_file=path)
            return
        try:
            res = subprocess.run(["zsteg", path], capture_output=True, text=True)
            self.safe_log(res.stdout if res.stdout else "[?] NO HIDDEN DATA DETECTED.", target_file=path)
        except: self.safe_log("[!] ZSTEG COMMAND NOT FOUND IN SYSTEM PATH.", "error", target_file=path)

    def extract_all_strings(self, path, state):
        p = self.regex_var.get()
        try:
            file_size = os.path.getsize(path)
            if file_size == 0:
                self.safe_log("[!] TARGET FILE IS EMPTY.", target_file=path)
                return

            with open(path, "rb") as f:
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                    found_iter = re.finditer(rb"[ -~]{4,}", mm)
                    
                    for match in found_iter:
                        # หยุดถ้าแสดงผลครบลิมิตแล้ว (ถ้ามี p ให้ทำงานเงียบๆ ต่อเพื่อเก็บยอด match_count)
                        if state['display_count'] >= state['max_display'] and not p:
                            if not state['warned']:
                                self.safe_log(f"\n[⚠️] REACHED BATCH DISPLAY LIMIT ({state['max_display']}). HALTING TO PREVENT HANG.", "error", target_file=path)
                                state['warned'] = True
                            break 

                        s = match.group()
                        line = s.decode(errors="ignore")
                        
                        matches = []
                        if p:
                            matches = list(re.finditer(p, line, re.IGNORECASE))
                            if matches:
                                state['match_count'] += len(matches)
                                
                        if state['display_count'] < state['max_display']:
                            if matches:
                                # ไฮไลท์เฉพาะบรรทัดที่เจอ (สาดสีฟ้า)
                                self.safe_log("  ", newline=False, target_file=path)
                                lp = 0
                                for m in matches: 
                                    st, en = m.span()
                                    self.safe_log(line[lp:st], newline=False, target_file=path)
                                    self.safe_log(line[st:en], "found", newline=False, target_file=path)
                                    lp = en
                                self.safe_log(line[lp:], target_file=path)
                            else:
                                # บรรทัดปกติ พิมพ์ออกมาตามปกติ
                                self.safe_log(f"  {line}", target_file=path)
                                
                            state['display_count'] += 1
                        elif state['display_count'] == state['max_display']:
                            if not state['warned']:
                                self.safe_log(f"\n[⚠️] REACHED DISPLAY LIMIT ({state['max_display']}). PROCESSING REMAINDER IN BACKGROUND...", "error", target_file=path)
                                state['warned'] = True
                            state['display_count'] += 1 
                                
        except Exception as e: 
            self.safe_log(f"[!] STRINGS EXTRACTION ERROR: {str(e)}", "error", target_file=path)

    def finish_analysis(self, choice, total_matches):
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.btn_analyze.configure(state="normal")
        self.tool_menu.configure(state="normal")
        
        if choice == "Strings" and self.regex_var.get():
            self.warning_label.configure(text=f"STATUS: FOUND {total_matches} MATCHES", text_color=ACCENT_GREEN)
        else:
            self.warning_label.configure(text="STATUS: COMPLETE", text_color=ACCENT_GREEN)

    def show_regex_info(self):
        info_window = ctk.CTkToplevel(self)
        info_window.withdraw()
        info_window.title("SYS_MANUAL :: REGEX")
        info_window.geometry("520x500")
        info_window.configure(fg_color=BG_COLOR)

        container = ctk.CTkFrame(info_window, fg_color=PANEL_COLOR, corner_radius=4, border_width=1, border_color=ACCENT_CYAN)
        container.pack(fill="both", expand=True, padx=20, pady=20)
        ctk.CTkLabel(container, text="[ REGULAR_EXPRESSION_GUIDE ]", font=("Consolas", 16, "bold"), text_color=ACCENT_CYAN).pack(pady=15)
        guide_text = (
            "Syntax references for pattern matching:\n\n"
            "• [a-z] : Match lowercase a to z\n"
            "• [0-9] : Match digits 0 to 9\n"
            "• .*?   : Non-greedy match anything\n"
            "• \\{..\\} : Match curly braces (escape required)\n"
            "• |     : OR operator (e.g., flag|ctf)\n\n"
            "💡 COMMON EXAMPLES:\n"
            "------------------------------------------\n"
            "1. FLAG FORMAT: FLAG\\{.*?\\}\n"
            "2. EMAIL ADDR.: [a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\n"
            "3. MD5 HASH   : [a-fA-F0-9]{32}\n\n"
            ">_ Copy and paste into Custom Regex field."
        )
        ctk.CTkLabel(container, text=guide_text, justify="left", font=("Consolas", 12), text_color="white").pack(padx=20, pady=10)
        ctk.CTkButton(container, text="[ CLOSE ]", width=100, font=("Consolas", 12, "bold"), fg_color="transparent", border_width=1, border_color=ALERT_RED, text_color=ALERT_RED, hover_color="#4A0011", command=info_window.destroy).pack(pady=15)
        
        info_window.update_idletasks()
        info_window.deiconify()
        info_window.lift()
        info_window.focus_force()