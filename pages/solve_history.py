"""Shared local history viewer; never executes or opens stored content."""
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk
from Tools.solve_history import export_html
from Tools.window_layout import fit_window
from Tools.text_view import background


CATEGORIES = ['All', 'Data Hashing', 'File Inspection', 'Pipeline']

class HistoryWindow(ctk.CTkToplevel):
    PAGE_SIZE = 100

    # หน้าที่: สร้างหน้าต่าง History เชื่อม store และเตรียมตัวกรอง ตาราง รายละเอียด และ timer
    # ที่มา: Tools/history_hooks.py::open_history (เรียกตรง)
    # Input: self (HistoryWindow) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: root (tkinter.Misc (widget ของ Tk/CustomTkinter)) — หน้าต่างหรือ widget ที่ผู้เรียกสร้างไว้
    # Input: category (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def __init__(self, root, category='All'):
        super().__init__(root)
        self.app_root = root
        self.store = getattr(root, 'history_store', None)
        self.title('Solve History')
        width, height = fit_window(self, '1200x800')
        self.minsize(min(850, width), min(550, height))
        self.configure(fg_color='#0D0D12')
        self.page_index = 0
        self.events = []
        self.total_events = 0
        self._exporting = False
        self.selected_ids = set()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)
        toolbar = ctk.CTkFrame(self, fg_color='transparent')
        toolbar.grid(row=0, column=0, sticky='ew', padx=16, pady=12)
        self.filter = ctk.CTkOptionMenu(toolbar, values=CATEGORIES, command=self.set_category)
        self.filter.pack(side='left', padx=(0, 8))
        for label, command in [('Refresh', self.refresh), ('Export Selected', self.export_selected),
                               ('Export All', self.export_all), ('Clear History', self.clear_history)]:
            ctk.CTkButton(toolbar, text=label, width=135, command=command).pack(side='left', padx=3)
        table_frame = ctk.CTkFrame(self, fg_color='#15151E')
        table_frame.grid(row=1, column=0, sticky='nsew', padx=16)
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        style = ttk.Style(self)
        style.configure('SolveHistory.Treeview', background='#15151E', foreground='#FFFFFF',
                        fieldbackground='#15151E', rowheight=28)
        style.map('SolveHistory.Treeview', background=[('selected', '#165A64')],
                  foreground=[('selected', '#FFFFFF')])
        style.configure('SolveHistory.Treeview.Heading', background='#1E1E2A', foreground='#00FFFF')
        self.table = ttk.Treeview(table_frame, columns=('seq', 'category', 'tool', 'status', 'group'),
                                  show='headings', selectmode='extended', style='SolveHistory.Treeview')
        for name, title, width in [('seq', '#', 55), ('category', 'Category', 130),
                                    ('tool', 'Tool / Operation', 240), ('status', 'Status', 90),
                                    ('group', 'Pipeline / Batch', 150)]:
            self.table.heading(name, text=title)
            self.table.column(name, width=width, minwidth=45)
        self.table.grid(row=0, column=0, sticky='nsew')
        scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.table.yview)
        scrollbar.grid(row=0, column=1, sticky='ns')
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.bind('<<TreeviewSelect>>', self.selection_changed)
        self.details = ctk.CTkTextbox(self, fg_color='#0A0A0F', text_color='#FFFFFF', wrap='word')
        self.details.grid(row=2, column=0, sticky='nsew', padx=16, pady=10)
        self.details.configure(state='disabled')
        footer = ctk.CTkFrame(self, fg_color='transparent')
        footer.grid(row=3, column=0, sticky='ew', padx=16, pady=(0, 12))
        ctk.CTkButton(footer, text='Previous', width=90, command=lambda: self.turn_page(-1)).pack(side='left')
        ctk.CTkButton(footer, text='Next', width=90, command=lambda: self.turn_page(1)).pack(side='left', padx=5)
        ctk.CTkButton(footer, text='Select Page', width=100,
                      command=lambda: self.table.selection_set(self.table.get_children())).pack(side='left')
        self.notice = ctk.CTkLabel(footer, text='', text_color='#8892B0', wraplength=560)
        self.notice.pack(side='left', padx=10)
        self.set_category(category)
        self._refresh_id = self.after(1000, self.tick)

    # หน้าที่: ยกเลิก timer แล้วทำลายหน้าต่าง History
    # ที่มา: Tk/หน้าต่างหลักเรียกเมื่อทำลาย widget
    # Input: self (HistoryWindow) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def destroy(self):
        if getattr(self, '_refresh_id', None):
            self.after_cancel(self._refresh_id)
        super().destroy()

    # หน้าที่: รีเฟรช History ตามรอบ timer เพื่อแสดงสถานะงานล่าสุด
    # ที่มา: pages/solve_history.py::HistoryWindow.__init__ (อ้างอิง/callback)
    # Input: self (HistoryWindow) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def tick(self):
        self.refresh()
        self._refresh_id = self.after(1000, self.tick)

    # หน้าที่: ตั้งหมวดตัวกรองและกลับไปแสดงหน้าแรกของ History
    # ที่มา: Tools/history_hooks.py::open_history (เรียกตรง)
    # ที่มา: pages/solve_history.py::HistoryWindow.__init__ (เรียกตรง)
    # ที่มา: pages/solve_history.py::HistoryWindow.__init__ (อ้างอิง/callback)
    # Input: self (HistoryWindow) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: category (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def set_category(self, category):
        self.capture_selection()
        self.filter.set(category if category in CATEGORIES else 'All')
        self.page_index = 0
        self.refresh()

    # หน้าที่: รวม selection ของหน้าที่เห็นเข้ากับชุด IDs ที่เลือกข้ามหน้า
    # ที่มา: pages/solve_history.py::HistoryWindow.set_category (เรียกตรง)
    # ที่มา: pages/solve_history.py::HistoryWindow.selection_changed (เรียกตรง)
    # ที่มา: pages/solve_history.py::HistoryWindow.refresh (เรียกตรง)
    # ที่มาเพิ่มเติม: อีก 1 จุดเรียก/อ้างอิงในโปรเจกต์
    # Input: self (HistoryWindow) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def capture_selection(self):
        visible = set(self.table.get_children())
        self.selected_ids.difference_update(visible)
        self.selected_ids.update(self.table.selection())

    # หน้าที่: เก็บ selection ใหม่และอัปเดตรายละเอียด/ข้อความสถานะ
    # ที่มา: pages/solve_history.py::HistoryWindow.__init__ (อ้างอิง/callback)
    # Input: self (HistoryWindow) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: event (tkinter.Event | None) — Tk/TkDND ส่งมาจาก event binding; บางจุดเรียกตรงโดยไม่ส่ง event
    def selection_changed(self, event=None):
        self.capture_selection()
        self.show_details()
        self.update_notice()

    # หน้าที่: แสดง error ของ History หรือจำนวน records/หน้าปัจจุบัน/จำนวนที่เลือก
    # ที่มา: pages/solve_history.py::HistoryWindow.selection_changed (เรียกตรง)
    # ที่มา: pages/solve_history.py::HistoryWindow.refresh (เรียกตรง)
    # Input: self (HistoryWindow) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def update_notice(self):
        error = getattr(self.app_root, 'history_error', '')
        if not self._exporting:
            self.notice.configure(text=error or f'{self.total_events} records · Page {self.page_index + 1} · {len(self.selected_ids)} selected · Ctrl/Shift to select')

    # หน้าที่: อ่าน records ตามหมวดและเลขหน้าแล้วอัปเดตตารางเมื่อข้อมูลเปลี่ยน
    # ที่มา: pages/solve_history.py::HistoryWindow.tick (เรียกตรง)
    # ที่มา: pages/solve_history.py::HistoryWindow.set_category (เรียกตรง)
    # ที่มา: pages/solve_history.py::HistoryWindow.turn_page (เรียกตรง)
    # ที่มาเพิ่มเติม: อีก 3 จุดเรียก/อ้างอิงในโปรเจกต์
    # Input: self (HistoryWindow) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def refresh(self):
        if self.store is None:
            self.notice.configure(text=getattr(self.app_root, 'history_error', '') or 'History unavailable')
            return
        try:
            self.total_events = self.store.count_events(self.filter.get())
            self.page_index = min(self.page_index, max(0, (self.total_events - 1) // self.PAGE_SIZE))
            events = self.store.list_events(self.filter.get(), limit=self.PAGE_SIZE,
                                           offset=self.page_index * self.PAGE_SIZE, summaries=True)
        except Exception as error:
            self.notice.configure(text=f'Cannot read history: {error}')
            return
        self.events = events
        visible = events
        self.capture_selection()
        selected = self.selected_ids
        signature = [(e['id'], e['status'], e.get('output'), e.get('error')) for e in visible]
        if signature != getattr(self, '_signature', None):
            self._signature = signature
            self.table.delete(*self.table.get_children())
            for event in visible:
                group = event.get('group_id')
                self.table.insert('', 'end', iid=event['id'], values=(event['seq'], event['category'],
                                  event['tool'], self.status_text(event), f"Run {group[:8]}" if group else ''))
            self.table.selection_set([e['id'] for e in visible if e['id'] in selected])
            self.show_details()
        self.update_notice()

    # หน้าที่: แปลงสถานะ Running ที่ไม่อยู่ในงาน active เป็น Unfinished สำหรับแสดงผล
    # ที่มา: pages/solve_history.py::HistoryWindow.show_details (เรียกตรง)
    # ที่มา: pages/solve_history.py::HistoryWindow.refresh (เรียกตรง)
    # Input: self (HistoryWindow) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: event (dict[str, Any]) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def status_text(self, event):
        if event['status'] == 'Running' and event['id'] not in getattr(self.app_root, 'history_active', set()):
            return 'Unfinished'
        return event['status']

    # หน้าที่: เลื่อนเลขหน้าตาม offset แล้วโหลดรายการใหม่
    # ที่มา: pages/solve_history.py::HistoryWindow.__init__ (เรียกตรง)
    # Input: self (HistoryWindow) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: offset (int) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def turn_page(self, offset):
        self.page_index = max(0, self.page_index + offset)
        self.refresh()

    # หน้าที่: อ่านรายละเอียดของ record ที่เลือกพร้อมข้อมูล source/run group มาแสดง
    # ที่มา: pages/solve_history.py::HistoryWindow.selection_changed (เรียกตรง)
    # ที่มา: pages/solve_history.py::HistoryWindow.refresh (เรียกตรง)
    # Input: self (HistoryWindow) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: event (tkinter.Event | None) — Tk/TkDND ส่งมาจาก event binding; บางจุดเรียกตรงโดยไม่ส่ง event
    def show_details(self, event=None):
        selected = set(self.table.selection())
        records = [e for e in self.events if e['id'] in selected]
        parts = []
        for summary in records[:1]:
            item = self.store.get_event(summary['id'])
            if item is None:
                continue
            parts.append(f"#{item['seq']} · {item['category']} · {item['tool']} · {self.status_text(item)}")
            if item.get('parent_id'):
                try:
                    parent = self.store.get_event(item['parent_id'])
                except Exception:
                    parent = None
                parts.append(f"Source: #{parent['seq']} · {parent['category']} · {parent['tool']}" if parent else
                             f"Source record unavailable: {item['parent_id']}")
            if item.get('group_id'):
                parts.append('Run group: ' + item['group_id'])
            for key in ('input', 'options', 'output', 'error', 'files'):
                value = item.get(key, '')
                parts.append(f"\n{key.upper()}\n" + ('\n'.join(value) if isinstance(value, list) else str(value)))
        self.details.configure(state='normal')
        self.details.delete('1.0', 'end')
        self.details.insert('1.0', '\n'.join(parts))
        self.details.configure(state='disabled')

    # หน้าที่: อ่าน records ที่มี ID ในชุด selection แล้วส่งออกเป็นรายงาน
    # ที่มา: pages/solve_history.py::HistoryWindow.__init__ (อ้างอิง/callback)
    # Input: self (HistoryWindow) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def export_selected(self):
        self.capture_selection()
        try:
            selected = set(self.selected_ids)
            self.export((e for e in self.store.iter_events() if e['id'] in selected), len(selected))
        except Exception as error:
            messagebox.showerror('Export History', str(error), parent=self)

    # หน้าที่: ส่ง iterator ของทุก record ในหมวดที่เลือกไปสร้างรายงาน
    # ที่มา: pages/solve_history.py::HistoryWindow.__init__ (อ้างอิง/callback)
    # Input: self (HistoryWindow) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def export_all(self):
        self.refresh()
        self.export(self.store.iter_events(self.filter.get()), self.total_events)

    # หน้าที่: เลือก destination และเริ่มเขียน HTML report เบื้องหลังโดยแสดงจำนวน records
    # ที่มา: pages/solve_history.py::HistoryWindow.export_all (เรียกตรง)
    # ที่มา: pages/solve_history.py::HistoryWindow.export_selected (เรียกตรง)
    # Input: self (HistoryWindow) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: records (Iterable[Mapping[str, Any]]) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: count (int | None) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def export(self, records, count=None):
        if self._exporting:
            return
        if count == 0 or (count is None and not records):
            messagebox.showinfo('Export History', 'No records selected.', parent=self)
            return
        path = filedialog.asksaveasfilename(parent=self, title='Export History',
                 initialfile='unit-solve-history.html', defaultextension='.html',
                 filetypes=[('HTML report', '*.html')])
        if not path:
            return
        try:
            target = Path(path).resolve()
            if target.suffix.lower() not in ('.html', '.htm'):
                raise ValueError('Choose an .html or .htm report file.')
            # Exports must not replace any referenced evidence file.
            # หน้าที่: เรียก export_html ด้วย destination และ records ที่ closure จับไว้
            # ที่มา: pages/solve_history.py::HistoryWindow.export (อ้างอิง/callback)
            # ที่มา: pages/solve_history.py::HistoryWindow.export (เรียกตรง)
            # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
            # Closure: records (Iterable[Mapping[str, Any]]) — รับจาก scope HistoryWindow.export
            # Closure: self (HistoryWindow) — รับจาก scope HistoryWindow.export
            # Closure: target (Path) — รับจาก scope HistoryWindow.export
            def write():
                for event in self.store.iter_events():
                    if any(Path(p).resolve() == target for p in event.get('files', [])):
                        raise ValueError('Choose a new report path, not a source or result file.')
                export_html(target, records)
            # หน้าที่: รับผลส่งออกจาก worker แล้วคืนปุ่มและแจ้งสำเร็จหรือ error
            # ที่มา: pages/solve_history.py::HistoryWindow.export (อ้างอิง/callback)
            # Input: _ (None (ผลของงานเขียนรายงาน; callback ไม่ใช้ค่านี้)) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
            # Input: error (Exception | None) — ผลหรือสถานะจากงานเบื้องหลังที่ผู้เรียกส่งต่อมา
            # Closure: self (HistoryWindow) — รับจาก scope HistoryWindow.export
            def finished(_, error):
                self._exporting = False
                if error:
                    messagebox.showerror('Export History', str(error), parent=self)
                else:
                    self.notice.configure(text='Export completed')
            if self.store.count_events() > 100:
                self._exporting = True
                self.notice.configure(text='Exporting in background…')
                background(self, write, finished)
            else:
                write()
                self.notice.configure(text='Export completed')
        except Exception as error:
            messagebox.showerror('Export History', str(error), parent=self)

    # หน้าที่: ขอยืนยันก่อนล้าง History ในหมวดปัจจุบันแล้วรีเฟรชตาราง
    # ที่มา: pages/solve_history.py::HistoryWindow.__init__ (อ้างอิง/callback)
    # Input: self (HistoryWindow) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def clear_history(self):
        if self.store is None:
            return
        if self._exporting:
            messagebox.showinfo('Clear History', 'Wait for the export to finish.', parent=self)
            return
        self.refresh()
        category = self.filter.get()
        active = (self.store.get_event(event_id) for event_id in getattr(self.app_root, 'history_active', set()))
        if any(e and (category == 'All' or e['category'] == category) for e in active):
            messagebox.showinfo('Clear History', 'Wait for running operations to finish.', parent=self)
            return
        scope = 'all categories' if category == 'All' else category
        if not messagebox.askyesno('Clear History',
                f'Permanently clear history for {scope}?\nSource and output files will not be deleted.', parent=self):
            return
        try:
            self.store.clear(category)
            self.table.selection_remove(self.table.selection())
            self.selected_ids = {event_id for event_id in self.selected_ids if self.store.get_event(event_id)}
            self.refresh()
        except Exception as error:
            messagebox.showerror('Clear History', str(error), parent=self)
