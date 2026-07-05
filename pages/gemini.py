import customtkinter as ctk
import google.generativeai as genai
import threading
import os
import re
import subprocess

class GeminiPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)

        # --- 1. ส่วนกรอก API Key ---
        api_container = ctk.CTkFrame(self, fg_color="transparent")
        api_container.pack(pady=20, fill="x", padx=100)
        
        self.api_entry = ctk.CTkEntry(api_container, placeholder_text="วาง API Key ของคุณที่นี่...", show="*")
        self.api_entry.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(api_container, text="เชื่อมต่อ API", width=80, command=self.init_api).pack(side="left", padx=10)

        # --- 2. ส่วนหัวโปรแกรม ---
        ctk.CTkLabel(self, text="GEMINI AI (CTF MODE)", font=("Impact", 50), text_color="#A9CCE3").pack(pady=10)
        ctk.CTkLabel(self, text="Python SDK + Auto Save & Execute (Anti-Quota Ban)", font=("Arial", 12, "italic"), text_color="#5DADE2").place(relx=0.95, rely=0.8, anchor="e")

        # --- 3. กล่องแสดงแชท ---
        self.chat_display = ctk.CTkTextbox(self, font=("Arial", 14), state="disabled", wrap="word")
        self.chat_display.pack(expand=True, fill="both", padx=100, pady=10)

        # --- 4. กล่องพิมพ์ข้อความ ---
        input_container = ctk.CTkFrame(self, fg_color="transparent")
        input_container.pack(side="bottom", fill="x", padx=100, pady=20)
        
        self.input_field = ctk.CTkEntry(input_container, placeholder_text="สั่งให้ AI วิเคราะห์ไฟล์ หรือรันคำสั่ง (เช่น 'รัน zsteg ดูรูปนี้หน่อย')", height=40)
        self.input_field.pack(side="left", fill="x", expand=True)
        self.input_field.bind("<Return>", lambda event: self.send_message())
        
        self.send_btn = ctk.CTkButton(input_container, text="Enter", width=80, height=40, command=self.send_message)
        self.send_btn.pack(side="left", padx=10)

        self.chat_session = None

    def init_api(self):
        api_key = self.api_entry.get().strip()
        if not api_key:
            self.update_chat_ui("System", "กรุณาใส่ API Key ก่อนครับ!")
            return
        
        try:
            genai.configure(api_key=api_key)
            
            # 🔥 System Prompt กฎเหล็ก ห้ามใช้แท็กพร่ำเพรื่อ
            system_prompt = (
                "คุณคือ Cybersecurity Expert และ AI Assistant สำหรับแข่ง CTF "
                "คุณสามารถเซฟไฟล์ได้โดยใช้ [SAVE:ที่อยู่ไฟล์]...เนื้อหา...[/SAVE] "
                "และสามารถรันคำสั่ง Terminal ในเครื่องได้ด้วยแท็ก [EXEC]คำสั่ง[/EXEC] "
                "⚠️ กฎเหล็ก: ห้ามพิมพ์แท็ก [EXEC] หรือ [SAVE] เพื่อยกตัวอย่าง แนะนำตัว หรือทักทายเด็ดขาด! "
                "ถ้าผู้ใช้แค่ทักทาย (เช่น พิมพ์ hello) หรือถามทฤษฎีทั่วไป ให้ตอบกลับด้วยข้อความธรรมดา ห้ามใช้แท็กใดๆ ทั้งสิ้น "
                "ให้ใช้แท็กเหล่านี้เฉพาะตอนที่จำเป็นต้อง 'รันคำสั่งเพื่อแก้โจทย์' หรือ 'เขียนไฟล์จริงๆ' เท่านั้น"
            )
            
            model = genai.GenerativeModel(
                'gemini-2.5-flash', 
                system_instruction=system_prompt
            )
            self.chat_session = model.start_chat(history=[])
            
            self.update_chat_ui("System", "✅ CTF Mode พร้อมลุย! (ระบบป้องกันโควตาเต็มทำงานอยู่)")
            self.api_entry.configure(state="disabled")
        except Exception as e:
            self.update_chat_ui("System", f"❌ การเชื่อมต่อล้มเหลว: {e}")

    def send_message(self):
        user_text = self.input_field.get().strip()
        if not user_text: return
        if not self.chat_session:
            self.update_chat_ui("System", "⚠️ กรุณาเชื่อมต่อ API ก่อนครับ!")
            return

        self.update_chat_ui("You", user_text)
        self.input_field.delete(0, "end")
        self.send_btn.configure(state="disabled")
        self.update_chat_ui("System", "กำลังวิเคราะห์...")
        
        threading.Thread(target=self.process_request, args=(user_text,), daemon=True).start()

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
                        with open(clean_path, 'r', encoding='utf-8') as f:
                            file_data += f"\n\n--- ข้อมูลไฟล์: {clean_path} ---\n{f.read()}\n------------------\n"
                    except: pass
            if file_data: enhanced_prompt = f"{prompt}\n{file_data}"

            # 2. คุยกับ AI ครั้งแรก
            response = self.chat_session.send_message(enhanced_prompt)
            output = response.text

            # 🔥 3. ระบบ Agent: ดักจับแท็ก [EXEC] และรันคำสั่งอัตโนมัติ (ลิมิต 2 รอบกันโควตาพัง)
            exec_pattern = r'\[EXEC\](.*?)\[/EXEC\]'
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
                    
                    # 🛡️ ระบบป้องกันโควตาระเบิด ตัดข้อความที่ยาวเกินไป
                    if len(cmd_out) > 4000:
                        cmd_out = cmd_out[:4000] + "\n...[ข้อความถูกตัดทิ้งเนื่องจากยาวเกินไปเพื่อประหยัดโควตา API]..."
                        
                except Exception as e:
                    cmd_out = f"Error: {e}"
                
                feedback_prompt = f"ผลลัพธ์จากการรัน `{cmd}`:\n```\n{cmd_out}\n```\nโปรดวิเคราะห์ผลลัพธ์นี้ต่อ"
                response = self.chat_session.send_message(feedback_prompt)
                output = response.text

        except Exception as e:
            output = f"❌ Error จาก API:\n{e}"
        
        self.after(0, self.finish_response, output)

    def finish_response(self, output):
        # 4. ดักจับเผื่อมีการสั่ง [SAVE:...] โค้ด
        save_pattern = r'\[SAVE:(.*?)\](.*?)\[/SAVE\]'
        matches = re.findall(save_pattern, output, re.DOTALL)
        
        for file_path, content in matches:
            clean_path = file_path.strip()
            clean_content = content.strip()
            full_tag = f"[SAVE:{file_path}]{content}[/SAVE]"
            try:
                with open(clean_path, 'w', encoding='utf-8') as f: f.write(clean_content)
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