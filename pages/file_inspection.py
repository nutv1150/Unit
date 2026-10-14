import customtkinter as ctk
from tkinter import filedialog, Menu, TclError
from tkinterdnd2 import DND_FILES
import puremagic
import os
import re
import subprocess
import threading
import hashlib
import mmap  
import queue
import uuid
import tempfile
import shutil
import io
import codecs
from pathlib import Path

from Tools.flag_detector import UNIVERSAL_FLAG_REGEX, find_flags
from Tools import history_hooks
from Tools.window_layout import fit_window
from Tools.stream_capture import run_capture
from Tools.text_view import save_async, open_text_view

# ==========================================
# ธีมสีหลัก (Cyberpunk / Terminal)
# ==========================================
BG_COLOR = "#0D0D12"        
PANEL_COLOR = "#15151E"     
ACCENT_CYAN = "#00FFFF"     
ACCENT_GREEN = "#00FF41"    
TEXT_DIM = "#8892B0"        
ALERT_RED = "#FF3366"       


class _OutputDirectory:
    """Shared lifetime for a worker, its result panels and open full viewers."""
    def __init__(self, prefix):
        self.name = tempfile.mkdtemp(prefix=prefix)

    def cleanup(self):
        shutil.rmtree(self.name, ignore_errors=True)

    def __del__(self):
        self.cleanup()

# --- ⭐ 1. คลาสสำหรับการสร้าง "กรอบ" ผลลัพธ์ ---
class ResultBox(ctk.CTkFrame):
    def __init__(self, master, filename, app_root, **kwargs):
        super().__init__(master, border_width=1, border_color="#333344", corner_radius=6, fg_color="#0A0A0F", **kwargs)
        
        self.header = ctk.CTkFrame(self, fg_color="#1E1E2E", corner_radius=4, height=35)
        self.header.pack(fill="x", padx=1, pady=1)
        self.header.pack_propagate(False)
        
        self.title = ctk.CTkLabel(self.header, text=f" 📄 {filename} ", font=("Consolas", 13, "bold"), text_color=ACCENT_CYAN)
        self.title.pack(side="left", padx=10, pady=5)
        
        # ลดความสูง (height) จาก 350 เหลือ 280
        self.textbox = ctk.CTkTextbox(
            self, fg_color="#050508", text_color=ACCENT_GREEN, 
            font=("Consolas", 12), height=280, border_width=0
        )
        self.textbox.pack(fill="both", expand=True, padx=2, pady=(0, 2))
        
        self.textbox.tag_config("found", background=ACCENT_CYAN, foreground="#000000")
        self.textbox.tag_config("highlight", background="#FFB800", foreground="#000000") 
        self.textbox.tag_config("error", foreground=ALERT_RED)
        
        self.app_root = app_root
        self.full_output_path = None
        self.preview_bytes = 128 * 1024
        self._preview_bytes_used = 0
        self.save_button = ctk.CTkButton(
            self.header, text="SAVE FULL OUTPUT", width=135, height=25,
            font=("Consolas", 10, "bold"), fg_color="transparent",
            border_width=1, border_color=ACCENT_GREEN, text_color=ACCENT_GREEN,
            hover_color="#003311", command=self.save_full_output,
        )
        self.save_button.pack(side="right", padx=8)
        self.view_button = ctk.CTkButton(
            self.header, text="VIEW FULL OUTPUT", width=135, height=25,
            font=("Consolas", 10, "bold"), fg_color="transparent",
            border_width=1, border_color=ACCENT_CYAN, text_color=ACCENT_CYAN,
            hover_color="#003344", command=self.view_full_output,
        )
        self.view_button.pack(side="right", padx=2)
        self.context_menu = Menu(self, tearoff=0, bg=PANEL_COLOR, fg="white", activebackground=ACCENT_CYAN, activeforeground="black", font=("Consolas", 10))
        self.context_menu.add_command(label="🚀 FORWARD TO HASHING MODULE", command=self.send_selection)
        self.gemini_selection = ""
        self.context_menu.add_command(label="🚀 FORWARD TO GEMINI MODULE", command=self.send_selection_to_gemini)
        self.textbox.bind("<Button-3>", self.show_context_menu)

    def set_full_output_path(self, path):
        self.full_output_path = path
        self._preview_bytes_used = 0
        self.save_button.configure(state='disabled')
        self.view_button.configure(state='disabled')

    def reset_output(self):
        self._preview_bytes_used = 0
        self.textbox.delete("1.0", "end")

    def save_full_output(self):
        if not self.full_output_path or not os.path.isfile(self.full_output_path):
            return
        destination = filedialog.asksaveasfilename(
            title="Save full inspection output", initialfile=os.path.basename(self.title.cget("text")).strip(" 📄") + ".txt",
            defaultextension=".txt", filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if destination:
            event_id = getattr(self, 'history_id', None)
            save_async(self, Path(self.full_output_path), destination,
                       lambda: history_hooks.attach_file(self.app_root, event_id, destination),
                       owner=getattr(self, '_output_owner', None))

    def view_full_output(self):
        if self.full_output_path and os.path.isfile(self.full_output_path):
            open_text_view(self, self.full_output_path, owner=getattr(self, '_output_owner', None))

    def insert_preview(self, text, tag=None):
        if not text or self._preview_bytes_used >= self.preview_bytes:
            return
        remaining = self.preview_bytes - self._preview_bytes_used
        encoded = text.encode("utf-8", errors="replace")
        if len(encoded) > remaining:
            text = encoded[:remaining].decode("utf-8", errors="ignore")
            text += "\n[⚠️] PREVIEW TRUNCATED — USE SAVE FULL OUTPUT FOR COMPLETE RESULTS.\n"
        self._preview_bytes_used += len(text.encode("utf-8", errors="replace"))
        self.textbox.insert("end", text, tag)
        self.textbox.see("end")

    def send_selection(self):
        try:
            sel = self.textbox.get("sel.first", "sel.last").strip()
            if sel and hasattr(self.app_root, "send_to_hashing"):
                source = getattr(self, 'history_id', None)
                if source:
                    self.app_root.send_to_hashing(sel, source_history_id=source)
                else:
                    self.app_root.send_to_hashing(sel)
        except: pass
        
    def show_context_menu(self, e):
        try:
            self.gemini_selection = self.textbox.get("sel.first", "sel.last")
        except TclError:
            self.gemini_selection = ""
        if self.gemini_selection.strip():
            try:
                self.context_menu.tk_popup(e.x_root, e.y_root)
            finally:
                self.context_menu.grab_release()
        return "break"

    def send_selection_to_gemini(self):
        if self.gemini_selection.strip():
            self.app_root.send_to_gemini(self.gemini_selection)

    def search_keyword(self, keyword):
        self.textbox.tag_remove("highlight", "1.0", "end")
        if not keyword:
            return 0

        matches = 0
        pos = "1.0"
        while True:
            pos = self.textbox.search(keyword, pos, stopindex="end", nocase=True)
            if not pos:
                break
            
            end_pos = f"{pos}+{len(keyword)}c"
            self.textbox.tag_add("highlight", pos, end_pos)
            matches += 1
            pos = end_pos

        if matches > 0:
            first_match = self.textbox.tag_ranges("highlight")
            if first_match:
                self.textbox.see(first_match[0])
        return matches


# --- ⭐ 2. หน้าต่าง Popup สำหรับเลือก Regex ---
class RegexSelectionPopup(ctk.CTkToplevel):
    def __init__(self, parent, current_regex, callback):
        super().__init__(parent)
        self.withdraw()
        self.title("SELECT REGEX PATTERN :: [CONFIG]")
        fit_window(self, "740x660")
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
        self._ui_queue = queue.Queue()
        self._worker_context = threading.local()
        self._analysis_generation = 0
        self._metadata_generation = 0
        self._history_pending = set()
        self.after(40, self._drain_ui)
        self.app_root = master.master 
        self.configure(fg_color=BG_COLOR)
        
        self.selected_files = [] 
        self.analysis_flags = {}
        self.regex_var = ctk.StringVar(value="") 

        self.smart_db = {
            r"(?:0|\+66)[689]\d[\-\.]?\d{3}[\-\.]?\d{4}": "📱 THAI_MOBILE_NUM",
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b": "📧 EMAIL_ADDR",
            r"(?<![A-Za-z0-9+/=])(?:[A-Za-z0-9+/]{4}){5,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?(?![A-Za-z0-9+/=])": "🔐 BASE64_STRING",
            r"(?:\d{1,3}\.){3}\d{1,3}": "🌐 IPv4_ADDR",
            r"https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}": "🔗 URL_LINK",
            r"[a-fA-F0-9]{32}": "🔑 MD5_HASH",
            UNIVERSAL_FLAG_REGEX: "🚩 UNIVERSAL_CTF_FLAG"
        }

        self.regex_previews = {
            r"(?:0|\+66)[689]\d[\-\.]?\d{3}[\-\.]?\d{4}": "📱 THAI_MOBILE_NUM\nFind Thai mobile numbers (08x, 09x, 06x)",
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b": "📧 EMAIL_ADDR\nStrict standard email pattern",
            r"(?:[A-Za-z0-9+/]{4}){5,}|(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)": "🔐 BASE64_STRING\nFlexible Base64 (Catches padded strings or long blocks)",
            r"FLAG\{.*?\}": "🎯 STD_FLAG\nStandard CTF flag format",
            r"(flag|ctf|picoCTF)\{[^}]+\}": "🌐 MULTI_CTF_FLAG\nCommon CTF platform formats (pico, HTB, etc.)",
            "": "💡 HOVER FOR DETAILS",
            UNIVERSAL_FLAG_REGEX:
                "🚩 UNIVERSAL_CTF_FLAG\n"
                "Detect common CTF wrappers: flag, CTF, TCTT2026, "
                "IT_MSU_ANNIV25, HTB, picoCTF, etc.",
        }
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1) 

        # 1. Header 
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=30, pady=(20, 5))
        ctk.CTkLabel(header_frame, text=">_ DATA_INSPECTOR :: [BATCH_SCAN]", font=("Consolas", 28, "bold"), text_color=ACCENT_CYAN).pack(side="left")
        ctk.CTkButton(header_frame, text='History', width=90,
                      command=lambda: history_hooks.open_history(self.app_root, 'File Inspection')).pack(side='right')

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

        # เพิ่ม steghide Analysis เข้าไปใน options 
        self.tool_menu = ctk.CTkOptionMenu(
            action_frame, values=["'file' Command", "Header Check", "Executable Check", "Strings", "zsteg Analysis", "steghide Analysis", "Exiftool"], 
            width=180, height=35, font=("Consolas", 12),
            fg_color="#1E1E2E", button_color="#2B2B36", button_hover_color="#3A3A4A",
            state="disabled", command=self.on_tool_change
        )
        self.tool_menu.pack(side="left", padx=15, pady=15)

        self.btn_analyze = ctk.CTkButton(
            action_frame, text="[ EXECUTE ]", width=100, height=35, 
            font=("Consolas", 12, "bold"), fg_color=ACCENT_CYAN, text_color="black", hover_color="#00CCCC",
            state="disabled", command=self.start_analysis_thread
        )
        self.btn_analyze.pack(side="left", padx=5)

        self.btn_regex_popup = ctk.CTkButton(
            action_frame, text="⚙️ CFG_REGEX", width=100, height=35,
            font=("Consolas", 12, "bold"), fg_color="transparent", border_width=1, border_color=ACCENT_GREEN, text_color=ACCENT_GREEN, hover_color="#003311",
            state="disabled", command=self.open_regex_popup
        )
        self.btn_regex_popup.pack(side="left", padx=(10, 5))

        self.btn_clear_regex = ctk.CTkButton(
            action_frame, text="[X]", width=35, height=35, 
            font=("Consolas", 12, "bold"), fg_color="transparent", border_width=1, border_color=ALERT_RED, text_color=ALERT_RED, hover_color="#4A0011",
            state="disabled", command=self.clear_main_regex
        )
        self.btn_clear_regex.pack(side="left", padx=0)

        # ช่องกรอก Max Display
        ctk.CTkLabel(action_frame, text="Max:", font=("Consolas", 11, "bold"), text_color=TEXT_DIM).pack(side="left", padx=(10, 2))
        self.max_display_entry = ctk.CTkEntry(
            action_frame, width=65, height=35,
            font=("Consolas", 12), fg_color="#0A0A0F",
            border_color="#333344", text_color=ACCENT_CYAN
        )
        self.max_display_entry.insert(0, "3000")
        self.max_display_entry.pack(side="left", padx=(0, 10))

        self.progress_bar = ctk.CTkProgressBar(action_frame, mode="indeterminate", width=80, progress_color=ACCENT_CYAN, fg_color="#2B2B36")
        self.progress_bar.pack(side="left", padx=5)
        self.progress_bar.pack_forget() 

        self.warning_label = ctk.CTkLabel(action_frame, text="STATUS: IDLE", text_color=TEXT_DIM, font=("Consolas", 12, "bold"))
        self.warning_label.pack(side="right", padx=(10, 20))

        self.regex_status_label = ctk.CTkLabel(
            action_frame, text=" 🔍 REGEX: NONE ", font=("Consolas", 12, "bold"), 
            fg_color="#0A0A0F", text_color=TEXT_DIM, corner_radius=4, width=130, height=30
        )
        self.regex_status_label.pack(side="right", padx=5)

        # 5. Output Container (Split View + In-App Search Bar)
        output_header = ctk.CTkFrame(self, fg_color="transparent")
        output_header.grid(row=4, column=0, sticky="ew", padx=30, pady=(5, 0))
        
        ctk.CTkLabel(output_header, text=">_ ANALYSIS_OUTPUT", font=("Consolas", 14, "bold"), text_color=ALERT_RED).pack(side="left")
        
        ctk.CTkButton(output_header, text="[ CLEAR_ALL ]", font=("Consolas", 12, "bold"), width=90, height=28, fg_color="transparent", border_width=1, border_color=ALERT_RED, text_color=ALERT_RED, hover_color="#4A0011", command=self.clear_terminal).pack(side="right", padx=(5, 0))
        
        self.search_btn = ctk.CTkButton(output_header, text="[ FIND ]", font=("Consolas", 11, "bold"), width=60, height=28, fg_color="transparent", border_width=1, border_color=ACCENT_CYAN, text_color=ACCENT_CYAN, hover_color="#003344", command=self.trigger_in_app_search)
        self.search_btn.pack(side="right", padx=5)

        self.search_entry = ctk.CTkEntry(output_header, placeholder_text="Search in output...", font=("Consolas", 11), width=150, height=28, fg_color="#0A0A0F", border_color="#333344", text_color=ACCENT_CYAN)
        self.search_entry.pack(side="right", padx=5)
        self.search_entry.bind("<Return>", lambda e: self.trigger_in_app_search())

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

    def trigger_in_app_search(self):
        keyword = self.search_entry.get().strip()
        total_found = 0
        for path, box in self.result_boxes.items():
            found = box.search_keyword(keyword)
            total_found += found
        
        if keyword:
            self.warning_label.configure(text=f"STATUS: FOUND {total_found} MATCHES", text_color=ACCENT_GREEN)

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
            self.result_boxes[target_file].insert_preview(txt, tag)

    def safe_log(self, msg, tag=None, newline=True, target_file=None):
        if tag == "error":
            self._worker_context.failed = True
        self._write_full_output(target_file, msg + ("\n" if newline else ""))
        self._post_ui(lambda: self.log(msg, tag, newline, target_file))

    def _write_full_output(self, target_file, text):
        job = getattr(self._worker_context, "job", None)
        if not job or target_file not in job.get("boxes", {}):
            return
        path = job.get('outputs', {}).get(target_file)
        if not path:
            return
        with open(path, "a", encoding="utf-8", errors="replace") as stream:
            stream.write(text)

    def _post_ui(self, callback):
        generation = getattr(self._worker_context, "generation", self._analysis_generation)
        self._ui_queue.put(("analysis", generation, callback))

    def _drain_ui(self):
        for _ in range(100):
            try:
                kind, generation, callback = self._ui_queue.get_nowait()
            except queue.Empty:
                break
            current = self._metadata_generation if kind == "metadata" else self._analysis_generation
            if generation == current:
                callback()
        self.after(40, self._drain_ui)

    def clear_terminal(self):
        for box in self.result_boxes.values():
            box.textbox.delete("1.0", "end")

    def on_drop(self, event):
        raw_paths = self.tk.splitlist(event.data)
        self.load_files(raw_paths)

    def browse_file(self):
        paths = filedialog.askopenfilenames()
        if paths: self.load_files(paths)

    def load_files(self, paths):
        valid_paths = [p for p in paths if os.path.isfile(p)]
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
        self.start_analysis_thread()

    def format_size(self, size_bytes):
        if size_bytes < 1024: return f"{size_bytes} B"
        elif size_bytes < 1024**2: return f"{size_bytes/1024:.2f} KB"
        else: return f"{size_bytes/(1024**2):.2f} MB"

    def update_metadata_card(self):
        self._metadata_generation += 1
        self.meta_frame.grid() 
        if len(self.selected_files) == 1:
            path = self.selected_files[0]
            size_bytes = os.path.getsize(path)
            size_str = self.format_size(size_bytes)
            ext = os.path.splitext(path)[1].lower() or "Unknown"
            threading.Thread(target=self._calc_md5, args=(path, size_str, ext, self._metadata_generation), daemon=True).start()
        else:
            total_bytes = sum(os.path.getsize(p) for p in self.selected_files)
            size_str = self.format_size(total_bytes)
            self.meta_size.configure(text=f"[TOTAL_SIZE]: {size_str}")
            self.meta_ext.configure(text=f"[MODE]: BATCH_PROCESSING")
            self.meta_md5.configure(text=f"[MD5]: N/A (MULTIPLE FILES)")

    def _calc_md5(self, path, size_str, ext, generation):
        md5 = hashlib.md5()
        try:
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""): md5.update(chunk)
            result = md5.hexdigest()
        except: result = "Error"
        self._ui_queue.put(("metadata", generation, lambda: self._update_meta_ui(size_str, ext, result)))
        
    def _update_meta_ui(self, size_str, ext, md5_str):
        self.meta_size.configure(text=f"[SIZE]: {size_str}")
        self.meta_ext.configure(text=f"[EXT]: {ext}")
        self.meta_md5.configure(text=f"[MD5]: {md5_str}")

    def on_tool_change(self, choice):
        self.toggle_regex_button(choice)
        if self.selected_files:
            self.start_analysis_thread()

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
        if self.selected_files:
            self.start_analysis_thread()

    def clear_main_regex(self):
        self.regex_var.set("")
        self.regex_status_label.configure(text=" 🔍 REGEX: NONE ", fg_color="#0A0A0F", text_color=TEXT_DIM)
        if self.selected_files:
            self.start_analysis_thread()

    def start_analysis_thread(self):
        if not self.selected_files: return
        try:
            limit = int(self.max_display_entry.get())
            if not 1 <= limit <= 100000:
                raise ValueError("Display limit must be 1..100000")
            pattern = self.regex_var.get()
            re.compile(pattern)
        except (ValueError, re.error) as error:
            event_id = history_hooks.begin(self.app_root, category='File Inspection', tool=self.tool_menu.get(),
                input_data='\n'.join(self.selected_files), options={'regex': self.regex_var.get(),
                'display_limit': self.max_display_entry.get()}, files=self.selected_files)
            history_hooks.finish(self.app_root, event_id, 'Failed', error=str(error))
            self.warning_label.configure(text=f"ERROR: {error}", text_color=ALERT_RED)
            return

        for event_id in self._history_pending:
            history_hooks.finish(self.app_root, event_id, 'Failed', error='Superseded by another analysis.')
        self._history_pending.clear()
        self._analysis_generation += 1
        
        self.populate_file_nav()
        
        choice = self.tool_menu.get()
        self.btn_analyze.configure(state="disabled")
        self.tool_menu.configure(state="disabled")
        self.warning_label.configure(text="STATUS: PROCESSING...", text_color="#FFB800")
        self.progress_bar.pack(side="left", padx=5)
        self.progress_bar.start()

        job = dict(generation=self._analysis_generation, limit=limit, pattern=pattern,
                   paths=tuple(self.selected_files), boxes=dict(self.result_boxes), flags={})
        job['owner'] = _OutputDirectory(prefix='unit-inspection-')
        job['output_dir'] = job['owner'].name
        job['outputs'] = {path: os.path.join(job['output_dir'], uuid.uuid4().hex + '.txt') for path in job['paths']}
        for path, box in job['boxes'].items():
            box.set_full_output_path(job['outputs'][path])
            box._output_owner = job['owner']
        group_id = uuid.uuid4().hex
        job['history'] = {
            path: history_hooks.begin(self.app_root, category='File Inspection', tool=choice,
                    input_data=path, options={'regex': pattern, 'display_limit': limit},
                    files=[path], group_id=group_id)
            for path in job['paths']
        }
        for path, event_id in job['history'].items():
            if event_id:
                self._history_pending.add(event_id)
            if path in job['boxes']:
                job['boxes'][path].history_id = event_id
        threading.Thread(target=self._run_analysis_logic, args=(choice, job), daemon=True).start()

    def _run_analysis_logic(self, choice, job):
        self._worker_context.generation = job["generation"]
        self._worker_context.job = job
        max_limit = job["limit"]

        state = {'match_count': 0, 'display_count': 0, 'max_display': max_limit, 'warned': False}

        for path in job["paths"]:
            if job["generation"] != self._analysis_generation:
                break
            self._worker_context.failed = False
            

            try:
                if choice == "'file' Command": self.run_file_command(path)
                elif choice == "Header Check": self.inspect_file_header(path)
                elif choice == "Executable Check": self.check_if_executable(path)
                elif choice == "Strings": self.extract_all_strings(path, state)
                elif choice == "zsteg Analysis": self.run_zsteg_analysis(path)
                elif choice == "Exiftool": self.run_exiftool_analysis(path)
                elif choice == "steghide Analysis": self.run_steghide_analysis(path)
            except Exception as error:
                self._worker_context.failed = True
                try:
                    self.safe_log(f"[!] ANALYSIS ERROR: {error}", "error", target_file=path)
                except OSError:
                    self._post_ui(lambda p=path, message=str(error): self.log(f'[!] Output could not be saved: {message}', 'error', target_file=p))

            status = "failed" if self._worker_context.failed else "success"
            flags = job["flags"].get(path, []) if choice == "Strings" else []
            self._post_ui(lambda p=path, s=status, f=flags: self._record_activity(choice, p, flags=f, status=s))
            self._post_ui(lambda p=path, s=status: self._finish_history(job, p, s))
            if status == "failed":
                state["failed"] = True

        self._post_ui(lambda: self.finish_analysis(choice, state['match_count'], state.get('failed', False)))

    def _finish_history(self, job, path, status):
        box = job['boxes'].get(path)
        output = ''
        full_path = job.get('outputs', {}).get(path)
        if box and full_path and os.path.isfile(full_path):
            try:
                with open(full_path, 'rb') as stream:
                    output = stream.read(16385)
                box.save_button.configure(state='normal')
                box.view_button.configure(state='normal')
            except OSError:
                pass
        elif box:
            output = box.textbox.get('1.0', 'end-1c')
        history_hooks.finish(self.app_root, job.get('history', {}).get(path),
                             'Success' if status == 'success' else 'Failed', output_data=output)
        self._history_pending.discard(job.get('history', {}).get(path))

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
                try: res = puremagic.from_file(path) or None
                except: res = None
            if not res:
                try: header_data.decode('utf-8'); res = "Plain Text (.txt / Code)"
                except: res = "Unknown Binary Data"
            
            self.safe_log(f"[+] DETECTED TYPE: {res}", target_file=path)
        except Exception as e:
            self.safe_log(f"[!] ERROR: {str(e)}", "error", target_file=path)

    def _log_capture(self, path, capture, channel='stdout', tag=None):
        preview = getattr(capture, channel).decode('utf-8', errors='replace')
        full_path = getattr(capture, channel + '_file')
        if full_path:
            with full_path.open('r', encoding='utf-8', errors='replace') as stream:
                for chunk in iter(lambda: stream.read(65536), ''):
                    self._write_full_output(path, chunk)
            self._post_ui(lambda: self.log(preview + '\n[Preview only — use VIEW FULL OUTPUT / SAVE FULL OUTPUT.]', tag, True, path))
        else:
            self.safe_log(preview, tag, target_file=path)

    def _external_analysis(self, command, path, timeout):
        generation = self._worker_context.job['generation']
        class Superseded:
            def is_set(_):
                return generation != self._analysis_generation
        capture = run_capture(command, timeout=timeout, cancel_event=Superseded())
        try:
            if capture.returncode != 0:
                self.safe_log(f'[!] {command[0]} EXIT {capture.returncode}', 'error', target_file=path)
                if capture.stdout:
                    self._log_capture(path, capture, 'stdout')
                if capture.stderr:
                    self._log_capture(path, capture, 'stderr', 'error')
            else:
                self._log_capture(path, capture)
                if capture.stderr:
                    self._log_capture(path, capture, 'stderr')
        finally:
            capture.close()

    def run_zsteg_analysis(self, path):
        if os.path.splitext(path)[1].lower() not in ('.png', '.bmp'):
            self.safe_log('[!] ZSTEG ERROR: TARGET MUST BE PNG OR BMP', 'error', target_file=path)
            return
        self._external_analysis(['zsteg', path], path, 30)

    # 🌟 ฟังก์ชัน Steghide Analysis พร้อม UI Popup 🌟
    def run_steghide_analysis(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext not in [".jpg", ".jpeg", ".bmp", ".wav", ".au"]:
            self.safe_log(f"[!] STEGHIDE ERROR: '{ext}' MAY NOT BE SUPPORTED. (SUPPORTED: JPG, BMP, WAV, AU)", "error", target_file=path)

        def process_steghide(mode, secret_val):
            if mode == "passphrase":
                self.safe_log(f"[*] RUNNING STEGHIDE EXTRACT WITH PASSPHRASE: '{secret_val}'...", "highlight", target_file=path)
                try:
                    res = subprocess.run(
                        ["steghide", "extract", "-sf", path, "-p", secret_val, "-f"], 
                        capture_output=True, text=True
                    )
                    if res.returncode == 0:
                        self.safe_log(f"[+] SUCCESS! DATA EXTRACTED.", "found", target_file=path)
                        self.safe_log(res.stdout.strip() + "\n" + res.stderr.strip(), target_file=path)
                    else:
                        self.safe_log(f"[!] FAILED: {res.stderr.strip()}", "error", target_file=path)
                except Exception as e:
                    self.safe_log(f"[!] ERROR: {str(e)}", "error", target_file=path)

            elif mode == "wordlist":
                self.safe_log(f"[*] STARTING BRUTEFORCE WITH WORDLIST: {secret_val}...", "highlight", target_file=path)
                self.safe_log(f"[!] WARNING: STEGHIDE MAY PRODUCE FALSE POSITIVES.", "error", target_file=path)
                try:
                    with open(secret_val, 'r', encoding='utf-8', errors='ignore') as wl:
                        words = [line.strip() for line in wl.readlines()]
                    
                    found_count = 0
                    for w in words:
                        if not w: continue
                        res = subprocess.run(
                            ["steghide", "extract", "-sf", path, "-p", w, "-f"], 
                            capture_output=True, text=True
                        )
                        if res.returncode == 0:
                            self.safe_log(f"[+] POTENTIAL PASSPHRASE FOUND: '{w}'", "found", target_file=path)
                            self.safe_log(res.stdout.strip() + "\n" + res.stderr.strip(), target_file=path)
                            found_count += 1
                            
                            # เราเอาคำสั่ง break ออก เพื่อให้มันหาต่อ!
                            # แต่ตั้งเงื่อนไขว่าถ้าเจอ "ผลลวง" เกิน 5 อัน ให้หยุด ป้องกันแอปค้างนานเกินไป
                            if found_count >= 5:
                                self.safe_log(f"[!] REACHED LIMIT OF 5 POTENTIAL PASSPHRASES. STOPPING.", "error", target_file=path)
                                break
                    
                    if found_count == 0:
                        self.safe_log("[!] BRUTEFORCE COMPLETE: NO VALID PASSPHRASE FOUND.", "error", target_file=path)
                    else:
                        self.safe_log(f"[*] DONE. FOUND {found_count} POTENTIAL PASSPHRASES. PLEASE CHECK THE EXTRACTED FILES.", "highlight", target_file=path)
                except Exception as e:
                    self.safe_log(f"[!] WORDLIST ERROR: {str(e)}", "error", target_file=path)

        def show_steghide_prompt():
            popup = ctk.CTkToplevel(self)
            popup.title("STEGHIDE :: EXTRACTION CONFIG")
            popup.geometry("500x260")
            popup.configure(fg_color="#0D0D12")
            popup.attributes("-topmost", True)

            ctk.CTkLabel(popup, text="[ STEGHIDE EXTRACTION ]", font=("Consolas", 16, "bold"), text_color="#00FFFF").pack(pady=10)
            
            radio_var = ctk.StringVar(value="passphrase")
            
            ctk.CTkRadioButton(popup, text="Use Passphrase (ปล่อยว่างได้ถ้าไม่มีรหัส)", variable=radio_var, value="passphrase", font=("Consolas", 12), text_color="white").pack(anchor="w", padx=30, pady=5)
            pass_entry = ctk.CTkEntry(popup, placeholder_text="Enter passphrase here...", width=400, fg_color="#0A0A0F", border_color="#333344", text_color="#00FFFF")
            pass_entry.pack(padx=30, pady=5)

            ctk.CTkRadioButton(popup, text="Use Wordlist (Bruteforce Attack)", variable=radio_var, value="wordlist", font=("Consolas", 12), text_color="white").pack(anchor="w", padx=30, pady=5)
            wl_frame = ctk.CTkFrame(popup, fg_color="transparent")
            wl_frame.pack(fill="x", padx=30, pady=5)
            wl_entry = ctk.CTkEntry(wl_frame, placeholder_text="Path to wordlist.txt...", width=300, fg_color="#0A0A0F", border_color="#333344", text_color="#00FFFF")
            wl_entry.pack(side="left", padx=(0, 10))
            
            def browse_wordlist():
                p = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
                if p:
                    wl_entry.delete(0, "end")
                    wl_entry.insert(0, p)
                    radio_var.set("wordlist")
                    
            ctk.CTkButton(wl_frame, text="BROWSE", width=90, font=("Consolas", 10, "bold"), fg_color="#1E1E2E", command=browse_wordlist).pack(side="left")

            def execute():
                mode = radio_var.get()
                secret = pass_entry.get() if mode == "passphrase" else wl_entry.get()
                popup.destroy()
                threading.Thread(target=process_steghide, args=(mode, secret), daemon=True).start()

            ctk.CTkButton(popup, text="[ START EXTRACTION ]", font=("Consolas", 12, "bold"), fg_color="#00FFFF", text_color="black", hover_color="#00CCCC", command=execute).pack(pady=15)

        self.after(0, show_steghide_prompt)

    def run_exiftool_analysis(self, path):
        self._external_analysis(['exiftool', path], path, 10)

    def extract_all_strings(self, path, state):
        from Tools.inspection_stream import extract_strings
        from Tools.regex_runner import find_match_spans
        job = self._worker_context.job
        if path not in job['boxes']:
            return
        box = job['boxes'][path]
        destination = Path(job['outputs'][path])
        extract_strings(Path(path), destination,
                        lambda: job['generation'] != self._analysis_generation)
        # Preview only: full extraction remains on disk, including long lines.
        with destination.open('r', encoding='utf-8', newline='') as stream:
            sample = stream.read(128 * 1024 + 1)
        truncated = len(sample) > 128 * 1024
        lines = sample[:128 * 1024].splitlines()
        line_limited = len(lines) > state['max_display']
        display = '\n'.join(lines[:state['max_display']])
        state['display_count'] += min(len(lines), state['max_display'])
        state['warned'] = truncated or line_limited
        # Highlighting is scoped to the displayed portion, as before.
        matches = find_match_spans(job['pattern'], display) if job['pattern'] else []
        state['match_count'] += len(matches)
        job['flags'][path] = find_flags(display)
        warning = ('\n[Preview only — use VIEW FULL OUTPUT / SAVE FULL OUTPUT for all results. Regex highlights apply to this preview.]'
                   if state['warned'] else '')
        def render():
            box.reset_output()
            box.insert_preview(display)
            for start, end in matches:
                box.textbox.tag_add('found', f'1.0+{start}c', f'1.0+{end}c')
            box.textbox.insert('end', warning)
        self._post_ui(render)

    def run_file_command(self, path):
        self._external_analysis(['file', path], path, 5)

    def _record_activity(self, tool, path, flags=None, status="success", details=""):
        if not hasattr(self.app_root, "record_activity"):
            return
        self.app_root.record_activity(
            tool=tool,
            category="File Inspection",
            action="Analyze File",
            status=status,
            file_path=path,
            flags=flags or [],
            details=details,
        )

    def finish_analysis(self, choice, total_matches, failed=False):
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.btn_analyze.configure(state="normal")
        self.tool_menu.configure(state="normal")
        
        if failed:
            self.warning_label.configure(text="STATUS: COMPLETED WITH ERRORS", text_color=ALERT_RED)
        elif choice == "Strings" and self.regex_var.get():
            self.warning_label.configure(text=f"STATUS: FOUND {total_matches} MATCHES IN DISPLAYED PREVIEW", text_color=ACCENT_GREEN)
        else:
            self.warning_label.configure(text="STATUS: COMPLETE", text_color=ACCENT_GREEN)

    def show_regex_info(self):
        info_window = ctk.CTkToplevel(self)
        info_window.withdraw()
        info_window.title("SYS_MANUAL :: REGEX")
        fit_window(info_window, "600x570")
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
