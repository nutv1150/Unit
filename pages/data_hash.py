import customtkinter as ctk
from Encode.base_encoder import encode_data
from Decode.base_decoder import decode_data, custom_hex_to_hex, STANDARD_HEX_ALPHABET
from Hashing.hash_utils import hash_data
from Tools.extra_tools import (
    highlight_text,
    bitwise_mask,
    bitwise_unmask,
    detect_embedded_key,
)
from Tools.flag_detector import find_flags
from tkinter import filedialog, Menu, TclError

# ==========================================
# ธีมสีหลัก (Cyberpunk / Terminal)
# เหมือนกับ file_inspection.py / app_portal.py / gemini.py
# ==========================================
BG_COLOR = "#0D0D12"
PANEL_COLOR = "#15151E"
INPUT_BG = "#0A0A0F"
TERMINAL_BG = "#050508"
BORDER_DIM = "#333344"
ACCENT_CYAN = "#00FFFF"
ACCENT_GREEN = "#00FF41"
TEXT_DIM = "#8892B0"
ALERT_RED = "#FF3366"
ALERT_AMBER = "#FFB800"


class DataHashPage(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)
        self.app_root = master.master
        self.current_file_path = None
        self.configure(fg_color=BG_COLOR)

        # =========================
        # Algorithm Lists (เหมือนเดิมทุกประการ)
        # =========================
        self.encode_algos = [
            "Base64", "Base32", "Base45", "Base85",
            "Base16", "Base58", "Base62",
            "Hex", "Binary", "Octal", "Decimal",
            "URL Encode",
            "URL-safe Base64",
            "HTML Entity",
            "Unicode Escape", "Reverse", "ROT"
        ]

        self.decode_algos = [
            "Auto Detect", "Base64", "Base32",
            "Base45", "Base85", "Base58", "Base62", "Ascii85",
            "Base16", "Hex",
            "Binary", "Octal", "Decimal",
            "URL Decode",
            "URL-safe Base64",
            "HTML Entity",
            "Unicode Escape", "Reverse", "ROT"
        ]

        self.hash_algos = [
            "md5", "sha1", "sha224", "sha256",
            "sha384", "sha512",
            "sha3_224", "sha3_256",
            "sha3_384", "sha3_512",
            "blake2b", "blake2s"
        ]

        # ⭐ Bitwise algorithms จาก Tools
        self.bitwise_algos = [
            "XOR Mask",
            "XOR Unmask",
            "OR Mask",
            "AND Mask"
        ]

        # แผนที่ค่าเริ่มต้นของแต่ละโหมด (ใช้แทน logic การ "วน" โหมดแบบเดิม)
        self._mode_algos = {
            "Decode": (self.decode_algos, "Auto Detect"),
            "Encode": (self.encode_algos, "Base64"),
            "Hash": (self.hash_algos, "sha256"),
            "Bitwise": (self.bitwise_algos, "XOR Mask"),
        }

        # ปุ่มลัด (Quick Select) ต่อโหมด — เอาไว้กดรวดเร็วโดยไม่ต้องเปิด dropdown
        self._quick_selects = {
            "Decode": ["Auto Detect", "Base64", "Base32", "Hex", "URL Decode"],
            "Encode": ["Base64", "Base32", "Hex", "URL Encode", "ROT"],
            "Hash": ["sha256", "md5", "sha1", "sha512"],
            "Bitwise": ["XOR Mask", "XOR Unmask", "OR Mask", "AND Mask"],
        }

        self.mode = "Decode"
        self.mode_buttons = {}
        self.quick_buttons = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(6, weight=2)  # OUTPUT textbox ขยายมากที่สุด
        self.grid_rowconfigure(4, weight=1)  # INPUT textbox ขยายได้บ้าง

        # =========================
        # 1. Header (HUD Style)
        # =========================
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=30, pady=(20, 5))

        ctk.CTkLabel(
            header_frame, text=">_ DATA_FORGE :: [ENCODE / DECODE / HASH]",
            font=("Consolas", 28, "bold"), text_color=ACCENT_CYAN
        ).pack(anchor="w")

        ctk.CTkLabel(
            header_frame, text="Universal codec console — encode, decode, hash และ bitwise mask ในที่เดียว",
            font=("Consolas", 12), text_color=TEXT_DIM
        ).pack(anchor="w", pady=(2, 0))

        # =========================
        # 2. Mode Selector (Segmented Control)
        # =========================
        mode_bar = ctk.CTkFrame(self, fg_color=PANEL_COLOR, corner_radius=4, border_width=1, border_color=BORDER_DIM)
        mode_bar.grid(row=1, column=0, sticky="ew", padx=30, pady=(10, 8))

        mode_inner = ctk.CTkFrame(mode_bar, fg_color="transparent")
        mode_inner.pack(padx=15, pady=12, anchor="w")

        for name in ["Decode", "Encode", "Hash", "Bitwise"]:
            btn = ctk.CTkButton(
                mode_inner, text=f"[ {name.upper()} ]", width=110, height=32,
                font=("Consolas", 12, "bold"),
                command=lambda n=name: self.set_mode(n)
            )
            btn.pack(side="left", padx=(0, 8))
            self.mode_buttons[name] = btn

        # =========================
        # 3. Algorithm Bar (Dropdown + Quick chips + Bitwise Key)
        # =========================
        algo_bar = ctk.CTkFrame(self, fg_color=PANEL_COLOR, corner_radius=4, border_width=1, border_color=BORDER_DIM)
        algo_bar.grid(row=2, column=0, sticky="ew", padx=30, pady=8)

        algo_row = ctk.CTkFrame(algo_bar, fg_color="transparent")
        algo_row.pack(fill="x", padx=15, pady=(15, 8))

        ctk.CTkLabel(algo_row, text="ALGORITHM:", font=("Consolas", 12, "bold"), text_color=TEXT_DIM).pack(side="left", padx=(0, 10))

        self.algo_menu = ctk.CTkOptionMenu(
            algo_row,
            values=self.decode_algos,
            width=220, height=32,
            font=("Consolas", 12),
            fg_color="#1E1E2E", button_color="#2B2B36", button_hover_color="#3A3A4A",
            text_color="white",
            dropdown_fg_color="#1E1E2E", dropdown_hover_color="#2B2B36",
            dropdown_text_color="white", dropdown_font=("Consolas", 12),
            command=lambda _: self.on_algo_selected()
        )
        self.algo_menu.pack(side="left")

        # ⭐ Key สำหรับ Bitwise — โชว์เฉพาะตอนอยู่โหมด Bitwise เท่านั้น
        self.key_entry = ctk.CTkEntry(
            algo_row, placeholder_text="KEY (number / hex / text)",
            font=("Consolas", 12), height=32, width=220,
            fg_color=INPUT_BG, border_color=BORDER_DIM, text_color=ACCENT_CYAN
        )
        self.key_entry.pack(side="left", padx=(10, 0))
        self.key_entry.pack_forget()  # ซ่อนไว้ก่อน จะโชว์ตอนโหมด Bitwise

        # ROT ใช้ค่า shift และชุดอักขระที่ผู้ใช้เลือก
        self.rot_entry = ctk.CTkEntry(
            algo_row, placeholder_text="ROT n (alpha 1–25)",
            font=("Consolas", 12), height=32, width=150,
            fg_color=INPUT_BG, border_color=BORDER_DIM, text_color=ACCENT_CYAN,
        )
        self.rot_entry.insert(0, "13")
        self.rot_entry.bind("<KeyRelease>", self.process_data)
        self.rot_mode_var = ctk.StringVar(value="alpha (A-Z)")
        self.rot_mode_menu = ctk.CTkOptionMenu(
            algo_row, values=["alpha (A-Z)", "ascii (33-126)"],
            width=150, height=32, font=("Consolas", 11),
            variable=self.rot_mode_var, command=lambda _: self.process_data(),
        )

        # แถวปุ่มลัด (Quick Select)
        self.quick_row = ctk.CTkFrame(algo_bar, fg_color="transparent")
        self.quick_row.pack(fill="x", padx=15, pady=(0, 15))

        self.custom_hex_panel = ctk.CTkFrame(algo_bar, fg_color="transparent")
        ctk.CTkLabel(
            self.custom_hex_panel, text="ALPHABET → 0123456789ABCDEF | เปลี่ยนสัญลักษณ์ตามลำดับ 0–F",
            font=("Consolas", 11), text_color=TEXT_DIM,
        ).pack(anchor="w")
        self.custom_hex_entry = ctk.CTkEntry(
            self.custom_hex_panel, width=300, height=32, font=("Consolas", 12),
            fg_color=INPUT_BG, border_color=BORDER_DIM, text_color=ACCENT_CYAN,
        )
        self.custom_hex_entry.insert(0, STANDARD_HEX_ALPHABET)
        self.custom_hex_entry.pack(anchor="w", pady=(4, 4))
        self.custom_hex_entry.bind("<KeyRelease>", self.process_data)
        self.custom_hex_preview = ctk.CTkLabel(
            self.custom_hex_panel, text="HEX PREVIEW: —", anchor="w",
            font=("Consolas", 11), text_color=TEXT_DIM,
        )
        self.custom_hex_preview.pack(anchor="w")

        # =========================
        # 4. INPUT SECTION
        # =========================
        input_header = ctk.CTkFrame(self, fg_color="transparent")
        input_header.grid(row=3, column=0, sticky="ew", padx=30, pady=(10, 0))

        ctk.CTkLabel(input_header, text=">_ INPUT_STREAM", font=("Consolas", 14, "bold"), text_color=ACCENT_CYAN).pack(side="left")

        ctk.CTkButton(
            input_header, text="[ BROWSE ]", width=100, height=28,
            font=("Consolas", 12, "bold"), fg_color="transparent",
            border_width=1, border_color=ACCENT_CYAN, text_color=ACCENT_CYAN,
            hover_color="#003344", command=self.browse_file
        ).pack(side="right")

        self.input_box = ctk.CTkTextbox(
            self, height=150, fg_color=TERMINAL_BG, text_color="white",
            font=("Consolas", 13), border_width=1, border_color=BORDER_DIM, corner_radius=4
        )
        self.input_box.grid(row=4, column=0, sticky="nsew", padx=30, pady=(5, 10))

        # =========================
        # 5. OUTPUT SECTION
        # =========================
        output_header = ctk.CTkFrame(self, fg_color="transparent")
        output_header.grid(row=5, column=0, sticky="ew", padx=30, pady=(5, 0))

        ctk.CTkLabel(output_header, text=">_ OUTPUT_STREAM", font=("Consolas", 14, "bold"), text_color=ACCENT_CYAN).pack(side="left")

        self.output_label_btn = ctk.CTkButton(
            output_header, text="Decode • Auto Detect", width=170, height=28,
            font=("Consolas", 11, "bold"), fg_color=PANEL_COLOR,
            border_width=1, border_color=BORDER_DIM, text_color=TEXT_DIM,
            hover_color=PANEL_COLOR, state="disabled"
        )
        self.output_label_btn.pack(side="left", padx=10)

        ctk.CTkButton(
            output_header, text="[ FIND ]", width=70, height=28,
            font=("Consolas", 12, "bold"), fg_color="transparent",
            border_width=1, border_color=ACCENT_GREEN, text_color=ACCENT_GREEN,
            hover_color="#003311", command=self.search_output
        ).pack(side="right")

        self.search_entry = ctk.CTkEntry(
            output_header, placeholder_text="Search in output...",
            font=("Consolas", 12), height=28, width=200,
            fg_color=INPUT_BG, border_color=BORDER_DIM, text_color="white"
        )
        self.search_entry.pack(side="right", padx=8)

        self.output_box = ctk.CTkTextbox(
            self, fg_color=TERMINAL_BG, text_color=ACCENT_GREEN,
            font=("Consolas", 13), border_width=1, border_color=BORDER_DIM, corner_radius=4
        )
        self.output_box.grid(row=6, column=0, sticky="nsew", padx=30, pady=(5, 20))
        self.output_box.tag_config("found", background=ACCENT_CYAN, foreground="black")

        self.gemini_selection = ""
        self.context_menu = Menu(
            self, tearoff=0, bg=PANEL_COLOR, fg="white",
            activebackground=ACCENT_CYAN, activeforeground="black",
            font=("Consolas", 11),
        )
        self.context_menu.add_command(
            label="Send selection to Gemini", command=self.send_selection_to_gemini,
        )
        for textbox in (self.input_box, self.output_box):
            textbox.bind(
                "<Button-3>",
                lambda event, box=textbox: self.show_context_menu(event, box),
            )

        self.input_box.bind("<KeyRelease>", self.process_data)

        # ตั้งค่าเริ่มต้น: โหมด Decode + สร้างปุ่มลัดชุดแรก + ไฮไลต์ปุ่มโหมด
        self.refresh_quick_chips()
        self.update_mode_button_styles()

    def show_context_menu(self, event, textbox):
        # เก็บเฉพาะข้อความที่เลือกในช่องที่คลิก ก่อน popup เปลี่ยน focus
        try:
            self.gemini_selection = textbox.get("sel.first", "sel.last")
        except TclError:
            self.gemini_selection = ""
        self.context_menu.entryconfigure(
            0, state="normal" if self.gemini_selection.strip() else "disabled",
        )
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()
        return "break"

    def send_selection_to_gemini(self):
        if self.gemini_selection.strip():
            self.app_root.send_to_gemini(self.gemini_selection)

    # =========================
    # Process Main Logic
    # =========================
    def process_data(self, event=None):
        data = self.input_box.get("1.0", "end").strip()
        algo = self.algo_menu.get()

        self.custom_hex_preview.configure(text="HEX PREVIEW: —")

        if not data:
            self.output_box.delete("1.0", "end")
            self.current_detected_algo = None # เคลียร์ค่าที่เจอ
            self.update_output_label()
            return

        try:
            if algo == "ROT":
                n = int(self.rot_entry.get().strip() or "13")
                mode = "ascii" if self.rot_mode_var.get().startswith("ascii") else "alpha"
                algo = f"ROT:{n}:{mode}"
            if self.mode == "Encode":
                result = encode_data(data, algo)

            elif self.mode == "Decode":
                # ⭐ แก้ไข: ถ้าเป็น Auto Detect ให้ไปเรียกฟังก์ชันหลักมาตรงๆ เพื่อเอาชื่อด้วย
                if algo == "Hex":
                    alphabet = self.custom_hex_entry.get()
                    hex_text = custom_hex_to_hex(data, alphabet)
                    preview = hex_text[:80] + ("…" if len(hex_text) > 80 else "")
                    self.custom_hex_preview.configure(text=f"HEX PREVIEW: {preview}")
                    result = decode_data(data, algo, alphabet=alphabet)
                    self.current_detected_algo = algo
                elif algo == "Auto Detect":
                    from Decode.base_decoder import auto_detect_decode
                    detected_name, result = auto_detect_decode(data.encode())
                    self.current_detected_algo = detected_name # บันทึกชื่อที่หาเจอไว้
                else:
                    result = decode_data(data, algo)
                    self.current_detected_algo = algo # ถ้าไม่ได้ Auto ก็ใช้ชื่อจากเมนู

            elif self.mode == "Hash":
                result = hash_data(data, algo)

            elif self.mode == "Bitwise":

                key = self.key_entry.get().strip()

                # =====================================================
                # P0.4A - AUTO KEY DETECTION
                # =====================================================

                if not key:

                    detected_key = detect_embedded_key(
                        data
                    )

                    if detected_key:

                        key = detected_key["key"]

                        # เติม key ลงช่อง UI ให้ user เห็น
                        self.key_entry.delete(
                            0,
                            "end"
                        )

                        self.key_entry.insert(
                            0,
                            key
                        )

                    else:
                        raise ValueError(
                            "กรุณาใส่ Key "
                            "หรือวางข้อมูลที่มี key เช่น "
                            "$key = 0x4A"
                        )

                if algo == "XOR Mask":
                    result = bitwise_mask(
                        data,
                        key,
                        "xor"
                    )

                elif algo == "XOR Unmask":
                    result = bitwise_unmask(
                        data,
                        key
                    )

                elif algo == "OR Mask":
                    result = bitwise_mask(
                        data,
                        key,
                        "or"
                    )

                elif algo == "AND Mask":
                    result = bitwise_mask(
                        data,
                        key,
                        "and"
                    )

            self.output_box.delete("1.0", "end")
            self.output_box.insert("1.0", result)

            self._record_activity(
                tool=f"{self.mode}: {algo}",
                action=self.mode,
                status="success",
                flags=find_flags(result),
                details=f"Input length: {len(data)} characters",
            )

        except Exception as e:
            self.output_box.delete("1.0", "end")
            self.output_box.insert("1.0", f"Error: {e}")
            self._record_activity(
                tool=f"{self.mode}: {algo}",
                action=self.mode,
                status="failed",
                details=str(e),
            )

        # อัปเดต Label หลังจากประมวลผลเสร็จ
        self.update_output_label()

    # =========================
    # Highlight Output
    # =========================
    def search_output(self):
        highlight_text(self.output_box, self.search_entry.get())

    # =========================
    # Browse File
    # =========================
    def browse_file(self):

        file_path = filedialog.askopenfilename(
            filetypes=[("Text Files", "*.txt *.json *.log *.py *.md"), ("All Files", "*.*")]
        )

        if not file_path:
            return

        try:
            self.current_file_path = file_path
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            self.input_box.delete("1.0", "end")
            self.input_box.insert("1.0", content)
            self.process_data()

        except Exception as e:
            print("Read file error:", e)

    def _record_activity(self, tool, action, status, flags=None, details=""):
        if not hasattr(self.app_root, "record_activity"):
            return
        self.app_root.record_activity(
            tool=tool,
            category="Data Hashing",
            action=action,
            status=status,
            file_path=self.current_file_path,
            flags=flags or [],
            details=details,
        )

    # =========================
    # Mode Selector (Segmented Control)
    # =========================
    def set_mode(self, name):
        """สลับโหมดโดยตรง (Decode / Encode / Hash / Bitwise) แทนการวนปุ่มเดิม
        logic การประมวลผลข้างในยังเหมือนเดิมทุกอย่าง แค่เปลี่ยนวิธีเลือกโหมดใน UI"""

        if name not in self._mode_algos:
            return

        self.mode = name
        algos, default_algo = self._mode_algos[name]

        self.algo_menu.configure(values=algos)
        self.algo_menu.set(default_algo)

        # โชว์ช่อง Key เฉพาะโหมด Bitwise เท่านั้น
        if name == "Bitwise":
            self.key_entry.pack(side="left", padx=(10, 0))
        else:
            self.key_entry.pack_forget()

        self.update_mode_button_styles()
        self.refresh_quick_chips()
        self.on_algo_selected()

    def update_mode_button_styles(self):
        """ไฮไลต์ปุ่มโหมดที่กำลังใช้งานอยู่ (สไตล์เดียวกับ segmented control หน้าอื่น)"""
        for name, btn in self.mode_buttons.items():
            if name == self.mode:
                btn.configure(fg_color=ACCENT_CYAN, text_color="black", hover_color="#00CCCC", border_width=0)
            else:
                btn.configure(fg_color="transparent", text_color=TEXT_DIM, hover_color="#2B2B36",
                               border_width=1, border_color=BORDER_DIM)

    # =========================
    # Quick Select Chips
    # =========================
    def refresh_quick_chips(self):
        """สร้างปุ่มลัดใหม่ตามโหมดปัจจุบัน (แก้บั๊กเดิมที่ select_tab ไม่มีอยู่จริง)"""
        for btn in self.quick_buttons:
            btn.destroy()
        self.quick_buttons = []

        for algo in self._quick_selects.get(self.mode, []):
            btn = ctk.CTkButton(
                self.quick_row, text=algo, height=26,
                font=("Consolas", 11, "bold"),
                command=lambda a=algo: self.select_quick_algo(a)
            )
            btn.pack(side="left", padx=(0, 6))
            self.quick_buttons.append(btn)

        self.refresh_quick_chip_styles()

    def refresh_quick_chip_styles(self):
        current = self.algo_menu.get()
        for btn in self.quick_buttons:
            if btn.cget("text") == current:
                btn.configure(fg_color=ACCENT_GREEN, text_color="black", hover_color="#00CC33")
            else:
                btn.configure(fg_color="transparent", text_color=TEXT_DIM, hover_color="#2B2B36",
                               border_width=1, border_color=BORDER_DIM)

    def select_quick_algo(self, algo):
        self.algo_menu.set(algo)
        self.on_algo_selected()

    def on_algo_selected(self):
        if self.mode == "Decode" and self.algo_menu.get() == "Hex":
            self.custom_hex_panel.pack(fill="x", padx=15, pady=(0, 12))
        else:
            self.custom_hex_panel.pack_forget()
        if self.algo_menu.get() == "ROT" and self.mode in ("Encode", "Decode"):
            self.rot_entry.pack(side="left", padx=(10, 0))
            self.rot_mode_menu.pack(side="left", padx=(4, 0))
        else:
            self.rot_entry.pack_forget()
            self.rot_mode_menu.pack_forget()
        self.refresh_quick_chip_styles()
        self.process_data()

    # =========================
    # Update Label
    # =========================
    def update_output_label(self):
        # ⭐ แก้ไข: ให้โชว์ป้ายกำกับเท่ๆ เวลาใช้งาน Auto Detect
        if self.mode == "Decode" and self.algo_menu.get() == "Auto Detect":
            detected = getattr(self, "current_detected_algo", None)

            # ⭐ แก้บั๊ก: ตอนเคลียร์ INPUT จนว่าง current_detected_algo จะถูกตั้งเป็น None
            # (ไม่ใช่ attribute หายไป) ต้องเช็คทั้ง None และ "Unknown" ไม่งั้น .upper() จะพัง
            if not detected or detected == "Unknown":
                self.output_label_btn.configure(
                    text="AUTO_DETECT :: ❓ UNKNOWN",
                    fg_color=PANEL_COLOR, border_color=ALERT_RED, text_color=ALERT_RED
                )
            else:
                self.output_label_btn.configure(
                    text=f"AUTO_DETECT :: 🎯 {detected.upper()}",
                    fg_color=PANEL_COLOR, border_color=ACCENT_GREEN, text_color=ACCENT_GREEN
                )
        else:
            self.output_label_btn.configure(
                text=f"{self.mode.upper()} • {self.algo_menu.get()}",
                fg_color=PANEL_COLOR, border_color=ACCENT_CYAN, text_color=ACCENT_CYAN
            )
