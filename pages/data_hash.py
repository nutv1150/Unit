import customtkinter as ctk
from Encode.base_encoder import encode_data
from Decode.base_decoder import decode_data
from Hashing.hash_utils import hash_data
from Tools.extra_tools import highlight_text, bitwise_mask, bitwise_unmask
from tkinter import filedialog


class DataHashPage(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)

        # =========================
        # Algorithm Lists
        # =========================
        self.encode_algos = [
            "Base64", "Base32", "Base45", "Base85",
            "Base16", "Base58", "Base62",
            "Hex", "Binary", "Octal", "Decimal",
            "URL Encode",
            "URL-safe Base64",
            "HTML Entity",
            "Unicode Escape","Reverse","ROT13"
        ]

        self.decode_algos = [
            "Auto Detect", "Base64", "Base32",
            "Base45", "Base85", "Base58", "Base62","Ascii85",
            "Base16", "Hex",
            "Binary", "Octal", "Decimal",
            "URL Decode",
            "URL-safe Base64",
            "HTML Entity",
            "Unicode Escape","Reverse","ROT13"
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

        self.mode = "Decode"
        self.tab_buttons = {}

        # =========================
        # Title
        # =========================
        ctk.CTkLabel(
            self,
            text="Data Hashing Encoding And Decoding",
            font=("Arial", 18, "bold")
        ).pack(anchor="w", padx=20, pady=(20, 10))

        # =========================
        # Top Control Bar
        # =========================
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=20)

        self.mode_btn = ctk.CTkButton(
            top_bar,
            text="Decode",
            width=100,
            command=self.toggle_mode
        )
        self.mode_btn.pack(side="left", padx=5)

        self.algo_menu = ctk.CTkOptionMenu(
            top_bar,
            values=self.decode_algos,
            width=200,
            command=lambda _: self.process_data()
        )
        self.algo_menu.pack(side="left", padx=5)

        # =========================
        # Tabs Quick Select
        # =========================
        tab_frame = ctk.CTkFrame(self, fg_color="transparent")
        tab_frame.pack(fill="x", padx=20, pady=10)

        tabs = ["Auto Detect", "Base64", "Base32", "Hex"]

        for t in tabs:
            btn = ctk.CTkButton(
                tab_frame,
                text=t,
                width=80,
                fg_color=None if t == "Auto Detect" else "gray",
                command=lambda name=t: self.select_tab(name)
            )
            btn.pack(side="left", padx=4)
            self.tab_buttons[t] = btn

        # =========================
        # INPUT SECTION
        # =========================
        input_header = ctk.CTkFrame(self, fg_color="transparent")
        input_header.pack(fill="x", padx=20)

        ctk.CTkLabel(input_header, text="INPUT", font=("Arial", 12, "bold")).pack(side="left")

        ctk.CTkButton(
            input_header,
            text="Browse",
            width=60,
            command=self.browse_file
        ).pack(side="left", padx=10)

        self.input_box = ctk.CTkTextbox(self, height=150)
        self.input_box.pack(fill="x", padx=20, pady=(5, 10))

        # ⭐ Key สำหรับ Bitwise
        self.key_entry = ctk.CTkEntry(
            self,
            placeholder_text="Bitwise Key (Number)"
        )
        self.key_entry.pack(fill="x", padx=20, pady=5)

        # =========================
        # OUTPUT SECTION
        # =========================
        output_header = ctk.CTkFrame(self, fg_color="transparent")
        output_header.pack(fill="x", padx=20)

        ctk.CTkLabel(output_header, text="OUTPUT", font=("Arial", 12, "bold")).pack(side="left")

        self.output_label_btn = ctk.CTkButton(
            output_header,
            text="Decode • Base64",
            width=120,
            fg_color="gray"
        )
        self.output_label_btn.pack(side="left", padx=10)

        # Search Highlight
        self.search_entry = ctk.CTkEntry(
            output_header,
            placeholder_text="Search in output..."
        )
        self.search_entry.pack(side="right", padx=5)

        ctk.CTkButton(
            output_header,
            text="Find",
            width=60,
            command=self.search_output
        ).pack(side="right", padx=5)

        self.output_box = ctk.CTkTextbox(self, height=150)
        self.output_box.pack(fill="both", expand=True, padx=20, pady=(5, 20))

        self.input_box.bind("<KeyRelease>", self.process_data)

    # =========================
    # Process Main Logic
    # =========================
    def process_data(self, event=None):
        data = self.input_box.get("1.0", "end").strip()
        algo = self.algo_menu.get()

        if not data:
            self.output_box.delete("1.0", "end")
            self.current_detected_algo = None # เคลียร์ค่าที่เจอ
            self.update_output_label()
            return

        try:
            if self.mode == "Encode":
                result = encode_data(data, algo)

            elif self.mode == "Decode":
                # ⭐ แก้ไข: ถ้าเป็น Auto Detect ให้ไปเรียกฟังก์ชันหลักมาตรงๆ เพื่อเอาชื่อด้วย
                if algo == "Auto Detect":
                    from Decode.base_decoder import auto_detect_decode
                    detected_name, result = auto_detect_decode(data.encode())
                    self.current_detected_algo = detected_name # บันทึกชื่อที่หาเจอไว้
                else:
                    result = decode_data(data, algo)
                    self.current_detected_algo = algo # ถ้าไม่ได้ Auto ก็ใช้ชื่อจากเมนู

            elif self.mode == "Hash":
                result = hash_data(data, algo)

            elif self.mode == "Bitwise":
                key = self.key_entry.get()
                if not key:
                    raise ValueError("กรุณาใส่ Key")

                if algo == "XOR Mask": result = bitwise_mask(data, key, "xor")
                elif algo == "XOR Unmask": result = bitwise_unmask(data, key)
                elif algo == "OR Mask": result = bitwise_mask(data, key, "or")
                elif algo == "AND Mask": result = bitwise_mask(data, key, "and")

            self.output_box.delete("1.0", "end")
            self.output_box.insert("1.0", result)

        except Exception as e:
            self.output_box.delete("1.0", "end")
            self.output_box.insert("1.0", f"Error: {e}")

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
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            self.input_box.delete("1.0", "end")
            self.input_box.insert("1.0", content)
            self.process_data()

        except Exception as e:
            print("Read file error:", e)

    # =========================
    # Toggle Mode
    # =========================
    def toggle_mode(self):

        if self.mode == "Decode":
            self.mode = "Encode"
            self.algo_menu.configure(values=self.encode_algos)
            self.mode_btn.configure(text="Encode")
            self.algo_menu.set("Base64")

        elif self.mode == "Encode":
            self.mode = "Hash"
            self.algo_menu.configure(values=self.hash_algos)
            self.mode_btn.configure(text="Hash")
            self.algo_menu.set("sha256")

        elif self.mode == "Hash":
            self.mode = "Bitwise"
            self.algo_menu.configure(values=self.bitwise_algos)
            self.mode_btn.configure(text="Bitwise")
            self.algo_menu.set("XOR Mask")

        else:
            self.mode = "Decode"
            self.algo_menu.configure(values=self.decode_algos)
            self.mode_btn.configure(text="Decode")
            self.algo_menu.set("Auto Detect")

        self.process_data()

    # =========================
    # Update Label
    # =========================
    def update_output_label(self):
        # ⭐ แก้ไข: ให้โชว์ป้ายกำกับเท่ๆ เวลาใช้งาน Auto Detect
        if self.mode == "Decode" and self.algo_menu.get() == "Auto Detect":
            detected = getattr(self, "current_detected_algo", "Unknown")
            
            if detected == "Unknown":
                self.output_label_btn.configure(text="Auto Detect: ❓ Unknown", fg_color="#E74C3C")
            else:
                self.output_label_btn.configure(text=f"Auto Detect: 🎯 {detected}", fg_color="#2ECC71") # สีเขียวเมื่อตรวจเจอ
        else:
            self.output_label_btn.configure(text=f"{self.mode} • {self.algo_menu.get()}", fg_color="gray")