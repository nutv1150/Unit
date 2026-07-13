import customtkinter as ctk
import threading
import os
import re
import subprocess
import shutil


class GeminiPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)

        # --- 1. ส่วนเชื่อมต่อ Gemini CLI ---
        api_container = ctk.CTkFrame(self, fg_color="transparent")
        api_container.pack(pady=20, fill="x", padx=100)

        self.api_entry = ctk.CTkEntry(
            api_container,
            placeholder_text="(ถ้าไม่ได้ login gemini CLI ไว้) วาง API Key ที่นี่ - เว้นว่างได้ถ้า login แล้ว",
            show="*",
        )
        self.api_entry.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            api_container, text="เชื่อมต่อ CLI", width=100, command=self.init_api
        ).pack(side="left", padx=10)

        self.status_label = ctk.CTkLabel(
            self,
            text="ยังไม่ได้เชื่อมต่อ Gemini CLI",
            anchor="w",
        )
        self.status_label.pack(fill="x", padx=100)

        # --- 2. ส่วนหัวโปรแกรม ---
        ctk.CTkLabel(self, text="GEMINI AI (CTF MODE)", font=("Impact", 50), text_color="#A9CCE3").pack(pady=10)
        ctk.CTkLabel(self, text="Gemini CLI Wrapper + Auto Save & Execute", font=("Arial", 12, "italic"), text_color="#5DADE2").place(relx=0.95, rely=0.8, anchor="e")

        # --- 3. กล่องแสดงแชท ---
        self.chat_display = ctk.CTkTextbox(self, font=("Arial", 14), state="disabled", wrap="word")
        self.chat_display.pack(expand=True, fill="both", padx=100, pady=10)

        # --- 4. กล่องพิมพ์ข้อความ ---
        input_container = ctk.CTkFrame(self, fg_color="transparent")
        input_container.pack(side="bottom", fill="x", padx=100, pady=20)

        self.input_field = ctk.CTkEntry(
            input_container,
            placeholder_text="สั่งให้ AI วิเคราะห์ไฟล์ หรือรันคำสั่ง (เช่น 'รัน zsteg ดูรูปนี้หน่อย')",
            height=40,
        )
        self.input_field.pack(side="left", fill="x", expand=True)
        self.input_field.bind("<Return>", lambda event: self.send_message())

        self.send_btn = ctk.CTkButton(input_container, text="Enter", width=80, height=40, command=self.send_message)
        self.send_btn.pack(side="left", padx=10)

        # ตัวแปรควบคุม state
        self.cli_ready = False
        self.gemini_cmd = "gemini"          # ชื่อคำสั่ง CLI (แก้ตรงนี้ได้ถ้า path ไม่ตรง)
        self.model_name = "gemini-2.5-flash"  # แก้เป็นโมเดลที่ CLI ของคุณรองรับ
        self.api_key = None  # ถ้าผู้ใช้กรอกมา จะส่งเป็น env var ให้ CLI ใช้แทน OAuth login

        # เก็บ system prompt + ประวัติแชทไว้เอง เพราะ CLI แบบ one-shot ไม่มี session ให้
        self.system_prompt = (
            "คุณคือ Cybersecurity Expert และ AI Assistant สำหรับแข่ง CTF "
            "คุณสามารถเซฟไฟล์ได้โดยใช้ [SAVE:ที่อยู่ไฟล์]...เนื้อหา...[/SAVE] "
            "และสามารถรันคำสั่ง Terminal ในเครื่องได้ด้วยแท็ก [EXEC]คำสั่ง[/EXEC] "
            "⚠️ กฎเหล็ก: ห้ามพิมพ์แท็ก [EXEC] หรือ [SAVE] เพื่อยกตัวอย่าง แนะนำตัว หรือทักทายเด็ดขาด! "
            "ถ้าผู้ใช้แค่ทักทาย (เช่น พิมพ์ hello) หรือถามทฤษฎีทั่วไป ให้ตอบกลับด้วยข้อความธรรมดา ห้ามใช้แท็กใดๆ ทั้งสิ้น "
            "ให้ใช้แท็กเหล่านี้เฉพาะตอนที่จำเป็นต้อง 'รันคำสั่งเพื่อแก้โจทย์' หรือ 'เขียนไฟล์จริงๆ' เท่านั้น"
        )
        self.history = []  # list ของ ("user"/"model", text)

    # ------------------------------------------------------------------
    # เชื่อมต่อ / เช็คว่ามี Gemini CLI ในเครื่องไหม
    # ------------------------------------------------------------------
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

        # รันการเช็ค/ทดสอบ CLI ใน background thread เพื่อไม่ให้ UI ค้าง
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
            )
            version_info = (res.stdout or res.stderr).strip()

            # ทดสอบยิง prompt สั้นๆ จริงๆ เพื่อเช็คว่า auth ผ่านไหม (ไม่ใช่แค่เช็คว่ามีคำสั่ง)
            test_res = subprocess.run(
                [self.gemini_cmd, "-m", self.model_name, "-p", "hi"],
                capture_output=True,
                text=True,
                timeout=60,
                env=self._build_env(),
                stdin=subprocess.DEVNULL,
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
        self.status_label.configure(text=f"✅ เชื่อมต่อแล้ว: {version_info or self.gemini_cmd}")
        self.update_chat_ui("System", "✅ CTF Mode พร้อมลุย! (เชื่อมต่อผ่าน Gemini CLI)")

    def _init_api_fail(self, status_text, message):
        self.status_label.configure(text=status_text)
        self.update_chat_ui("System", message)

    def _build_env(self):
        """สร้าง environment variables ให้ subprocess โดยแนบ API key และ trust flag เข้าไป"""
        env = os.environ.copy()
        if self.api_key:
            env["GEMINI_API_KEY"] = self.api_key
            env["GOOGLE_API_KEY"] = self.api_key
        # ป้องกัน error "not running in a trusted directory" เวลารันแบบ non-interactive
        env["GEMINI_CLI_TRUST_WORKSPACE"] = "true"
        return env

    # ------------------------------------------------------------------
    # ส่งข้อความ
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # เรียก Gemini CLI แบบ non-interactive
    # ------------------------------------------------------------------
    def call_gemini_cli(self, prompt_text):
        """
        เรียก gemini CLI แบบ one-shot (-p) แล้วคืนค่า stdout
        ปรับ flag ตรงนี้ให้ตรงกับเวอร์ชัน CLI ที่ติดตั้งจริง ถ้าจำเป็น
        """
        cmd = [self.gemini_cmd, "-m", self.model_name, "-p", prompt_text]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            env=self._build_env(),
            stdin=subprocess.DEVNULL,
        )
        combined_err = result.stderr.strip()
        if "UNAUTHENTICATED" in combined_err or "invalid authentication" in combined_err.lower():
            raise RuntimeError(
                "Auth ไม่ผ่าน: กรุณา login ผ่าน `gemini` ในเทอร์มินัล หรือใส่ API Key แล้วกด 'เชื่อมต่อ CLI' ใหม่"
            )
        if result.returncode != 0 and not result.stdout.strip():
            raise RuntimeError(combined_err or "Gemini CLI คืนค่า error โดยไม่มีรายละเอียด")
        return (result.stdout or result.stderr).strip()

    def build_prompt_with_history(self, new_user_text):
        """
        ต่อ system prompt + ประวัติแชทเดิม + ข้อความใหม่ เป็น prompt เดียว
        เพื่อจำลอง 'session' เพราะ CLI แบบ one-shot ไม่มี state ให้เอง
        """
        parts = [f"[SYSTEM INSTRUCTION]\n{self.system_prompt}\n"]
        for role, text in self.history:
            tag = "USER" if role == "user" else "MODEL"
            parts.append(f"[{tag}]\n{text}\n")
        parts.append(f"[USER]\n{new_user_text}\n[MODEL]\n")
        return "\n".join(parts)

    def process_request(self, prompt):
        try:
            enhanced_prompt = prompt
            words = prompt.split()
            file_data = ""

            # 1. แอบอ่านไฟล์ก่อนส่งคำถาม (ถ้าผู้ใช้พิมพ์พาธไฟล์มา)
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

            # 2. คุยกับ AI ครั้งแรก (ผ่าน CLI)
            full_prompt = self.build_prompt_with_history(enhanced_prompt)
            output = self.call_gemini_cli(full_prompt)

            self.history.append(("user", enhanced_prompt))
            self.history.append(("model", output))

            # 🔥 3. ระบบ Agent: ดักจับแท็ก [EXEC] และรันคำสั่งอัตโนมัติ (ลิมิต 2 รอบกันโควตาพัง)
            exec_pattern = r"\[EXEC\](.*?)\[/EXEC\]"
            loop_count = 0

            while re.search(exec_pattern, output) and loop_count < 2:
                loop_count += 1
                match = re.search(exec_pattern, output)
                cmd = match.group(1).strip()

                self.after(0, self.update_chat_ui, "System", f"⚙️ AI กำลังรันคำสั่ง: {cmd}")

                try:
                    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                    cmd_out = (res.stdout + res.stderr).strip()
                    if not cmd_out:
                        cmd_out = "(คำสั่งทำงานสำเร็จ แต่ไม่มีข้อความตอบกลับ)"

                    # 🛡️ ระบบป้องกันข้อความยาวเกินไป
                    if len(cmd_out) > 4000:
                        cmd_out = cmd_out[:4000] + "\n...[ข้อความถูกตัดทิ้งเนื่องจากยาวเกินไป]..."

                except Exception as e:
                    cmd_out = f"Error: {e}"

                feedback_prompt = f"ผลลัพธ์จากการรัน `{cmd}`:\n```\n{cmd_out}\n```\nโปรดวิเคราะห์ผลลัพธ์นี้ต่อ"
                full_prompt = self.build_prompt_with_history(feedback_prompt)
                output = self.call_gemini_cli(full_prompt)

                self.history.append(("user", feedback_prompt))
                self.history.append(("model", output))

        except Exception as e:
            output = f"❌ Error จาก Gemini CLI:\n{e}"

        self.after(0, self.finish_response, output)

    def finish_response(self, output):
        # 4. ดักจับเผื่อมีการสั่ง [SAVE:...] โค้ด
        save_pattern = r"\[SAVE:(.*?)\](.*?)\[/SAVE\]"
        matches = re.findall(save_pattern, output, re.DOTALL)

        for file_path, content in matches:
            clean_path = file_path.strip()
            clean_content = content.strip()
            full_tag = f"[SAVE:{file_path}]{content}[/SAVE]"
            try:
                with open(clean_path, "w", encoding="utf-8") as f:
                    f.write(clean_content)
                output = output.replace(full_tag, f"\n\n💾 [ระบบ]: ทำการแก้ไขและเซฟไฟล์ทับที่ {clean_path} เรียบร้อยแล้ว!\n")
            except Exception as e:
                output = output.replace(full_tag, f"\n\n❌ [ระบบ]: เซฟไฟล์ไม่สำเร็จ: {e}\n")

        # เคลียร์หน้าจอแล้วแสดงผลสรุปสุดท้าย
        self.chat_display.configure(state="normal")

        # ลบข้อความ [System] ที่โหลดๆ อยู่ออกให้หมด
        lines = self.chat_display.get("1.0", "end").split("\n")
        last_you_idx = 0
        for i, line in enumerate(reversed(lines)):
            if line.startswith("You:"):
                last_you_idx = len(lines) - 1 - i
                break

        if last_you_idx > 0:
            for i in range(last_you_idx + 1, len(lines)):
                if "[System]: กำลัง" in lines[i] or "[System]: ⚙️ AI กำลังรัน" in lines[i]:
                    self.chat_display.delete(f"{i+1}.0", f"{i+2}.0")

        self.chat_display.configure(state="disabled")

        self.update_chat_ui("Gemini (CTF)", output.strip())
        self.send_btn.configure(state="normal")

    def update_chat_ui(self, sender, message):
        self.chat_display.configure(state="normal")
        if sender == "System":
            self.chat_display.insert("end", f"[{sender}]: {message}\n\n")
        else:
            self.chat_display.insert("end", f"{sender}:\n{message}\n\n")
        self.chat_display.see("end")
        self.chat_display.configure(state="disabled")