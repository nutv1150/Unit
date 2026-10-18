import customtkinter as ctk
from Tools.workspace_store import ChallengeStore, elapsed, format_elapsed, integer
from pages.workspace_ui import THEME_COLORS as T, label, dialog, CTkMessagebox, ENTRY_STYLE


class ChallengePage(ctk.CTkFrame):
    # หน้าที่: โหลด ChallengeStore และสร้างหน้าคะแนน/ตัวจับเวลา โดยแสดง error หาก config ใช้งานไม่ได้
    # ที่มา: app.py::UNITApp.__init__ (เรียกตรง)
    # Input: self (ChallengePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: parent (tkinter.Misc (widget ของ Tk/CustomTkinter)) — หน้าต่างหรือ widget ที่ผู้เรียกสร้างไว้
    # Input: storage_path (str | PathLike[str] | None) — path จากตัวเลือกไฟล์/config ที่จุดเรียกส่งมา หรือ default เมื่อไม่ระบุ
    # Input: **kwargs (dict[str, Any]) — keyword options ของ widget ที่ผู้เรียกส่งเพิ่มมา
    def __init__(self, parent, storage_path=None, **kwargs):
        super().__init__(parent, fg_color=T['bg'], **kwargs)
        self.load_error = ''
        try:
            self.store = ChallengeStore(storage_path)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self.store = None
            self.load_error = f'Could not read configuration: {exc} (original file preserved)'
        self.time_labels = {}
        self.editor = None
        self._tick_id = None
        self._build_ui()
        self._tick()

    # หน้าที่: สร้างช่องเพิ่มการแข่งขันและพื้นที่แสดงรายการ Challenge
    # ที่มา: pages/challenge.py::ChallengePage.__init__ (เรียกตรง)
    # Input: self (ChallengePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        ctk.CTkLabel(self, text='>_ CHALLENGE', font=('Consolas', 26, 'bold'), text_color=T['accent']).grid(row=0, column=0, sticky='w', padx=24, pady=24)
        form = ctk.CTkFrame(self, fg_color=T['panel'], border_width=1, border_color=T['border'])
        form.grid(row=1, column=0, sticky='ew', padx=24)
        ctk.CTkFrame(form, height=3, fg_color=T['accent']).pack(fill='x')
        label(form, '+ Add Challenge').pack(anchor='w', padx=20, pady=10)
        label(form, 'Competition name').pack(anchor='w', padx=20)
        self.name_entry = ctk.CTkEntry(form, **ENTRY_STYLE, placeholder_text='e.g. TCTT2026')
        self.name_entry.pack(fill='x', padx=20)
        self.name_error = ctk.CTkLabel(form, text='', text_color=T['error'])
        self.name_error.pack(anchor='w', padx=20)
        label(form, 'Total items (number of problems)').pack(anchor='w', padx=20)
        digits = (self.register(lambda value: value == '' or (value.isascii() and value.isdigit())), '%P')
        self.total_entry = ctk.CTkEntry(form, **ENTRY_STYLE, placeholder_text='20', validate='key', validatecommand=digits)
        self.total_entry.pack(fill='x', padx=20)
        self.total_error = ctk.CTkLabel(form, text='', text_color=T['error'])
        self.total_error.pack(anchor='w', padx=20)
        ctk.CTkButton(form, text='Create Challenge', fg_color=T['accent'], command=self._create,
                      state='disabled' if self.load_error else 'normal').pack(fill='x', padx=20, pady=(0, 16))
        self.status = ctk.CTkLabel(self, text=self.load_error or 'New timers start paused. Closing UNIT pauses all timers.', text_color=T['muted'], wraplength=700)
        self.status.grid(row=2, column=0, sticky='w', padx=24, pady=8)
        self.table = ctk.CTkScrollableFrame(self, fg_color=T['panel'])
        self.table.grid(row=3, column=0, sticky='nsew', padx=24, pady=(0, 20))
        self._render_rows()

    # หน้าที่: อ่านชื่อและจำนวนข้อจากฟอร์ม สร้าง Challenge แล้ววาดรายการใหม่
    # ที่มา: pages/challenge.py::ChallengePage._build_ui (อ้างอิง/callback)
    # Input: self (ChallengePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # อ่านภายใน: self.name_entry, self.total_entry ผ่าน .get() — str จากช่องกรอก หรือชนิดที่ Tk Variable กำหนด
    def _create(self):
        self.name_error.configure(text='' if self.name_entry.get().strip() else 'Enter a competition name')
        try:
            integer(self.total_entry.get(), 1, 'Total items')
            self.total_error.configure(text='')
        except ValueError as exc:
            self.total_error.configure(text=str(exc))
            return
        if not self.name_entry.get().strip():
            return
        try:
            self.store.create(self.name_entry.get(), self.total_entry.get())
        except (OSError, ValueError) as exc:
            self.status.configure(text=f'Could not save: {exc}', text_color=T['error'])
            return
        self.name_entry.delete(0, 'end')
        self.total_entry.delete(0, 'end')
        self._render_rows()

    # หน้าที่: สร้างแถวแสดงคะแนน เวลาสะสม สถานะ และปุ่มแก้ไข/ลบของแต่ละ Challenge
    # ที่มา: pages/challenge.py::ChallengePage._build_ui (เรียกตรง)
    # ที่มา: pages/challenge.py::ChallengePage._create (เรียกตรง)
    # ที่มา: pages/challenge.py::ChallengePage._delete.remove (เรียกตรง)
    # ที่มาเพิ่มเติม: อีก 2 จุดเรียก/อ้างอิงในโปรเจกต์
    # Input: self (ChallengePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def _render_rows(self):
        self.time_labels.clear()
        for widget in self.table.winfo_children():
            widget.destroy()
        for column, weight in enumerate((3, 2, 1, 1)):
            self.table.grid_columnconfigure(column, weight=weight)
        for column, title in enumerate(('Challenge', 'Time', 'Score', 'Actions')):
            label(self.table, title).grid(row=0, column=column, sticky='w', padx=12, pady=8)
        if not self.store or not self.store.rows:
            label(self.table, 'No challenges yet').grid(row=1, column=0, columnspan=4, pady=25)
            return
        for index, row in enumerate(self.store.rows, 1):
            record_id = row['id']
            for col, text in enumerate((row['name'], self._time_text(row), f"{row['solved_items']}/{row['total_items']}")):
                button = ctk.CTkButton(self.table, text=text, anchor='w', fg_color=T['card'], text_color=T['text'],
                                      hover_color=T['hover'], height=40, command=lambda rid=record_id: self._open_editor(rid))
                button.grid(row=index, column=col, sticky='ew', padx=3, pady=4)
                if col == 1:
                    self.time_labels[record_id] = button
            actions = ctk.CTkFrame(self.table, fg_color='transparent')
            actions.grid(row=index, column=3, padx=4)
            ctk.CTkButton(actions, text='✎', width=32, command=lambda rid=record_id: self._open_editor(rid)).pack(side='left', padx=3)
            ctk.CTkButton(actions, text='🗑', width=32, fg_color=T['error'], command=lambda rid=record_id: self._delete(rid)).pack(side='left')

    # หน้าที่: จัดข้อความเวลาสะสมของ record สำหรับแสดงบนหน้าจอ
    # ที่มา: pages/challenge.py::ChallengePage._open_editor (เรียกตรง)
    # ที่มา: pages/challenge.py::ChallengePage._render_rows (เรียกตรง)
    # ที่มา: pages/challenge.py::ChallengePage._tick (เรียกตรง)
    # ที่มาเพิ่มเติม: อีก 1 จุดเรียก/อ้างอิงในโปรเจกต์
    # Input: self (ChallengePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: row (dict[str, Any]) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def _time_text(self, row):
        return f"{format_elapsed(elapsed(row, self.store.clock()))} {'▶' if row['is_running'] else '⏸'}"

    # หน้าที่: อัปเดตป้ายเวลาของแต่ละ Challenge ตามรอบ Tk timer
    # ที่มา: pages/challenge.py::ChallengePage.__init__ (เรียกตรง)
    # Input: self (ChallengePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def _tick(self):
        if self.store:
            for row in self.store.rows:
                widget = self.time_labels.get(row['id'])
                if widget:
                    widget.configure(text=self._time_text(row))
            if self.editor and self.editor.winfo_exists():
                self.editor_time.configure(text=self._time_text(self.store.get(self.edit_id)))
        self._tick_id = self.after(1000, self._tick)

    # หน้าที่: เปิดกล่องยืนยันก่อนลบ Challenge ที่เลือก
    # ที่มา: pages/challenge.py::ChallengePage._open_editor (เรียกตรง)
    # ที่มา: pages/challenge.py::ChallengePage._render_rows (เรียกตรง)
    # Input: self (ChallengePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: record_id (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def _delete(self, record_id):
        # หน้าที่: ลบ record ที่ยืนยันแล้วออกจาก store และวาดรายการใหม่
        # ที่มา: pages/challenge.py::ChallengePage._delete (อ้างอิง/callback)
        # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
        # Closure: record_id (str) — รับจาก scope ChallengePage._delete
        # Closure: self (ChallengePage) — รับจาก scope ChallengePage._delete
        def remove():
            try:
                self.store.delete(record_id)
            except OSError as exc:
                self.status.configure(text=f'Could not delete: {exc}', text_color=T['error'])
                return
            if self.editor and self.editor.winfo_exists() and self.edit_id == record_id:
                self.editor.destroy()
            self.editor = None
            self._render_rows()
        CTkMessagebox(self, f"Delete {self.store.get(record_id)['name']}?", remove)

    # หน้าที่: เปิดฟอร์มแก้คะแนนและควบคุมการเริ่ม/หยุด timer ของ Challenge
    # ที่มา: pages/challenge.py::ChallengePage._render_rows (เรียกตรง)
    # Input: self (ChallengePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: record_id (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def _open_editor(self, record_id):
        if self.editor and self.editor.winfo_exists():
            self.editor.focus()
            return self.editor
        row = self.store.get(record_id)
        window = self.editor = dialog(self, row['name'], '460x360')
        self.edit_id = record_id
        label(window, f"Solved problems / {row['total_items']}").pack(anchor='w', padx=20, pady=(20, 8))
        solved = ctk.CTkEntry(window, **ENTRY_STYLE)
        solved.insert(0, str(row['solved_items']))
        solved.pack(fill='x', padx=20)
        error = ctk.CTkLabel(window, text='', text_color=T['error'])
        error.pack(padx=20)
        self.editor_time = label(window, self._time_text(row))
        self.editor_time.pack()
        # หน้าที่: สลับสถานะ timer และบันทึกทันทีโดยคงคะแนนเดิม; คะแนนในช่องกรอกยังไม่บันทึกจนกด Save
        # ที่มา: pages/challenge.py::ChallengePage._open_editor (อ้างอิง/callback)
        # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
        # Closure: error (ctk.CTkLabel) — รับจาก scope ChallengePage._open_editor
        # Closure: record_id (str) — รับจาก scope ChallengePage._open_editor
        # Closure: self (ChallengePage) — รับจาก scope ChallengePage._open_editor
        # Closure: toggle_button (ctk.CTkButton) — รับจาก scope ChallengePage._open_editor
        def toggle():
            current = self.store.get(record_id)
            try:
                # Timer changes persist immediately; unsaved score stays in the entry.
                self.store.update(record_id, current['solved_items'], not current['is_running'])
                toggle_button.configure(text='Pause' if self.store.get(record_id)['is_running'] else 'Start')
                self.editor_time.configure(text=self._time_text(self.store.get(record_id)))
                self._render_rows()
            except (OSError, ValueError) as exc:
                error.configure(text=str(exc))
        toggle_button = ctk.CTkButton(window, text='Pause' if row['is_running'] else 'Start', command=toggle)
        toggle_button.pack(pady=8)
        # หน้าที่: บันทึกคะแนนจากฟอร์มแก้ไขแล้วอัปเดตหน้าหลัก
        # ที่มา: pages/challenge.py::ChallengePage._open_editor (อ้างอิง/callback)
        # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
        # Closure: error (ctk.CTkLabel) — รับจาก scope ChallengePage._open_editor
        # Closure: record_id (str) — รับจาก scope ChallengePage._open_editor
        # Closure: self (ChallengePage) — รับจาก scope ChallengePage._open_editor
        # Closure: solved (ctk.CTkEntry) — รับจาก scope ChallengePage._open_editor
        # Closure: window (CTkToplevel) — รับจาก scope ChallengePage._open_editor
        def save():
            try:
                self.store.update(record_id, solved.get(), self.store.get(record_id)['is_running'])
            except (OSError, ValueError) as exc:
                error.configure(text=str(exc))
                return
            window.destroy()
            self.editor = None
            self._render_rows()
        buttons = ctk.CTkFrame(window, fg_color='transparent')
        buttons.pack(fill='x', padx=20, pady=12)
        ctk.CTkButton(buttons, text='Delete', width=100, fg_color=T['error'], command=lambda: self._delete(record_id)).pack(side='left')
        ctk.CTkButton(buttons, text='Save', width=100, command=save).pack(side='right')
        return window

    # หน้าที่: สั่งหยุด timers และบันทึกเวลาสะสมก่อนปิดแอป
    # ที่มา: app.py::UNITApp.on_close (เรียกตรง)
    # Input: self (ChallengePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def save_before_close(self):
        if self.store:
            self.store.pause_all()

    # หน้าที่: ยกเลิก Tk timer ที่ยังรออยู่แล้วทำลาย widget ของหน้า
    # ที่มา: Tk/หน้าต่างหลักเรียกเมื่อทำลาย widget
    # Input: self (ChallengePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def destroy(self):
        if self._tick_id is not None:
            self.after_cancel(self._tick_id)
            self._tick_id = None
        super().destroy()
