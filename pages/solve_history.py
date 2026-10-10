"""Shared local history viewer; never executes or opens stored content."""
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk
from Tools.solve_history import export_html


CATEGORIES = ['All', 'Data Hashing', 'File Inspection', 'Pipeline']

class HistoryWindow(ctk.CTkToplevel):
    PAGE_SIZE = 100

    def __init__(self, root, category='All'):
        super().__init__(root)
        self.app_root = root
        self.store = getattr(root, 'history_store', None)
        self.title('Solve History')
        self.geometry('1050x700')
        self.minsize(850, 550)
        self.configure(fg_color='#0D0D12')
        self.page_index = 0
        self.events = []
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

    def destroy(self):
        if getattr(self, '_refresh_id', None):
            self.after_cancel(self._refresh_id)
        super().destroy()

    def tick(self):
        self.refresh()
        self._refresh_id = self.after(1000, self.tick)

    def set_category(self, category):
        self.capture_selection()
        self.filter.set(category if category in CATEGORIES else 'All')
        self.page_index = 0
        self.refresh()

    def capture_selection(self):
        visible = set(self.table.get_children())
        self.selected_ids.difference_update(visible)
        self.selected_ids.update(self.table.selection())

    def selection_changed(self, event=None):
        self.capture_selection()
        self.show_details()
        self.update_notice()

    def update_notice(self):
        error = getattr(self.app_root, 'history_error', '')
        self.notice.configure(text=error or f'{len(self.events)} records · Page {self.page_index + 1} · {len(self.selected_ids)} selected · Ctrl/Shift to select')

    def refresh(self):
        if self.store is None:
            self.notice.configure(text=getattr(self.app_root, 'history_error', '') or 'History unavailable')
            return
        try:
            events = self.store.list_events(self.filter.get())
        except Exception as error:
            self.notice.configure(text=f'Cannot read history: {error}')
            return
        self.events = events
        self.page_index = min(self.page_index, max(0, (len(events) - 1) // self.PAGE_SIZE))
        visible = events[self.page_index * self.PAGE_SIZE:(self.page_index + 1) * self.PAGE_SIZE]
        self.capture_selection()
        selected = self.selected_ids
        signature = [(e['id'], e['status'], e.get('output'), e.get('error')) for e in visible]
        if signature != getattr(self, '_signature', None):
            self._signature = signature
            self.table.delete(*self.table.get_children())
            groups = {}
            for event in events:
                if event.get('group_id'):
                    groups.setdefault(event['group_id'], event['seq'])
            for event in visible:
                group = event.get('group_id')
                self.table.insert('', 'end', iid=event['id'], values=(event['seq'], event['category'],
                                  event['tool'], self.status_text(event), f"Run #{groups[group]}" if group else ''))
            self.table.selection_set([e['id'] for e in visible if e['id'] in selected])
            self.show_details()
        self.update_notice()

    def status_text(self, event):
        if event['status'] == 'Running' and event['id'] not in getattr(self.app_root, 'history_active', set()):
            return 'Unfinished'
        return event['status']

    def turn_page(self, offset):
        self.page_index = max(0, self.page_index + offset)
        self.refresh()

    def show_details(self, event=None):
        selected = set(self.table.selection())
        records = [e for e in self.events if e['id'] in selected]
        parts = []
        for item in records[:1]:
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

    def export_selected(self):
        self.capture_selection()
        try:
            self.export([e for e in self.store.list_events() if e['id'] in self.selected_ids])
        except Exception as error:
            messagebox.showerror('Export History', str(error), parent=self)

    def export_all(self):
        self.refresh()
        self.export(self.events)

    def export(self, records):
        if not records:
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
            protected = {str(Path(p).resolve()) for e in self.store.list_events() for p in e.get('files', [])}
            if str(target) in protected:
                raise ValueError('Choose a new report path, not a source or result file.')
            export_html(target, records)
            self.notice.configure(text=f'Exported {len(records)} records')
        except Exception as error:
            messagebox.showerror('Export History', str(error), parent=self)

    def clear_history(self):
        if self.store is None:
            return
        self.refresh()
        category = self.filter.get()
        if any(e['id'] in getattr(self.app_root, 'history_active', set()) for e in self.events):
            messagebox.showinfo('Clear History', 'Wait for running operations to finish.', parent=self)
            return
        scope = 'all categories' if category == 'All' else category
        if not messagebox.askyesno('Clear History',
                f'Permanently clear history for {scope}?\nSource and output files will not be deleted.', parent=self):
            return
        try:
            self.store.clear(category)
            self.table.selection_remove(self.table.selection())
            self.selected_ids.intersection_update(e['id'] for e in self.store.list_events())
            self.refresh()
        except Exception as error:
            messagebox.showerror('Clear History', str(error), parent=self)
