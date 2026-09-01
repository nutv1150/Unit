import customtkinter as ctk
from tkinter import filedialog
import threading
import os
import re
import subprocess
import shutil
import time
from Tools.flag_detector import find_flags

class GeminiPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.app_root = master.master
        
        # --- [ ธีมสี Cyberpunk / Terminal ] ---
        BG_COLOR = "#0D0D12"        # ดำสนิทเหลือบน้ำเงิน
        PANEL_COLOR = "#15151E"     # สีพื้นหลังกล่องควบคุม
        ACCENT_CYAN = "#00FFFF"     # สีฟ้า Neon
        ACCENT_GREEN = "#00FF41"    # สีเขียว Terminal
        TEXT_DIM = "#8892B0"        # สีเทาตัวหนังสือทั่วไป
        
        self.configure(fg_color=BG_COLOR)

        # ==========================================
        # 1. ส่วนหัวโปรแกรม (HEADER HUD)
        # ==========================================
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(pady=(20, 10), fill="x")
        
        ctk.CTkLabel(
            header_frame, 
            text=">_ GEMINI_AI :: [CTF_MODE]", 
            font=("Consolas", 42, "bold"), 
            text_color=ACCENT_CYAN
        ).pack()
        
        ctk.CTkLabel(
            header_frame, 
            text="SYSTEM_STATUS: WRAPPER ACTIVE | AUTO_EXEC: ENABLED", 
            font=("Consolas", 12), 
            text_color=ACCENT_GREEN
        ).pack()

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
        api_container.pack(pady=10, fill="x", padx=40)
        
        # จัด Layout ภายในแผงควบคุม
        api_inner = ctk.CTkFrame(api_container, fg_color="transparent")
        api_inner.pack(pady=15, padx=20, fill="x")

        # Label API
        ctk.CTkLabel(api_inner, text="🔑 API_KEY:", font=("Consolas", 14, "bold"), text_color=ACCENT_CYAN).pack(side="left", padx=(0, 10))

        # ช่องใส่ API Key ดีไซน์ใหม่
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

        # ปุ่มโชว์/ซ่อน API Key
        self.toggle_btn = ctk.CTkButton(
            api_inner, text="👁", width=35, height=35, 
            fg_color="#2B2B36", hover_color="#3A3A4A", text_color="white",
            command=self.toggle_api_visibility
        )
        self.toggle_btn.pack(side="left", padx=5)

        # ปุ่มเชื่อมต่อ
        ctk.CTkButton(
            api_inner, text="[ CONNECT_CLI ]", width=120, height=35,
            font=("Consolas", 12, "bold"),
            fg_color="transparent", border_width=1, border_color=ACCENT_GREEN, text_color=ACCENT_GREEN,
            hover_color="#003311",
            command=self.init_api
        ).pack(side="left", padx=10)

        # Dropdown Model
        self.model_options = [
            "gemini-3.1-flash-lite",
            "gemini-2.5-flash",
            "gemini-3.5-flash",
            "gemini-2.5-pro",
        ]
        self.model_var = ctk.StringVar(value=self.model_options[0])
        ctk.CTkOptionMenu(
            api_inner, values=self.model_options, variable=self.model_var,
            width=160, height=35,
            font=("Consolas", 12),
            fg_color="#1E1E2E", button_color="#2B2B36", button_hover_color="#3A3A4A",
            command=self.on_model_change,
        ).pack(side="left")

        # สถานะการเชื่อมต่อ
        self.status_label = ctk.CTkLabel(
            self,
            text="[!] WAITING FOR CONNECTION...",
            font=("Consolas", 12, "italic"),
            text_color=TEXT_DIM,
            anchor="w",
        )
        self.status_label.pack(fill="x", padx=40)

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
        self.chat_display.pack(pady=10, fill="both", expand=True, padx=40)
        self.chat_display.configure(state="disabled")

        # ==========================================
        # 4. กล่องพิมพ์ข้อความ (COMMAND INPUT)
        # ==========================================
        input_container = ctk.CTkFrame(self, fg_color="transparent")
        input_container.pack(side="bottom", fill="x", padx=40, pady=(5, 20))
        
        # Label หลอกให้ดูเหมือน Terminal Prompt
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

        # ปุ่ม Browse
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
        self.send_btn.pack(side="left", padx=10)

        # ==========================================
        # ตัวแปรควบคุม state & Logic
        # ==========================================
        self.cli_ready = False
        self.gemini_cmd = "gemini"          
        self.model_name = self.model_options[0]  
        self.api_key = None  
        self.cli_workdir = os.path.expanduser("~")

        self.system_prompt = (
            "คุณคือ Cybersecurity Expert และ AI Assistant สำหรับแข่ง CTF "
            "คุณสามารถเซฟไฟล์ได้โดยใช้ [SAVE:ที่อยู่ไฟล์]...เนื้อหา...[/SAVE] "
            "และสามารถรันคำสั่ง Terminal ในเครื่องได้ด้วยแท็ก [EXEC]คำสั่ง[/EXEC] "
            "⚠️ กฎเหล็ก: ห้ามพิมพ์แท็ก [EXEC] หรือ [SAVE] เพื่อยกตัวอย่าง แนะนำตัว หรือทักทายเด็ดขาด! "
            "ถ้าผู้ใช้แค่ทักทาย (เช่น พิมพ์ hello) หรือถามทฤษฎีทั่วไป ให้ตอบกลับด้วยข้อความธรรมดา ห้ามใช้แท็กใดๆ ทั้งสิ้น "
            "ให้ใช้แท็กเหล่านี้เฉพาะตอนที่จำเป็นต้อง 'รันคำสั่งเพื่อแก้โจทย์' หรือ 'เขียนไฟล์จริงๆ' เท่านั้น"
        )
        self.history = []  

    # --- ฟังก์ชันเสริม UI ---
    def toggle_api_visibility(self):
        """ฟังก์ชันสำหรับปุ่ม 👁 สลับดู API Key"""
        if self.api_entry.cget("show") == "*":
            self.api_entry.configure(show="")
            self.toggle_btn.configure(text="🔒")
        else:
            self.api_entry.configure(show="*")
            self.toggle_btn.configure(text="👁")

    def browse_file(self):
        """เปิดหน้าต่างเลือกไฟล์และนำ Path มาใส่ในช่อง Input"""
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
        """ระบบหยุด Thread เบื้องหลังเพื่อรอคำตอบจากผู้ใช้ผ่าน UI"""
        self._confirm_result = False
        self._confirm_event = threading.Event()
        
        self.after(0, self._show_confirm_dialog, action_type, detail)
        self._confirm_event.wait()
        return self._confirm_result

    def _show_confirm_dialog(self, action_type, detail):
        dialog = ctk.CTkToplevel(self)
        dialog.title("⚠️ SECURITY WARNING")
        dialog.geometry("550x380")
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
        
        ctk.CTkLabel(dialog, text="ระบบถูกระงับเพื่อความปลอดภัย ต้องการอนุญาตให้ดำเนินการนี้หรือไม่?", font=("Consolas", 12), text_color="#8892B0").pack(pady=(0, 10))
        
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
        self.update_chat_ui("System", f"🔄 เปลี่ยนไปใช้โมเดล: {selected_model}")

    def init_api(self):
        resolved_path = shutil.which(self.gemini_cmd)
        if resolved_path is None:
            self.update_chat_ui(
                "System",
                f"❌ ไม่พบคำสั่ง '{self.gemini_cmd}' ในเครื่อง (PATH ที่โปรแกรมเห็น: {os.environ.get('PATH', 'ไม่มี PATH เลย')}) "
                f"กรุณาติดตั้ง Gemini CLI (npm install -g @google/gemini-cli) ก่อนครับ",
            )
            return

        self.update_chat_ui("System", f"🔍 เจอ gemini ที่: {resolved_path}")

        entered_key = self.api_entry.get().strip()
        self.api_key = entered_key if entered_key else None

        self.status_label.configure(text="⏳ กำลังเชื่อมต่อ...")
        self.update_chat_ui("System", "กำลังเชื่อมต่อกับ Gemini CLI...")

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
                self.after(0, self._init_api_fail, "❌ Auth ไม่ผ่าน",
                    "❌ ยังไม่ได้ auth กับ Gemini CLI: ให้เปิด terminal แล้วรัน `gemini` เพื่อ login ผ่านเบราว์เซอร์ "
                    "หรือใส่ API Key ในช่องด้านบนแล้วกด 'เชื่อมต่อ CLI' อีกครั้งครับ")
                return
            if "trusted directory" in combined.lower():
                self.after(0, self._init_api_fail, "❌ โฟลเดอร์ไม่ trusted",
                    "❌ Gemini CLI บล็อกเพราะโฟลเดอร์ทำงานยังไม่ trusted ลองรันโปรแกรมนี้จาก terminal แล้ว "
                    "`cd` ไปที่โฟลเดอร์นั้นก่อน แล้วรัน `gemini` ครั้งนึงเพื่อ trust ผ่าน interactive mode ก่อนครับ")
                return

            self.after(0, self._init_api_success, version_info)
        except subprocess.TimeoutExpired:
            self.after(0, self._init_api_fail, "❌ หมดเวลา",
                "❌ การเชื่อมต่อ CLI ใช้เวลานานเกินไป (timeout) ลองเช็คอินเทอร์เน็ต หรือรัน `gemini -p \"hi\"` "
                "ตรงๆ ใน terminal ดูว่าค้างเหมือนกันไหมครับ")
        except Exception as e:
            self.after(0, self._init_api_fail, "❌ เชื่อมต่อล้มเหลว", f"❌ การเชื่อมต่อ CLI ล้มเหลว: {e}")

    def _init_api_success(self, version_info):
        self.cli_ready = True
        self.api_entry.configure(state="disabled")
        self.status_label.configure(text=f"✅ CONNECTED: {version_info or self.gemini_cmd}", text_color="#00FF41")
        self.update_chat_ui("System", "✅ CTF Mode พร้อมลุย! (เชื่อมต่อผ่าน Gemini CLI)")

    def _init_api_fail(self, status_text, message):
        self.status_label.configure(text=status_text, text_color="#FF3366")
        self.update_chat_ui("System", message)

    def _build_env(self):
        env = os.environ.copy()
        if self.api_key:
            env["GEMINI_API_KEY"] = self.api_key
            env["GOOGLE_API_KEY"] = self.api_key
        env["GEMINI_CLI_TRUST_WORKSPACE"] = "true"
        return env

    def send_message(self):
        user_text = self.input_field.get().strip()
        if not user_text:
            return
        if not self.cli_ready:
            self.update_chat_ui("System", "⚠️ กรุณาเชื่อมต่อ Gemini CLI ก่อนครับ!")
            return

        self.update_chat_ui("You", user_text)
        self.input_field.delete(0, "end")
        self.send_btn.configure(state="disabled")
        self.update_chat_ui("System", "กำลังวิเคราะห์...")

        threading.Thread(target=self.process_request, args=(user_text,), daemon=True).start()

    def call_gemini_cli(self, prompt_text, max_retries=3):
        cmd = [self.gemini_cmd, "-m", self.model_name, "-p", prompt_text]
        last_error = None

        for attempt in range(1, max_retries + 1):
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180,
                env=self._build_env(),
                stdin=subprocess.DEVNULL,
                cwd=self.cli_workdir,
            )
            combined_err = result.stderr.strip()
            combined_out = (result.stdout or "").strip()
            full_text = combined_out + combined_err

            if "UNAUTHENTICATED" in combined_err or "invalid authentication" in combined_err.lower():
                raise RuntimeError(
                    "Auth ไม่ผ่าน: กรุณา login ผ่าน `gemini` ในเทอร์มินัล หรือใส่ API Key แล้วกด 'เชื่อมต่อ CLI' ใหม่"
                )

            if "exhausted your daily quota" in full_text.lower() or "quotaerror" in full_text.lower():
                raise RuntimeError(
                    f"โควตารายวันของโมเดล '{self.model_name}' หมดแล้ว "
                    f"ลองเปลี่ยนโมเดลจาก dropdown ด้านบน (เช่น gemini-3.1-flash-lite) แล้วลองใหม่ครับ"
                )

            if "modelnotfounderror" in full_text.lower() or "no longer available to new users" in full_text.lower():
                raise RuntimeError(
                    f"โมเดล '{self.model_name}' ไม่พร้อมใช้งานสำหรับ API key นี้ (อาจถูกจำกัดสำหรับ key ใหม่) "
                    f"ลองเปลี่ยนโมเดลจาก dropdown ด้านบนเป็นตัวอื่น (เช่น gemini-2.5-flash หรือ gemini-3.5-flash) ครับ"
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
                    f"⏳ โมเดลกำลังโหลดสูง (503) กำลังลองใหม่ ({attempt}/{max_retries})...",
                )
                time.sleep(3 * attempt)
                continue

            if result.returncode != 0 and not combined_out:
                raise RuntimeError(combined_err or "Gemini CLI คืนค่า error โดยไม่มีรายละเอียด")
            return (combined_out or combined_err).strip()

        raise RuntimeError(f"โมเดลโหลดสูงต่อเนื่อง (503) ลองใหม่อีกครั้งภายหลังครับ\n\n{last_error}")

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
                        with open(clean_path, "r", encoding="utf-8") as f:
                            file_data += f"\n\n--- ข้อมูลไฟล์: {clean_path} ---\n{f.read()}\n------------------\n"
                    except Exception:
                        pass
            if file_data:
                enhanced_prompt = f"{prompt}\n{file_data}"

            full_prompt = self.build_prompt_with_history(enhanced_prompt)
            output = self.call_gemini_cli(full_prompt)

            self.history.append(("user", enhanced_prompt))
            self.history.append(("model", output))

            # ==========================================
            # 1. จัดการ Execution (EXEC)
            # ==========================================
            exec_pattern = r"\[EXEC\](.*?)\[/EXEC\]"
            loop_count = 0
            has_executed = False 

            while re.search(exec_pattern, output) and loop_count < 2:
                loop_count += 1
                match = re.search(exec_pattern, output)
                cmd = match.group(1).strip()
                full_exec_tag = match.group(0)

                if self.ask_action_confirm("SHELL COMMAND", f"Command to execute:\n{cmd}"):
                    self.after(0, self.update_chat_ui, "System", f"⚙️ AI ได้รับอนุญาตให้รันคำสั่ง: {cmd}")

                    try:
                        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                        cmd_out = (res.stdout + res.stderr).strip()
                        if not cmd_out:
                            cmd_out = "(คำสั่งทำงานสำเร็จ แต่ไม่มีข้อความตอบกลับ)"

                        if len(cmd_out) > 4000:
                            cmd_out = cmd_out[:4000] + "\n...[ข้อความถูกตัดทิ้งเนื่องจากยาวเกินไป]..."

                    except Exception as e:
                        cmd_out = f"Error: {e}"

                    feedback_prompt = f"ผลลัพธ์จากการรัน `{cmd}`:\n```\n{cmd_out}\n```\nโปรดวิเคราะห์ผลลัพธ์นี้ต่อ"
                    full_prompt = self.build_prompt_with_history(feedback_prompt)
                    output = self.call_gemini_cli(full_prompt)

                    self.history.append(("user", feedback_prompt))
                    self.history.append(("model", output))
                    has_executed = True 
                else:
                    self.after(0, self.update_chat_ui, "System", f"❌ ผู้ใช้ยกเลิกคำสั่ง: {cmd}")
                    output = output.replace(full_exec_tag, f"\n[ระบบ]: ผู้ใช้ปฏิเสธการรันคำสั่ง `{cmd}`\n")
                    break 

            # ==========================================
            # 2. จัดการ Save File 
            # ==========================================
            save_pattern = r"\[SAVE:(.*?)\](.*?)\[/SAVE\]"
            
            if not has_executed or (has_executed and not re.search(exec_pattern, output)):
                for match in re.finditer(save_pattern, output, re.DOTALL):
                    file_path = match.group(1).strip()
                    clean_content = match.group(2).strip()
                    full_save_tag = match.group(0)
                    
                    if self.ask_action_confirm("SAVE FILE", f"Target Path: {file_path}\nFile Size: {len(clean_content)} bytes\n\nPreview Content:\n{clean_content[:200]}..."):
                        try:
                            with open(file_path, "w", encoding="utf-8") as f:
                                f.write(clean_content)
                            output = output.replace(full_save_tag, f"\n\n💾 [ระบบ]: ทำการแก้ไขและเซฟไฟล์ทับที่ {file_path} เรียบร้อยแล้ว!\n")
                        except Exception as e:
                            output = output.replace(full_save_tag, f"\n\n❌ [ระบบ]: เซฟไฟล์ไม่สำเร็จ: {e}\n")
                    else:
                        output = output.replace(full_save_tag, f"\n\n❌ [ระบบ]: ผู้ใช้ยกเลิกการเซฟไฟล์ที่ {file_path}\n")
            elif has_executed and re.search(exec_pattern, output):
                output = re.sub(save_pattern, f"\n\n⚠️ [ระบบ]: ระงับการบันทึกไฟล์ เนื่องจากตรวจพบคำสั่งเพิ่มเติมที่ยังไม่ได้ดำเนินการ\n", output, flags=re.DOTALL)

        except Exception as e:
            output = f"❌ Error จาก Gemini CLI:\n{e}"

        self.after(0, self.finish_response, output)

    def finish_response(self, output):
        self.chat_display.configure(state="normal")

        lines = self.chat_display.get("1.0", "end").split("\n")
        last_you_idx = 0
        for i, line in enumerate(reversed(lines)):
            if line.startswith("You:"):
                last_you_idx = len(lines) - 1 - i
                break

        if last_you_idx > 0:
            for i in range(last_you_idx + 1, len(lines)):
                if "[System]: กำลัง" in lines[i] or "[System]: ⚙️ AI" in lines[i]:
                    self.chat_display.delete(f"{i+1}.0", f"{i+2}.0")

        self.chat_display.configure(state="disabled")

        self.update_chat_ui("Gemini (CTF)", output.strip())
        self.send_btn.configure(state="normal")

        if hasattr(self.app_root, "record_activity"):
            self.app_root.record_activity(
                tool=f"Gemini CLI: {self.model_name}",
                category="Gemini CLI",
                action="AI Request",
                status="failed" if output.startswith("❌ Error") else "success",
                flags=find_flags(output),
                details=f"Response length: {len(output)} characters",
            )

    def update_chat_ui(self, sender, message):
        self.chat_display.configure(state="normal")
        if sender == "System":
            self.chat_display.insert("end", f"[{sender}]: {message}\n\n")
        else:
            self.chat_display.insert("end", f"{sender}:\n{message}\n\n")
        self.chat_display.see("end")
        self.chat_display.configure(state="disabled")
