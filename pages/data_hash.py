import customtkinter as ctk
import threading
import tempfile
import os
from concurrent.futures import Future
from Encode.base_encoder import encode_data
from Decode.base_decoder import (
    decode_data, decode_to_bytes, custom_hex_to_hex, STANDARD_HEX_ALPHABET,
    is_probably_text,
)
from Hashing.hash_utils import hash_data
from Tools.extra_tools import (
    highlight_text,
    bitwise_mask,
    bitwise_unmask,
    detect_embedded_key,
)
from Tools.flag_detector import find_flags
from Tools.text_view import open_text_view, save_async
from Tools import history_hooks
from Tools.tool_catalog import DATA_HASH_DECODE_ALGORITHMS, DATA_HASH_BITWISE_ALGORITHMS
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

# Large text is processed off the Tk event loop.  The complete result remains
# in ``output_bytes``; only the widget preview is bounded.
LARGE_INPUT_BYTES = 16 * 1024
MAX_FILE_BYTES = 64 * 1024 * 1024
PREVIEW_CHARS = 12000


class _TempOutputPath(str):
    # หน้าที่: ลบไฟล์ output ชั่วคราวเมื่อไม่มีผู้ถือ reference ของ path แล้ว
    # ที่มา: Python เรียกผ่านวงจรชีวิตหรือ protocol ของ object
    # Input: self (_TempOutputPath) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def __del__(self):
        try:
            os.unlink(self)
        except OSError:
            pass


class _DaemonLatestExecutor:
    """One daemon worker; at most one queued (supersedable) job."""
    # หน้าที่: เตรียม condition/ช่องเก็บงานและเริ่ม daemon worker แบบรับงานล่าสุด
    # ที่มา: pages/data_hash.py::DataHashPage.__init__ (เรียกตรง)
    # Input: self (_DaemonLatestExecutor) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def __init__(self):
        self._condition = threading.Condition()
        self._pending = None
        self._pending_job = None
        self._closed = False
        self._thread = threading.Thread(target=self._run, name="data-hash", daemon=True)
        self._thread.start()

    # หน้าที่: ส่ง callable และ snapshot เข้า executor โดยแทนที่งานที่ยังไม่เริ่มด้วยงานล่าสุด
    # ที่มา: pages/data_hash.py::DataHashPage.browse_file (เรียกตรง)
    # ที่มา: pages/data_hash.py::DataHashPage.process_data (เรียกตรง)
    # Input: self (_DaemonLatestExecutor) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: function (Callable[..., Any]) — callable ที่ผู้เรียกลงทะเบียนไว้ให้เรียกต่อ
    # Input: argument (Any (argument ที่ส่งต่อให้ callable)) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def submit(self, function, argument):
        future = Future()
        with self._condition:
            if self._closed:
                future.cancel()
                return future
            if self._pending is not None:
                self._pending.cancel()
            self._pending = future
            self._pending_job = (future, function, argument)
            self._condition.notify()
        return future

    # หน้าที่: รอรับงานจากช่อง pending แล้วคำนวณผลหรือ exception ใส่ Future
    # ที่มา: pages/data_hash.py::_DaemonLatestExecutor.__init__ (อ้างอิง/callback)
    # Input: self (_DaemonLatestExecutor) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def _run(self):
        while True:
            with self._condition:
                while self._pending_job is None and not self._closed:
                    self._condition.wait()
                if self._closed and self._pending_job is None:
                    return
                future, function, argument = self._pending_job
                self._pending_job = None
                if self._pending is future:
                    self._pending = None
                if future.cancelled() or not future.set_running_or_notify_cancel():
                    continue
            try:
                future.set_result(function(argument))
            except BaseException as error:
                future.set_exception(error)
            finally:
                # Do not keep the previous large input/result while idle.
                del future, function, argument

    # หน้าที่: ปิดรับงานใหม่และยกเลิกงานที่ยังรออยู่ใน executor
    # ที่มา: pages/data_hash.py::DataHashPage.destroy (เรียกตรง)
    # Input: self (_DaemonLatestExecutor) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def shutdown(self):
        with self._condition:
            self._closed = True
            if self._pending is not None:
                self._pending.cancel()
                self._pending = None
            self._pending_job = None
            self._condition.notify_all()


class DataHashPage(ctk.CTkFrame):

    # หน้าที่: สร้างหน้า Encode/Decode/Hash/Bitwise พร้อมช่อง input/output และ executor
    # ที่มา: app.py::UNITApp.__init__ (เรียกตรง)
    # ที่มา: pages/data_hash.py::DataHashPage._compute_snapshot (อ้างอิง/callback)
    # Input: self (DataHashPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: master (tkinter.Misc (widget ของ Tk/CustomTkinter)) — หน้าต่างหรือ widget ที่ผู้เรียกสร้างไว้
    def __init__(self, master):
        super().__init__(master)
        self.app_root = master.master
        self.current_file_path = None
        self.output_bytes = b""
        self._full_output_path = None
        self._temp_outputs = set()
        self.history_source = (None, None)
        self.last_history_id = None
        self._job_generation = 0
        self._job_executor = _DaemonLatestExecutor()
        self._job_lock = threading.Lock()
        self._loading_programmatically = False
        self._file_source_text = None
        self._file_preview_text = None
        self._active_future = None
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

        self.decode_algos = list(DATA_HASH_DECODE_ALGORITHMS)

        self.hash_algos = [
            "md5", "sha1", "sha224", "sha256",
            "sha384", "sha512",
            "sha3_224", "sha3_256",
            "sha3_384", "sha3_512",
            "blake2b", "blake2s"
        ]

        # ⭐ Bitwise algorithms จาก Tools
        self.bitwise_algos = list(DATA_HASH_BITWISE_ALGORITHMS)

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
        ctk.CTkButton(header_frame, text='History', width=90,
                      command=lambda: history_hooks.open_history(self.app_root, 'Data Hashing')).pack(side='right')

        ctk.CTkLabel(
            header_frame, text=">_ DATA_FORGE :: [ENCODE / DECODE / HASH]",
            font=("Consolas", 28, "bold"), text_color=ACCENT_CYAN
        ).pack(anchor="w")

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
            self.custom_hex_panel, text="ALPHABET → 0123456789ABCDEF | Replace symbols in 0–F order",
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
        self.input_status_label = ctk.CTkLabel(input_header, text="", font=("Consolas", 10), text_color=TEXT_DIM)
        self.input_status_label.pack(side="left", padx=12)

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

        self.save_raw_button = ctk.CTkButton(
            output_header, text="[ SAVE RAW ]", width=100, height=28,
            font=("Consolas", 11, "bold"), fg_color="transparent",
            border_width=1, border_color=ALERT_AMBER, text_color=ALERT_AMBER,
            hover_color="#332600", command=self.save_raw_output,
            state="disabled",
        )
        self.save_raw_button.pack(side="right", padx=(0, 8))

        self.view_full_button = ctk.CTkButton(
            output_header, text="[ VIEW FULL ]", width=100, height=28,
            font=("Consolas", 11, "bold"), fg_color="transparent",
            border_width=1, border_color=ACCENT_GREEN, text_color=ACCENT_GREEN,
            hover_color="#003311", command=self.view_full_output, state="disabled",
        )
        self.view_full_button.pack(side="right", padx=(0, 8))

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

        self.input_box.bind("<KeyRelease>", self._input_changed)

        # ตั้งค่าเริ่มต้น: โหมด Decode + สร้างปุ่มลัดชุดแรก + ไฮไลต์ปุ่มโหมด
        self.refresh_quick_chips()
        self.update_mode_button_styles()

    # หน้าที่: ยกเลิกงาน ปิด executor และเก็บกวาดทรัพยากรก่อนทำลายหน้า
    # ที่มา: Tk/หน้าต่างหลักเรียกเมื่อทำลาย widget
    # Input: self (DataHashPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def destroy(self):
        """Stop queued work when navigating away without waiting on a huge job."""
        future = getattr(self, "_active_future", None)
        if future is not None:
            future.cancel()
        executor = getattr(self, "_job_executor", None)
        if executor is not None:
            executor.shutdown()
            self._job_executor = None
        for path in getattr(self, "_temp_outputs", set()):
            try:
                os.unlink(path)
            except OSError:
                pass
        self._temp_outputs.clear()
        super().destroy()

    # หน้าที่: เก็บข้อความที่เลือกและเปิดเมนูคลิกขวาสำหรับส่งไป Gemini
    # ที่มา: pages/data_hash.py::DataHashPage.__init__ (เรียกตรง)
    # Input: self (DataHashPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: event (tkinter.Event) — Tk/TkDND ส่งมาจาก event binding; บางจุดเรียกตรงโดยไม่ส่ง event
    # Input: textbox (CTkTextbox | tkinter.Text) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # อ่านภายใน: textbox ผ่าน .get() — str จากช่องกรอก หรือชนิดที่ Tk Variable กำหนด
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

    # หน้าที่: ส่งข้อความที่เลือกใน Data Hashing ไปยังหน้า Gemini
    # ที่มา: pages/data_hash.py::DataHashPage.__init__ (อ้างอิง/callback)
    # Input: self (DataHashPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def send_selection_to_gemini(self):
        if self.gemini_selection.strip():
            self.app_root.send_to_gemini(self.gemini_selection)

    # =========================
    # Process Main Logic
    # =========================
    # หน้าที่: ตรวจการแก้ input และเลิกใช้ full-file source เมื่อผู้ใช้แก้ข้อความบนจอ
    # ที่มา: pages/data_hash.py::DataHashPage.__init__ (อ้างอิง/callback)
    # Input: self (DataHashPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: event (tkinter.Event | None) — Tk/TkDND ส่งมาจาก event binding; บางจุดเรียกตรงโดยไม่ส่ง event
    # อ่านภายใน: self.input_box ผ่าน .get() — str จากช่องกรอก หรือชนิดที่ Tk Variable กำหนด
    def _input_changed(self, event=None):
        # A file preview is only authoritative until the user edits it.
        if not self._loading_programmatically and self._file_source_text is not None:
            visible = self.input_box.get("1.0", "end-1c")
            if visible != self._file_preview_text:
                self.input_status_label.configure(text="EDITED PREVIEW ONLY — browse again to use full file")
                self._file_source_text = None
                self._file_preview_text = None
        self.process_data(event)

    # หน้าที่: คืนข้อความต้นทางเต็มจากไฟล์หรืออ่านข้อความปัจจุบันจาก input box
    # ที่มา: pages/data_hash.py::DataHashPage.process_data (เรียกตรง)
    # Input: self (DataHashPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # อ่านภายใน: self.input_box ผ่าน .get() — str จากช่องกรอก หรือชนิดที่ Tk Variable กำหนด
    def _snapshot_source(self):
        visible = self.input_box.get("1.0", "end-1c")
        if self._file_source_text is not None and visible == self._file_preview_text:
            return self._file_source_text
        return visible

    # หน้าที่: เตรียม tuple ผลคำนวณและสร้างไฟล์ดูผลเต็มเมื่อข้อความเกิน preview
    # ที่มา: pages/data_hash.py::DataHashPage._compute_snapshot (เรียกตรง)
    # Input: output (bytes) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: result (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: algo (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: detected (str | dict[str, str] | None) — ผล auto-detect เป็น str หรือ key ของ Bitwise เป็น dict; None เมื่อไม่มีผลตรวจ
    @staticmethod
    def _worker_result(output, result, algo, detected):
        full_path = None
        if len(result) > PREVIEW_CHARS:
            handle = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False, prefix="unit-output-", suffix=".txt")
            with handle:
                if "[… binary preview truncated …]" in result:
                    handle.write(f"[BINARY HEX | {len(output)} bytes]\n")
                    for offset in range(0, len(output), 65536):
                        handle.write(output[offset:offset + 65536].hex())
                else:
                    handle.write(result)
            full_path = _TempOutputPath(handle.name)
        return output, result, algo, detected, full_path

    # หน้าที่: คำนวณ Encode/Decode/Hash/Bitwise จาก snapshot โดยไม่เข้าถึง Tk widgets
    # ที่มา: pages/data_hash.py::DataHashPage.process_data (อ้างอิง/callback)
    # ที่มา: pages/data_hash.py::DataHashPage.process_data (เรียกตรง)
    # Input: snapshot (tuple[str, str, str, dict[str, str]]) — process_data เก็บ (input, mode, algo, options) จาก UI ก่อนส่งเข้า worker
    @staticmethod
    def _compute_snapshot(snapshot):
        """Pure worker operation.  It must never touch Tk objects."""
        data, mode, algo, options = snapshot
        if algo == "ROT":
            n = int(options.get("rotation", "13").strip() or "13")
            rot_mode = "ascii" if options.get("alphabet", "").startswith("ascii") else "alpha"
            algo = f"ROT:{n}:{rot_mode}"
        if mode == "Encode":
            output = encode_data(data, algo).encode("utf-8")
            return DataHashPage._worker_result(output, output.decode("utf-8"), algo, None)
        if mode == "Decode":
            if algo == "Hex":
                alphabet = options.get("hex_alphabet")
                output = decode_to_bytes(data, algo, alphabet=alphabet)
                result = output.decode("utf-8") if is_probably_text(output) else f"[BINARY HEX | {len(output)} bytes]\n{output[:65536].hex()}" + ("\n[… binary preview truncated …]" if len(output) > 65536 else "")
                return DataHashPage._worker_result(output, result, algo, None)
            if algo == "Auto Detect":
                from Decode.base_decoder import auto_detect_decode
                detected, result = auto_detect_decode(data.encode())
                output = result.encode("utf-8")
                return DataHashPage._worker_result(output, result, algo, detected)
            output = decode_to_bytes(data, algo)
            result = output.decode("utf-8") if is_probably_text(output) else f"[BINARY HEX | {len(output)} bytes]\n{output[:65536].hex()}" + ("\n[… binary preview truncated …]" if len(output) > 65536 else "")
            return DataHashPage._worker_result(output, result, algo, None)
        if mode == "Hash":
            result = hash_data(data, algo)
            output = result.encode("utf-8")
            return DataHashPage._worker_result(output, result, algo, None)
        key = options.get("key", "").strip()
        if not key:
            detected_key = detect_embedded_key(data)
            if detected_key:
                key = detected_key["key"]
            else:
                raise ValueError("Enter a key or paste data containing a key, e.g. $key = 0x4A")
        if algo == "XOR Mask": result = bitwise_mask(data, key, "xor")
        elif algo == "XOR Unmask": result = bitwise_unmask(data, key)
        elif algo == "OR Mask": result = bitwise_mask(data, key, "or")
        elif algo == "AND Mask": result = bitwise_mask(data, key, "and")
        output = result.encode("utf-8") if isinstance(result, str) else bytes(result)
        return DataHashPage._worker_result(output, result, algo, {"key": key})

    # หน้าที่: แสดงผลของ generation ปัจจุบันและบันทึก History/กิจกรรม
    # ที่มา: pages/data_hash.py::DataHashPage._job_done (เรียกตรง)
    # ที่มา: pages/data_hash.py::DataHashPage.process_data (เรียกตรง)
    # Input: self (DataHashPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: output_bytes (bytes) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: result (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: algo (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: detected (str | dict[str, str] | None) — ผล auto-detect เป็น str หรือ key ของ Bitwise เป็น dict; None เมื่อไม่มีผลตรวจ
    # Input: full_path (str | None) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: history_id (str | None) — ID ที่ history_hooks.begin คืนให้เมื่อเริ่มงาน; None เมื่อ History ใช้งานไม่ได้
    # Input: data (str) — ข้อความต้นทางจาก _snapshot_source ที่ส่งต่อพร้อมงาน
    # Input: generation (int) — หมายเลข _job_generation ที่ใช้ข้ามผลของงานเก่า
    # อ่านภายใน: self.key_entry ผ่าน .get() — str จากช่องกรอก หรือชนิดที่ Tk Variable กำหนด
    def _show_result(self, output_bytes, result, algo, detected, full_path, history_id, data, generation):
        if generation != self._job_generation:
            return
        self.output_bytes = output_bytes
        self.current_detected_algo = detected or (algo if self.mode == "Decode" and algo != "Auto Detect" else None)
        if self.mode == "Bitwise" and isinstance(detected, dict) and not self.key_entry.get().strip():
            self.key_entry.insert(0, detected["key"])
        display = result if len(result) <= PREVIEW_CHARS else result[:PREVIEW_CHARS] + f"\n[… preview truncated; {len(result):,} characters total …]"
        # Viewers retain their own reference; unused old temporary output can go.
        self._temp_outputs.clear()
        self._full_output_path = full_path
        if full_path:
            self._temp_outputs.add(full_path)
        self.output_box.delete("1.0", "end")
        self.output_box.insert("1.0", display)
        self.save_raw_button.configure(state="normal" if output_bytes else "disabled")
        self.view_full_button.configure(state="normal" if full_path else "disabled")
        history_hooks.finish(self.app_root, history_id, 'Success', output_data=output_bytes)
        # Activity reporting is deliberately bounded too; scanning a massive
        # generated output on the Tk thread would defeat the responsiveness
        # guarantee.  Save Raw still retains the complete bytes above.
        self._record_activity(tool=f"{self.mode}: {algo}", action=self.mode, status="success", flags=find_flags(result[:PREVIEW_CHARS]), details=f"Input length: {len(data)} characters")
        self.update_output_label()

    # หน้าที่: รับผลหรือ exception จาก Future และแสดงเฉพาะงานที่ยังตรงกับ generation
    # ที่มา: pages/data_hash.py::DataHashPage.process_data (เรียกตรง)
    # Input: self (DataHashPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: future (concurrent.futures.Future) — ผลหรือสถานะจากงานเบื้องหลังที่ผู้เรียกส่งต่อมา
    # Input: generation (int) — หมายเลข _job_generation ที่ใช้ข้ามผลของงานเก่า
    # Input: history_id (str | None) — ID ที่ history_hooks.begin คืนให้เมื่อเริ่มงาน; None เมื่อ History ใช้งานไม่ได้
    # Input: data (str) — ข้อความต้นทางจาก _snapshot_source ที่ส่งต่อพร้อมงาน
    def _job_done(self, future, generation, history_id, data):
        if getattr(self, '_active_future', None) is future:
            self._active_future = None
        if generation != self._job_generation:
            history_hooks.finish(self.app_root, history_id, 'Failed', error='Superseded by newer input')
            return
        try:
            output, result, algo, detected, full_path = future.result()
        except Exception as exc:
            history_hooks.finish(self.app_root, history_id, 'Failed', error=str(exc))
            self.output_bytes = b""
            self.save_raw_button.configure(state="disabled")
            self.output_box.delete("1.0", "end")
            self.output_box.insert("1.0", f"Error: {exc}")
            self._record_activity(tool=f"{self.mode}: {self.algo_menu.get()}", action=self.mode, status="failed", details=str(exc))
            self.update_output_label()
            return
        self._show_result(output, result, algo, detected, full_path, history_id, data, generation)

    # หน้าที่: ตรวจ Future ตามรอบ Tk timer แล้วเรียก completion callback บน UI thread
    # ที่มา: pages/data_hash.py::DataHashPage.browse_file (อ้างอิง/callback)
    # ที่มา: pages/data_hash.py::DataHashPage.process_data (อ้างอิง/callback)
    # Input: self (DataHashPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: future (concurrent.futures.Future) — ผลหรือสถานะจากงานเบื้องหลังที่ผู้เรียกส่งต่อมา
    # Input: callback (Callable[[concurrent.futures.Future], None]) — callable ที่ผู้เรียกลงทะเบียนไว้ให้เรียกต่อ
    def _poll_future(self, future, callback):
        """Poll completion from Tk; worker threads never call Tk APIs."""
        if future.done():
            callback(future)
        else:
            self.after(20, self._poll_future, future, callback)

    # หน้าที่: อ่าน input/algorithm/options เป็น snapshot แล้วคำนวณทันทีหรือส่งเข้า worker
    # ที่มา: Tools/package_smoke.py::main (เรียกตรง)
    # ที่มา: app.py::UNITApp.send_to_hashing (เรียกตรง)
    # ที่มา: pages/data_hash.py::DataHashPage.__init__ (อ้างอิง/callback)
    # ที่มาเพิ่มเติม: อีก 4 จุดเรียก/อ้างอิงในโปรเจกต์
    # Input: self (DataHashPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: event (tkinter.Event | None) — Tk/TkDND ส่งมาจาก event binding; บางจุดเรียกตรงโดยไม่ส่ง event
    # อ่านภายใน: self.rot_entry, self.rot_mode_var, self.custom_hex_entry, self.key_entry ผ่าน .get() — str จากช่องกรอก หรือชนิดที่ Tk Variable กำหนด
    def process_data(self, event=None):
        if getattr(self, '_file_loading', False):
            return
        # Tk's `end` includes the implicit trailing newline.  Remove only
        # that sentinel; user whitespace is meaningful for hashes/encodings.
        data = self._snapshot_source()
        algo = self.algo_menu.get()

        with self._job_lock:
            self._job_generation += 1
            generation = self._job_generation

        self.custom_hex_preview.configure(text="HEX PREVIEW: —")

        if not data:
            self.output_bytes = b""
            self._full_output_path = None
            self.save_raw_button.configure(state="disabled")
            self.view_full_button.configure(state="disabled")
            self.output_box.delete("1.0", "end")
            self.current_detected_algo = None # เคลียร์ค่าที่เจอ
            self.update_output_label()
            return

        options = {'mode': self.mode, 'algorithm': algo}
        if algo == 'ROT':
            options.update(rotation=self.rot_entry.get(), alphabet=self.rot_mode_var.get())
        if algo == 'Hex' and self.mode == 'Decode':
            options['hex_alphabet'] = self.custom_hex_entry.get()
            try:
                preview = custom_hex_to_hex(data[:160], self.custom_hex_entry.get())
                preview = preview[:80] + ("…" if len(preview) > 80 else "")
                self.custom_hex_preview.configure(text=f"HEX PREVIEW: {preview}")
            except ValueError:
                self.custom_hex_preview.configure(text="HEX PREVIEW: invalid alphabet/input")
        if self.mode == 'Bitwise':
            options['key'] = self.key_entry.get()
        source_text, source_id = self.history_source
        history_input = data
        if len(data) >= LARGE_INPUT_BYTES:
            history_input = data[:PREVIEW_CHARS] + f"\n[… input preview truncated; {len(data):,} characters total …]"
        history_id = history_hooks.begin(
            self.app_root, category='Data Hashing', tool=f'{self.mode}: {algo}',
            input_data=history_input, options=options, parent_id=source_id if data == source_text else None,
            files=[self.current_file_path] if self.current_file_path else [],
        )
        self.last_history_id = history_id
        options_snapshot = dict(options)
        snapshot = (data, self.mode, algo, options_snapshot)
        if len(data) >= LARGE_INPUT_BYTES:
            self.output_bytes = b""
            self._full_output_path = None
            self.save_raw_button.configure(state="disabled")
            self.view_full_button.configure(state="disabled")
            self.output_box.delete("1.0", "end")
            self.output_box.insert("1.0", "Processing large input in background…")
            if self._active_future is not None:
                self._active_future.cancel()
            future = self._job_executor.submit(self._compute_snapshot, snapshot)
            self._active_future = future
            self.after(20, self._poll_future, future,
                       lambda f: self._job_done(f, generation, history_id, data))
            return
        try:
            output, result, resolved_algo, detected, full_path = self._compute_snapshot(snapshot)
            self._show_result(output, result, resolved_algo, detected, full_path, history_id, data, generation)
        except Exception as e:
            history_hooks.finish(self.app_root, history_id, 'Failed', error=str(e))
            self.output_bytes = b""
            self._full_output_path = None
            self.save_raw_button.configure(state="disabled")
            self.view_full_button.configure(state="disabled")
            self.output_box.delete("1.0", "end")
            self.output_box.insert("1.0", f"Error: {e}")
            self._record_activity(
                tool=f"{self.mode}: {algo}",
                action=self.mode,
                status="failed",
                details=str(e),
            )

        self.update_output_label()

    # หน้าที่: เลือก destination แล้วบันทึก output bytes ฉบับเต็ม
    # ที่มา: pages/data_hash.py::DataHashPage.__init__ (อ้างอิง/callback)
    # Input: self (DataHashPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def save_raw_output(self):
        """Save the exact decoded/output bytes, without text re-encoding."""
        if not self.output_bytes:
            return
        path = filedialog.asksaveasfilename(
            title="Save raw output", defaultextension=".bin",
            filetypes=[("Binary files", "*.bin"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            if len(self.output_bytes) >= LARGE_INPUT_BYTES:
                event_id = self.last_history_id
                save_async(self, self.output_bytes, path,
                           lambda: history_hooks.attach_file(self.app_root, event_id, path))
                return
            with open(path, "wb") as handle:
                handle.write(self.output_bytes)
            history_hooks.attach_file(self.app_root, self.last_history_id, path)
        except OSError as exc:
            self.output_box.insert("end", f"\nError saving raw output: {exc}")

    # หน้าที่: เปิด viewer สำหรับไฟล์ output เต็มที่ยาวเกิน preview
    # ที่มา: pages/data_hash.py::DataHashPage.__init__ (อ้างอิง/callback)
    # Input: self (DataHashPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def view_full_output(self):
        path = getattr(self, "_full_output_path", None)
        if path:
            open_text_view(self, path)

    # =========================
    # Highlight Output
    # =========================
    # หน้าที่: อ่านคำค้นแล้วไฮไลต์ข้อความที่ตรงใน output box
    # ที่มา: pages/data_hash.py::DataHashPage.__init__ (อ้างอิง/callback)
    # Input: self (DataHashPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # อ่านภายใน: self.search_entry ผ่าน .get() — str จากช่องกรอก หรือชนิดที่ Tk Variable กำหนด
    def search_output(self):
        highlight_text(self.output_box, self.search_entry.get())

    # =========================
    # Browse File
    # =========================
    # หน้าที่: เลือกไฟล์ ตรวจขนาด และเริ่มอ่าน UTF-8 เบื้องหลัง
    # ที่มา: pages/data_hash.py::DataHashPage.__init__ (อ้างอิง/callback)
    # Input: self (DataHashPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def browse_file(self):

        file_path = filedialog.askopenfilename(
            filetypes=[("Text Files", "*.txt *.json *.log *.py *.md"), ("All Files", "*.*")]
        )

        if not file_path:
            return

        self.current_file_path = file_path
        self._file_loading = True
        self.output_bytes = b""
        self._full_output_path = None
        self.save_raw_button.configure(state="disabled")
        self.view_full_button.configure(state="disabled")
        self.output_box.delete("1.0", "end")
        with self._job_lock:
            self._job_generation += 1
            load_generation = self._job_generation
        self.input_box.delete("1.0", "end")
        self.input_box.insert("1.0", "Loading file…")
        self.input_box.configure(state='disabled')
        self._file_source_text = None
        self._file_preview_text = None

        # หน้าที่: อ่านไฟล์ที่เลือกเป็น UTF-8 โดยตรวจเพดานขนาด input
        # ที่มา: pages/data_hash.py::DataHashPage.browse_file (เรียกตรง)
        # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
        # Closure: file_path (str) — รับจาก scope DataHashPage.browse_file
        def read_file():
            with open(file_path, "rb") as handle:
                raw = handle.read(MAX_FILE_BYTES + 1)
            if len(raw) > MAX_FILE_BYTES:
                raise ValueError(f"File exceeds the 64 MiB Data Hashing limit ({MAX_FILE_BYTES:,} bytes)")
            return raw.decode("utf-8")

        # หน้าที่: รับผลอ่านไฟล์จาก Future ตรวจ generation และเตรียมนำข้อมูลเข้า UI
        # ที่มา: pages/data_hash.py::DataHashPage.browse_file (อ้างอิง/callback)
        # Input: future (concurrent.futures.Future) — ผลหรือสถานะจากงานเบื้องหลังที่ผู้เรียกส่งต่อมา
        # Closure: load_generation (int) — รับจาก scope DataHashPage.browse_file
        # Closure: self (DataHashPage) — รับจาก scope DataHashPage.browse_file
        def loaded(future):
            if load_generation != self._job_generation:
                return
            self._file_loading = False
            self.input_box.configure(state='normal')
            try:
                content = future.result()
            except (OSError, UnicodeError, ValueError) as exc:
                self.input_box.delete("1.0", "end")
                self.input_status_label.configure(text="FILE NOT LOADED")
                self.output_box.insert("end", f"Error reading file: {exc}")
                return
            # หน้าที่: ติดตั้ง full-file source และ preview ลงหน้าจอแล้วเริ่มประมวลผล
            # ที่มา: pages/data_hash.py::DataHashPage.browse_file.loaded (เรียกตรง)
            # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
            # Closure: content (str) — รับจาก scope DataHashPage.browse_file.loaded
            # Closure: load_generation (int) — รับจาก scope DataHashPage.browse_file
            # Closure: self (DataHashPage) — รับจาก scope DataHashPage.browse_file
            def install():
                if load_generation != self._job_generation:
                    return
                self._file_source_text = content
                self._file_preview_text = content if len(content.encode("utf-8")) <= LARGE_INPUT_BYTES else content[:PREVIEW_CHARS]
                self._loading_programmatically = True
                try:
                    self.input_box.delete("1.0", "end")
                    self.input_box.insert("1.0", self._file_preview_text)
                finally:
                    self._loading_programmatically = False
                self.input_status_label.configure(
                    text=(f"FULL FILE ACTIVE ({len(content):,} chars)" if self._file_preview_text != content
                          else "FILE LOADED")
                )
                self.process_data()
            install()
        future = self._job_executor.submit(lambda _: read_file(), None)
        self.after(20, self._poll_future, future, loaded)

    # หน้าที่: ส่งเหตุการณ์แปลงข้อมูลไป Dashboard พร้อม path และ flags ที่พบ
    # ที่มา: pages/data_hash.py::DataHashPage._show_result (เรียกตรง)
    # ที่มา: pages/data_hash.py::DataHashPage._job_done (เรียกตรง)
    # ที่มา: pages/data_hash.py::DataHashPage.process_data (เรียกตรง)
    # Input: self (DataHashPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: tool (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: action (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: status (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: flags (list[str] | None) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: details (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
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
    # หน้าที่: เปลี่ยนโหมดพร้อมค่า dropdown และช่องกรอกเฉพาะโหมด
    # ที่มา: Tools/package_smoke.py::main (เรียกตรง)
    # ที่มา: app.py::UNITApp.navigate_to (เรียกตรง)
    # ที่มา: pages/data_hash.py::DataHashPage.__init__ (เรียกตรง)
    # Input: self (DataHashPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: name (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
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

    # หน้าที่: ปรับสีปุ่มให้ตรงกับโหมดที่ใช้งานอยู่
    # ที่มา: pages/data_hash.py::DataHashPage.__init__ (เรียกตรง)
    # ที่มา: pages/data_hash.py::DataHashPage.set_mode (เรียกตรง)
    # Input: self (DataHashPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
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
    # หน้าที่: สร้างปุ่มอัลกอริทึมด่วนตามโหมดปัจจุบัน
    # ที่มา: pages/data_hash.py::DataHashPage.__init__ (เรียกตรง)
    # ที่มา: pages/data_hash.py::DataHashPage.set_mode (เรียกตรง)
    # Input: self (DataHashPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
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

    # หน้าที่: ไฮไลต์ปุ่มอัลกอริทึมด่วนที่ตรงกับ dropdown
    # ที่มา: pages/data_hash.py::DataHashPage.refresh_quick_chips (เรียกตรง)
    # ที่มา: pages/data_hash.py::DataHashPage.on_algo_selected (เรียกตรง)
    # Input: self (DataHashPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def refresh_quick_chip_styles(self):
        current = self.algo_menu.get()
        for btn in self.quick_buttons:
            if btn.cget("text") == current:
                btn.configure(fg_color=ACCENT_GREEN, text_color="black", hover_color="#00CC33")
            else:
                btn.configure(fg_color="transparent", text_color=TEXT_DIM, hover_color="#2B2B36",
                               border_width=1, border_color=BORDER_DIM)

    # หน้าที่: ตั้ง dropdown เป็นอัลกอริทึมที่เลือกแล้วอัปเดตผล
    # ที่มา: app.py::UNITApp.navigate_to (เรียกตรง)
    # ที่มา: pages/data_hash.py::DataHashPage.refresh_quick_chips (เรียกตรง)
    # Input: self (DataHashPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: algo (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def select_quick_algo(self, algo):
        self.algo_menu.set(algo)
        self.on_algo_selected()

    # หน้าที่: ปรับช่อง options และคำนวณผลเมื่อเลือกอัลกอริทึมใหม่
    # ที่มา: pages/data_hash.py::DataHashPage.set_mode (เรียกตรง)
    # ที่มา: pages/data_hash.py::DataHashPage.select_quick_algo (เรียกตรง)
    # ที่มา: pages/data_hash.py::DataHashPage.__init__ (เรียกตรง)
    # Input: self (DataHashPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
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
    # หน้าที่: ปรับหัวข้อ output ตามโหมดและอัลกอริทึมที่ตรวจพบ
    # ที่มา: pages/data_hash.py::DataHashPage._show_result (เรียกตรง)
    # ที่มา: pages/data_hash.py::DataHashPage.process_data (เรียกตรง)
    # ที่มา: pages/data_hash.py::DataHashPage._job_done (เรียกตรง)
    # Input: self (DataHashPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
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
