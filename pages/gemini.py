import customtkinter as ctk
from tkinter import filedialog, Menu, TclError
import threading
import os
import re
import subprocess
import shutil
import time
import signal
from Tools.flag_detector import find_flags
from Tools.window_layout import fit_window
from Tools.stream_capture import run_capture
from Tools.text_view import open_text_view
from pathlib import Path
from Tools.app_paths import external_environment

MAX_PROMPT_BYTES = 4 * 1024 * 1024
MAX_ATTACHMENT_BYTES = 1024 * 1024

class GeminiPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.app_root = master.master
        
        # --- [ ธีมสี Cyberpunk / Terminal ] ---
        BG_COLOR = "#0D0D12"        
        PANEL_COLOR = "#15151E"     
        ACCENT_CYAN = "#00FFFF"     
        ACCENT_GREEN = "#00FF41"    
        TEXT_DIM = "#8892B0"        
        
        self.configure(fg_color=BG_COLOR)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # ==========================================
        # 1. ส่วนหัวโปรแกรม (HEADER HUD)
        # ==========================================
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky='ew', padx=24, pady=(20, 12))
        
        ctk.CTkLabel(
            header_frame, 
            text=">_ GEMINI_AI :: [CTF_MODE]", 
            font=("Consolas", 28, "bold"),
            text_color=ACCENT_CYAN
        ).pack(anchor='w')
        
        # ==========================================
        # 2. แผงควบคุม API & Model (CONTROL PANEL)
        # ==========================================
        api_container = ctk.CTkFrame(
            self, 
            fg_color=PANEL_COLOR, 
            border_color=ACCENT_CYAN, 
            border_width=1, 
            corner_radius=8
        )
        api_container.grid(row=1, column=0, sticky='ew', padx=24, pady=(0, 8))
        
        api_inner = ctk.CTkFrame(api_container, fg_color="transparent")
        api_inner.pack(pady=15, padx=20, fill="x")

        ctk.CTkLabel(api_inner, text="🔑 API_KEY:", font=("Consolas", 14, "bold"), text_color=ACCENT_CYAN).pack(side="left", padx=(0, 10))

        self.api_entry = ctk.CTkEntry(
            api_inner,
            placeholder_text="Paste your token here (Leave blank if CLI is authenticated)...",
            show="*",
            fg_color="#0A0A0F",
            border_color="#333344",
            text_color=ACCENT_CYAN,
            font=("Consolas", 12),
            height=35
        )
        self.api_entry.pack(side="left", fill="x", expand=True)

        self.toggle_btn = ctk.CTkButton(
            api_inner, text="👁", width=35, height=35, 
            fg_color="#2B2B36", hover_color="#3A3A4A", text_color="white",
            command=self.toggle_api_visibility
        )
        self.toggle_btn.pack(side="left", padx=5)

        model_row = ctk.CTkFrame(api_container, fg_color='transparent')
        model_row.pack(fill='x', padx=20, pady=(0, 12))

        # ⭐ แก้ไข: เก็บปุ่มไว้ในตัวแปร self.connect_btn เพื่อให้แก้ไขข้อความได้
        self.connect_btn = ctk.CTkButton(
            model_row, text="[ CONNECT_CLI ]", width=140, height=35,
            font=("Consolas", 12, "bold"),
            fg_color="transparent", border_width=1, border_color=ACCENT_GREEN, text_color=ACCENT_GREEN,
            hover_color="#003311",
            command=self.init_api
        )
        self.connect_btn.pack(side="left")

        self.model_options = [
            "gemini-3.1-flash-lite",
            "gemini-2.5-flash",
            "gemini-3.5-flash",
            "gemini-2.5-pro",
        ]
        self.model_var = ctk.StringVar(value=self.model_options[0])
        ctk.CTkOptionMenu(
            model_row, values=self.model_options, variable=self.model_var,
            width=220, height=35,
            font=("Consolas", 12),
            fg_color="#1E1E2E", button_color="#2B2B36", button_hover_color="#3A3A4A",
            command=self.on_model_change,
        ).pack(side="right")

        self.status_label = ctk.CTkLabel(
            self,
            text="[!] WAITING FOR CONNECTION...",
            font=("Consolas", 12, "italic"),
            text_color=TEXT_DIM,
            anchor="w",
        )
        self.status_label.grid(row=2, column=0, sticky='ew', padx=24)

        # ==========================================
        # 3. กล่องแสดงประวัติแชท (CHAT DISPLAY)
        # ==========================================
        self.chat_display = ctk.CTkTextbox(
            self,
            fg_color="#0A0A0F",
            border_color="#333344",
            border_width=1,
            corner_radius=8,
            text_color="#00FF41",
            font=("Consolas", 13)
        )
        self.chat_display.grid(row=3, column=0, sticky='nsew', padx=24, pady=(8, 10))
        self.chat_display.configure(state="disabled")

        self.hashing_selection = ""
        self.context_menu = Menu(
            self, tearoff=0, bg=PANEL_COLOR, fg="white",
            activebackground=ACCENT_CYAN, activeforeground="black",
            font=("Consolas", 11),
        )
        self.context_menu.add_command(
            label="Send to Data Hashing", command=self.send_selection_to_hashing,
        )
        self.chat_display.bind("<Button-3>", self.show_context_menu)
        self._captures = []
        self._full_response_path = None
        self._command_output_path = None
        result_actions = ctk.CTkFrame(self, fg_color='transparent')
        result_actions.grid(row=4, column=0, sticky='ew', padx=24, pady=(0, 10))
        action_style = dict(height=32, fg_color='transparent', border_width=1,
                            border_color=ACCENT_CYAN, text_color=ACCENT_CYAN,
                            hover_color='#003344')
        self.full_response_button = ctk.CTkButton(
            result_actions, text='View Full Response', state='disabled', **action_style,
            command=lambda: open_text_view(self, self._full_response_path) if self._full_response_path else None)
        self.full_response_button.pack(side='left', padx=(0, 8))
        self.command_output_button = ctk.CTkButton(result_actions, text='View Full Command Output', **action_style,
            command=lambda: open_text_view(self, self._command_output_path) if self._command_output_path else None)
        self.command_output_button.pack(side='left')

        # ⭐ เพิ่ม: สวิตช์เปิด-ปิด Auto-Execute (ข้ามการกด Allow)
        self.auto_exec_var = ctk.BooleanVar(value=False)
        self.auto_exec_switch = ctk.CTkSwitch(
            result_actions, 
            text="Auto-Execute (Skip Confirm)", 
            variable=self.auto_exec_var,
            font=("Consolas", 12, "bold"), 
            text_color="#FFB800",
            progress_color="#00FF41", 
            button_hover_color="#CCCCCC"
        )
        self.auto_exec_switch.pack(side='right', padx=(20, 0))

        # ==========================================
        # 4. กล่องพิมพ์ข้อความ (COMMAND INPUT)
        # ==========================================
        input_container = ctk.CTkFrame(self, fg_color="transparent")
        input_container.grid(row=5, column=0, sticky='ew', padx=24, pady=(0, 20))
        
        ctk.CTkLabel(
            input_container, 
            text="root@kali:~#", 
            font=("Consolas", 16, "bold"), 
            text_color="#FF3366" 
        ).pack(side="left", padx=(0, 10))

        self.input_field = ctk.CTkEntry(
            input_container,
            placeholder_text="Enter command or target file...",
            height=45,
            font=("Consolas", 14),
            fg_color="#0A0A0F",
            border_color=ACCENT_CYAN,
            text_color="white"
        )
        self.input_field.pack(side="left", fill="x", expand=True)
        self.input_field.bind("<Return>", lambda event: self.send_message())

        self.browse_btn = ctk.CTkButton(
            input_container, 
            text="📁", 
            width=45, height=45, 
            font=("Consolas", 18),
            fg_color="#2B2B36", 
            text_color="white",
            hover_color="#3A3A4A",
            command=self.browse_file
        )
        self.browse_btn.pack(side="left", padx=(10, 0))

        # ⭐ ปุ่มสำหรับรันคำสั่ง (EXECUTE)
        self.send_btn = ctk.CTkButton(
            input_container, 
            text="EXECUTE", 
            width=100, height=45, 
            font=("Consolas", 14, "bold"),
            fg_color=ACCENT_CYAN, 
            text_color="black",
            hover_color="#00CCCC",
            command=self.send_message
        )
        self.send_btn.pack(side="left", padx=(10, 5))
        
        # ⭐ ปุ่มใหม่สำหรับหยุดรัน (STOP)
        self.stop_btn = ctk.CTkButton(
            input_container, 
            text="STOP", 
            width=70, height=45, 
            font=("Consolas", 14, "bold"),
            fg_color="transparent", 
            border_width=1,
            border_color="#FF3366",
            text_color="#FF3366",
            hover_color="#4A0011",
            state="disabled",
            command=self.request_stop
        )
        self.stop_btn.pack(side="left")

        # ==========================================
        # ตัวแปรควบคุม state & Logic
        # ==========================================
        self.cli_ready = False
        self.gemini_cmd = "gemini"          
        self.model_name = self.model_options[0]  
        self.api_key = None  
        self.cli_workdir = os.path.expanduser("~")
        
        self.current_process = None  # เก็บ Process ของ Subprocess ที่กำลังทำงาน
        self._stop_requested = False # Flag เช็คว่าผู้ใช้กดหยุดหรือไม่
        self._busy = False
        self._connecting = False
        self._confirm_dialog = None

        # ⭐ ปรับปรุง System Prompt ให้โมเดลทำงานกับแท็กได้ดีขึ้น
        self.system_prompt = (
            "You are an AI Cybersecurity Assistant for CTF competitions. You have the ability to execute commands and save files directly on the user's system.\n"
            "CRITICAL INSTRUCTIONS FOR ACTIONS:\n"
            "1. To run a terminal command, you MUST wrap it EXACTLY like this: [EXEC]command here[/EXEC]\n"
            "2. To save or overwrite a file, you MUST wrap it EXACTLY like this: [SAVE:/path/to/file.txt]file content here[/SAVE]\n"
            "3. DO NOT use these tags for examples, greetings, or theoretical explanations. Only use them when you ACTUALLY want the system to execute the action.\n"
            "4. Provide a brief explanation before executing an action."
        )
        self.history = []  

    # --- ฟังก์ชันเสริม UI ---
    def show_context_menu(self, event):
        try:
            self.hashing_selection = self.chat_display.get("sel.first", "sel.last")
        except TclError:
            self.hashing_selection = ""
        self.context_menu.entryconfigure(
            0, state="normal" if self.hashing_selection.strip() else "disabled",
        )
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()
        return "break"

    def send_selection_to_hashing(self):
        if self.hashing_selection.strip():
            self.app_root.send_to_hashing(self.hashing_selection)

    def toggle_api_visibility(self):
        if self.api_entry.cget("show") == "*":
            self.api_entry.configure(show="")
            self.toggle_btn.configure(text="🔒")
        else:
            self.api_entry.configure(show="*")
            self.toggle_btn.configure(text="👁")

    def browse_file(self):
        file_path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title="Select Target File"
        )
        if file_path:
            current_text = self.input_field.get()
            if current_text:
                self.input_field.insert("end", f' "{file_path}"')
            else:
                self.input_field.insert(0, f'"{file_path}"')
            self.input_field.focus()

    # ==================================================================
    # ระบบยืนยันคำสั่ง (Confirmation System)
    # ==================================================================
    def ask_action_confirm(self, action_type, detail):
        # ⭐ เพิ่ม: ถ้ายเปิดสวิตช์ Auto-Execute ไว้ ให้ผ่านทันทีโดยไม่เด้ง Dialog
        if hasattr(self, 'auto_exec_var') and self.auto_exec_var.get():
            return True

        self._confirm_result = False
        self._confirm_event = threading.Event()
        
        self.after(0, self._show_confirm_dialog, action_type, detail)
        while not self._confirm_event.wait(0.1):
            if self._stop_requested:
                return False
        return self._confirm_result

    def _show_confirm_dialog(self, action_type, detail):
        if self._stop_requested:
            self._confirm_event.set()
            return
        dialog = ctk.CTkToplevel(self)
        self._confirm_dialog = dialog
        dialog.title("⚠️ SECURITY WARNING")
        fit_window(dialog, "630x440")
        dialog.attributes("-topmost", True)
        dialog.configure(fg_color="#0D0D12")
        dialog.transient(self.winfo_toplevel()) 
        dialog.grab_set() 
        
        title_color = "#FF3366" if action_type == "SHELL COMMAND" else "#00FFFF"
        ctk.CTkLabel(dialog, text=f"[ ACTION REQUIRED: {action_type} ]", font=("Consolas", 18, "bold"), text_color=title_color).pack(pady=(20, 10))
        
        detail_box = ctk.CTkTextbox(dialog, fg_color="#15151E", border_color="#333344", border_width=1, text_color="#00FF41", font=("Consolas", 12))
        detail_box.pack(padx=20, pady=10, fill="both", expand=True)
        detail_box.insert("1.0", detail)
        detail_box.configure(state="disabled")
        
        ctk.CTkLabel(dialog, text="Execution is paused for safety. Do you want to allow this action?", font=("Consolas", 12), text_color="#8892B0").pack(pady=(0, 10))
        
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        def on_allow():
            self._confirm_result = True
            self._confirm_event.set()
            dialog.grab_release()
            dialog.destroy()
            
        def on_deny():
            self._confirm_result = False
            self._confirm_event.set()
            dialog.grab_release()
            dialog.destroy()
            
        dialog.protocol("WM_DELETE_WINDOW", on_deny)
        
        ctk.CTkButton(btn_frame, text="[ ALLOW ]", fg_color="#00FF41", text_color="black", hover_color="#00CC33", font=("Consolas", 14, "bold"), command=on_allow).pack(side="left", expand=True, padx=10)
        ctk.CTkButton(btn_frame, text="[ DENY ]", fg_color="transparent", border_width=1, border_color="#FF3366", text_color="#FF3366", hover_color="#4A0011", font=("Consolas", 14, "bold"), command=on_deny).pack(side="right", expand=True, padx=10)

    # ==================================================================
    # LOGIC การทำงาน API
    # ==================================================================
    def on_model_change(self, selected_model):
        self.model_name = selected_model
        self.update_chat_ui("System", f"🔄 Switched to model: {selected_model}")

    def init_api(self):
        if self._busy or self._connecting:
            return
        resolved_path = shutil.which(self.gemini_cmd)
        if resolved_path is None:
            self.update_chat_ui(
                "System",
                f"❌ Command '{self.gemini_cmd}' was not found (PATH visible to the app: {os.environ.get('PATH', 'no PATH set')}). "
                f"Please install Gemini CLI (npm install -g @google/gemini-cli) first.",
            )
            return

        self.update_chat_ui("System", f"🔍 Found gemini at: {resolved_path}")

        entered_key = self.api_entry.get().strip()
        self.api_key = entered_key if entered_key else None

        self.status_label.configure(text="⏳ Connecting...")
        self.update_chat_ui("System", "Connecting to Gemini CLI...")

        self.cli_ready = False
        self._connecting = True
        threading.Thread(target=self._init_api_worker, daemon=True).start()

    def _init_api_worker(self):
        try:
            res = subprocess.run(
                [self.gemini_cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=20,
                env=self._build_env(),
                stdin=subprocess.DEVNULL,
                cwd=self.cli_workdir,
            )
            version_info = (res.stdout or res.stderr).strip()
            if res.returncode != 0:
                raise RuntimeError(version_info or "Gemini version check failed")

            test_res = subprocess.run(
                [self.gemini_cmd, "-m", self.model_name, "-p", "hi"],
                capture_output=True,
                text=True,
                timeout=60,
                env=self._build_env(),
                stdin=subprocess.DEVNULL,
                cwd=self.cli_workdir,
            )
            combined = (test_res.stdout + test_res.stderr)

            if "UNAUTHENTICATED" in combined or "invalid authentication" in combined.lower():
                self.after(0, self._init_api_fail, "❌ Authentication failed",
                    "❌ Gemini CLI is not authenticated: open a terminal and run `gemini` to log in through your browser, "
                    "or enter an API key above and click 'Connect CLI' again.")
                return
            if "trusted directory" in combined.lower():
                self.after(0, self._init_api_fail, "❌ Untrusted directory",
                    "❌ Gemini CLI blocked this request because the working directory is not trusted. Run this program from a terminal, "
                    "`cd` to that directory, and run `gemini` once in interactive mode to trust it.")
                return

            if test_res.returncode != 0:
                raise RuntimeError(combined.strip() or f"Gemini CLI exit code {test_res.returncode}")
            self.after(0, self._init_api_success, version_info)
        except subprocess.TimeoutExpired:
            self.after(0, self._init_api_fail, "❌ Timed out",
                "❌ The CLI connection timed out. Check your internet connection, or run `gemini -p \"hi\"` "
                "directly in a terminal to see whether it hangs there too.")
        except Exception as e:
            self.after(0, self._init_api_fail, "❌ Connection failed", f"❌ CLI connection failed: {e}")

    # ⭐ แก้ไข: ฟังก์ชันสำเร็จให้เปลี่ยนปุ่มเป็น [ EDIT_KEY ]
    def _init_api_success(self, version_info):
        self._connecting = False
        self.cli_ready = True
        self.api_entry.configure(state="disabled")
        
        self.connect_btn.configure(
            text="[ EDIT_KEY ]", 
            command=self.edit_api_key, 
            border_color="#FFB800", 
            text_color="#FFB800"
        )
        
        self.status_label.configure(text=f"✅ CONNECTED: {version_info or self.gemini_cmd}", text_color="#00FF41")
        self.update_chat_ui("System", "✅ CTF Mode ready! (Connected through Gemini CLI)")

    # ⭐ แก้ไข: ฟังก์ชันล้มเหลวให้ปุ่มกลับมาเป็น [ CONNECT_CLI ]
    def _init_api_fail(self, status_text, message):
        self._connecting = False
        self.cli_ready = False
        self.api_entry.configure(state="normal")
        
        self.connect_btn.configure(
            text="[ CONNECT_CLI ]", 
            command=self.init_api, 
            border_color="#00FF41", 
            text_color="#00FF41"
        )
        
        self.status_label.configure(text=status_text, text_color="#FF3366")
        self.update_chat_ui("System", message)

    # ⭐ เพิ่ม: ฟังก์ชันปลดล็อกเพื่อแก้ไข API Key กลางอากาศ
    def edit_api_key(self):
        self.api_entry.configure(state="normal")
        self.api_entry.focus()
        
        self.connect_btn.configure(
            text="[ UPDATE_KEY ]", 
            command=self.init_api, 
            border_color="#00FFFF", 
            text_color="#00FFFF"
        )
        
        self.status_label.configure(text="[!] WAITING FOR NEW API KEY...", text_color="#8892B0")
        self.update_chat_ui("System", "🔑 API Key input unlocked. Enter new key and click [ UPDATE_KEY ] to resume.")

    def _build_env(self):
        env = external_environment()
        if self.api_key:
            env["GEMINI_API_KEY"] = self.api_key
            env["GOOGLE_API_KEY"] = self.api_key
        env["GEMINI_CLI_TRUST_WORKSPACE"] = "true"
        return env

    def request_stop(self):
        self._stop_requested = True
        dialog = self._confirm_dialog
        if dialog is not None and dialog.winfo_exists():
            self._confirm_result = False
            self._confirm_event.set()
            dialog.destroy()
        self._confirm_dialog = None
        if self.current_process:
            try:
                if os.name == "posix":
                    os.killpg(self.current_process.pid, signal.SIGKILL)
                else:
                    self.current_process.kill()
            except Exception:
                pass
            self.update_chat_ui("System", "🛑 Operation cancelled by the user...")
            self.stop_btn.configure(state="disabled")

    def send_message(self):
        if self._busy or self._connecting:
            return
        user_text = self.input_field.get().strip()
        if not user_text:
            return
        if not self.cli_ready:
            self.update_chat_ui("System", "⚠️ Please connect to Gemini CLI first!")
            return

        self._stop_requested = False
        self._busy = True
        self.update_chat_ui("You", user_text)
        self.input_field.delete(0, "end")
        
        self.send_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.update_chat_ui("System", "Analyzing (press STOP to cancel)...")

        threading.Thread(target=self.process_request, args=(user_text,), daemon=True).start()

    def call_gemini_cli(self, prompt_text, max_retries=3):
        encoded_prompt = prompt_text.encode('utf-8')
        if len(encoded_prompt) > MAX_PROMPT_BYTES:
            raise ValueError('Prompt and history exceed 4 MiB. Reduce the input or start a new conversation; nothing was sent.')
        
        cmd = [self.gemini_cmd, "-m", self.model_name, "-p", 'Respond to the request above.']
        self._full_response_path = None
        class StopRequested:
            def is_set(_):
                return self._stop_requested
        last_error = None

        for attempt in range(1, max_retries + 1):
            if self._stop_requested:
                return "❌ [System]: Cancelled by the user"

            try:
                capture = run_capture(cmd, input_data=encoded_prompt, timeout=300, cancel_event=StopRequested(),
                    env=self._build_env(), cwd=self.cli_workdir,
                    on_process=lambda process: setattr(self, 'current_process', process))
                if not hasattr(self, '_captures'):
                    self._captures = []
                self._captures.append(capture)
                self._full_response_path = capture.stdout_file or capture.stderr_file
                out = capture.stdout.decode('utf-8', errors='replace')
                err = capture.stderr.decode('utf-8', errors='replace')

                if self._stop_requested:
                    return "❌ [System]: Cancelled by the user"

                combined_err = (err or "").strip()
                combined_out = (out or "").strip()
                full_text = combined_out + combined_err

                if "UNAUTHENTICATED" in combined_err or "invalid authentication" in combined_err.lower():
                    raise RuntimeError(
                        "Authentication failed: log in with `gemini` in a terminal, or enter an API key and click 'Connect CLI' again."
                    )

                if "exhausted your daily quota" in full_text.lower() or "quotaerror" in full_text.lower():
                    raise RuntimeError(
                        f"The daily quota for model '{self.model_name}' has been exhausted. "
                        f"Try switching to another model from the dropdown above (such as gemini-3.1-flash-lite) and try again."
                    )

                if "modelnotfounderror" in full_text.lower() or "no longer available to new users" in full_text.lower():
                    raise RuntimeError(
                        f"Model '{self.model_name}' is not available for this API key (it may be restricted for new keys). "
                        f"Try switching to another model from the dropdown above (such as gemini-2.5-flash or gemini-3.5-flash)."
                    )

                is_overloaded = (
                    '"status":503' in full_text.replace(" ", "")
                    or "UNAVAILABLE" in full_text
                    or "experiencing high demand" in full_text.lower()
                )
                
                if is_overloaded and attempt < max_retries:
                    last_error = full_text
                    self.after(
                        0,
                        self.update_chat_ui,
                        "System",
                        f"⏳ Model is under heavy load (503); retrying ({attempt}/{max_retries})...",
                    )
                    time.sleep(3 * attempt)
                    continue

                if capture.returncode != 0:
                    raise RuntimeError(combined_err or "Gemini CLI returned an error without details")
                
                response = (combined_out or combined_err).strip()
                if self._full_response_path:
                    response += '\n[Preview only — View Full Response contains the complete output. Automatic EXEC/SAVE parsing is disabled for this oversized response.]'
                return response

            except Exception as e:
                if self._stop_requested:
                    return "❌ [System]: Cancelled by the user"
                raise RuntimeError(f"Unexpected error: {e}")
            finally:
                self.current_process = None

        raise RuntimeError(f"The model remains overloaded (503). Try again later.\n\n{last_error}")

    def build_prompt_with_history(self, new_user_text, max_history_turns=6):
        parts = [f"[SYSTEM INSTRUCTION]\n{self.system_prompt}\n"]
        recent_history = self.history[-max_history_turns:]
        for role, text in recent_history:
            tag = "USER" if role == "user" else "MODEL"
            parts.append(f"[{tag}]\n{text}\n")
        parts.append(f"[USER]\n{new_user_text}\n[MODEL]\n")
        return "\n".join(parts)

    def process_request(self, prompt):
        try:
            enhanced_prompt = prompt
            words = prompt.split()
            file_data = ""

            for word in words:
                clean_path = word.strip('"\'')
                if os.path.isfile(clean_path):
                    try:
                        with open(clean_path, "rb") as f:
                            content = f.read(MAX_ATTACHMENT_BYTES + 1)
                        # คอมเมนต์ปิดการเช็กขนาดไฟล์ (ปลดล็อกขนาด 1 MiB)
                        #if len(content) > MAX_ATTACHMENT_BYTES:
                            #raise ValueError('Attachment exceeds 1 MiB. Extract relevant text first; the file was not sent or truncated.')
                        file_data += f"\n\n--- File contents: {clean_path} ---\n{content.decode('utf-8')}\n------------------\n"
                        if len(file_data.encode('utf-8')) > MAX_PROMPT_BYTES:
                            raise ValueError('Attachments exceed the 4 MiB request limit; nothing was sent.')
                    except UnicodeDecodeError:
                        # ข้ามไฟล์ Binary (รูปภาพ) ไปเพื่อให้ส่งรูปเข้า AI ได้
                        pass
                        #raise ValueError('Binary attachments are not sent as text. Extract relevant text with File Inspection first.')
            if file_data:
                enhanced_prompt = f"{prompt}\n{file_data}"

            full_prompt = self.build_prompt_with_history(enhanced_prompt)
            output = self.call_gemini_cli(full_prompt)
            if getattr(self, '_full_response_path', None):
                self.after(0, self.finish_response, output)
                return

            self.history.append(("user", enhanced_prompt))
            self.history.append(("model", output))
            self.history = self.history[-6:]

            # ==========================================
            # 1. จัดการ Execution (EXEC)
            # ==========================================
            # แก้ไข Regex เติม \ หน้า [ และ ] เพื่อป้องกันคำสั่งแหว่ง (XEC)
            exec_pattern = r"\[EXEC\](.*?)\[/EXEC\]"
            loop_count = 0
            has_executed = False 

            while re.search(exec_pattern, output) and loop_count < 2 and not self._stop_requested:
                loop_count += 1
                match = re.search(exec_pattern, output)
                cmd = match.group(1).strip()
                full_exec_tag = match.group(0)

                if self.ask_action_confirm("SHELL COMMAND", f"Command to execute:\n{cmd}") and not self._stop_requested:
                    self.after(0, self.update_chat_ui, "System", f"⚙️ AI was authorized to run command: {cmd}")

                    try:
                        capture = run_capture(cmd, shell=True, timeout=30,
                            on_process=lambda process: setattr(self, 'current_process', process))
                        if not hasattr(self, '_captures'):
                            self._captures = []
                        self._captures.append(capture)
                        self._command_output_path = capture.report_path()
                        stdout = capture.stdout.decode('utf-8', errors='replace')
                        stderr = capture.stderr.decode('utf-8', errors='replace')
                        code = capture.returncode
                        cmd_out = f"Exit code: {code}\nstdout:\n{stdout or '(empty)'}\nstderr:\n{stderr or '(empty)'}"
                        if len(cmd_out) > 4000:
                            cmd_out = cmd_out[:4000] + "\n...[output truncated because it is too long]..."

                    except Exception as e:
                        cmd_out = f"Error: {e}"
                    finally:
                        self.current_process = None

                    if self._stop_requested:
                        output = "❌ [System]: Cancelled by the user"
                        break

                    feedback_prompt = f"Result from running `{cmd}`:\n```\n{cmd_out}\n```\nPlease continue analyzing this result."
                    full_prompt = self.build_prompt_with_history(feedback_prompt)
                    output = self.call_gemini_cli(full_prompt)
                    if getattr(self, '_full_response_path', None):
                        self.after(0, self.finish_response, output)
                        return

                    self.history.append(("user", feedback_prompt))
                    self.history.append(("model", output))
                    self.history = self.history[-6:]
                    has_executed = True 
                else:
                    self.after(0, self.update_chat_ui, "System", f"❌ User cancelled command: {cmd}")
                    output = output.replace(full_exec_tag, f"\n[System]: User denied running command `{cmd}`\n")
                    break 

            # ==========================================
            # 2. จัดการ Save File 
            # ==========================================
            save_pattern = r"\[SAVE:(.*?)\](.*?)\[/SAVE\]"
            
            if not self._stop_requested:
                if not has_executed or (has_executed and not re.search(exec_pattern, output)):
                    for match in re.finditer(save_pattern, output, re.DOTALL):
                        file_path = match.group(1).strip()
                        clean_content = match.group(2).strip()
                        full_save_tag = match.group(0)
                        
                        if self.ask_action_confirm("SAVE FILE", f"Target Path: {file_path}\nFile Size: {len(clean_content.encode('utf-8'))} bytes\n\nPreview Content:\n{clean_content[:200]}...") and not self._stop_requested:
                            try:
                                with open(file_path, "w", encoding="utf-8") as f:
                                    f.write(clean_content)
                                output = output.replace(full_save_tag, f"\n\n💾 [System]: Edited and overwrote file {file_path} successfully!\n")
                            except Exception as e:
                                output = output.replace(full_save_tag, f"\n\n❌ [System]: Failed to save file: {e}\n")
                        else:
                            output = output.replace(full_save_tag, f"\n\n❌ [System]: User cancelled saving file {file_path}\n")
                elif has_executed and re.search(exec_pattern, output):
                    output = re.sub(save_pattern, f"\n\n⚠️ [System]: File saving suspended because additional unexecuted commands were detected.\n", output, flags=re.DOTALL)

        except Exception as e:
            output = f"❌ Error:\n{e}"

        self.after(0, self.finish_response, output)

    def finish_response(self, output):
        self._busy = False
        if hasattr(self, 'full_response_button'):
            self.full_response_button.configure(state='normal' if self._full_response_path else 'disabled')
        self.chat_display.configure(state="normal")

        lines = self.chat_display.get("1.0", "end").split("\n")
        last_you_idx = 0
        for i, line in enumerate(reversed(lines)):
            if line.startswith("You:"):
                last_you_idx = len(lines) - 1 - i
                break

        if last_you_idx > 0:
            for i in range(last_you_idx + 1, len(lines)):
                if "[System]: Analyzing" in lines[i] or "[System]: ⚙️ AI" in lines[i]:
                    self.chat_display.delete(f"{i+1}.0", f"{i+2}.0")

        self.chat_display.configure(state="disabled")

        self.update_chat_ui("Gemini (CTF)", output.strip())
        
        self.send_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.current_process = None

        if hasattr(self.app_root, "record_activity"):
            self.app_root.record_activity(
                tool=f"Gemini CLI: {self.model_name}",
                category="Gemini CLI",
                action="AI Request",
                status="failed" if output.startswith("❌") else "success",
                flags=find_flags(output),
                details=f"Response length: {len(output)} characters",
            )

        # ⭐ เพิ่มฟังก์ชันแจ้งเตือน (Notification & Bell) เมื่อ AI ทำงานเสร็จ
        try:
            self.bell()
            os.system('notify-send "UNIT: Gemini CLI" "AI Analysis Complete! Check the results."')
        except Exception:
            pass

    def update_chat_ui(self, sender, message):
        self.chat_display.configure(state="normal")
        if len(message) > 128 * 1024:
            message = message[:128 * 1024] + '\n[Display preview only; large responses are available in View Full Response.]'
        count = int(self.chat_display._textbox.count('1.0', 'end', 'chars')[0])
        if count > 256 * 1024:
            self.chat_display.delete('1.0', f'1.0+{count - 128 * 1024}c')
            self.chat_display.insert('1.0', '[Older messages removed from the display to keep it responsive.]\n')
        if sender == "System":
            self.chat_display.insert("end", f"[{sender}]: {message}\n\n")
        else:
            self.chat_display.insert("end", f"{sender}:\n{message}\n\n")
        self.chat_display.see("end")
        self.chat_display.configure(state="disabled")