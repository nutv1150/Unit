import customtkinter as ctk
from Tools.workspace_store import CONFIG_DIR, load_records, save_records, make_group
from pages.workspace_ui import THEME_COLORS as T, COLORS, FONT, label, dialog, CTkMessagebox, ENTRY_STYLE

TOOL_OPTIONS = [
    {'name': 'Base64 decode', 'page': 'Data Hashing', 'sub': 'Base64', 'color': 'blue'},
    {'name': 'ROT decode', 'page': 'Data Hashing', 'sub': 'ROT', 'color': 'blue'},
    {'name': 'Hex decode', 'page': 'Data Hashing', 'sub': 'Hex', 'color': 'blue'},
    {'name': 'XOR bitwise', 'page': 'Data Hashing', 'sub': 'XOR', 'color': 'blue'},
    {'name': 'File Inspection', 'page': 'File Inspection', 'sub': None, 'color': 'green'},
    {'name': 'zsteg', 'page': 'File Inspection', 'sub': 'zsteg Analysis', 'color': 'green'},
    {'name': 'Pipeline', 'page': 'Pipeline', 'sub': None, 'color': 'purple'},
    {'name': 'Wireshark', 'page': 'App Portal', 'sub': 'Wireshark', 'color': 'amber'},
    {'name': 'Burp Suite', 'page': 'App Portal', 'sub': 'Burp Suite', 'color': 'amber'},
]


class MyToolsPage(ctk.CTkFrame):
    def __init__(self, parent, navigate_callback, storage_path=None, **kwargs):
        super().__init__(parent, fg_color=T['bg'], **kwargs)
        self.navigate = navigate_callback
        self.path = storage_path if storage_path is not None else CONFIG_DIR / 'my_tools_groups.json'
        self.columns = 2
        self.load_error = ''
        try:
            self.groups = load_records(self.path)
            for group in self.groups:
                make_group(group['name'], group['tools'], group['id'])
                for tool in group['tools']:
                    if not isinstance(tool.get('name'), str) or not isinstance(tool.get('page'), str):
                        raise ValueError('Invalid tool in config')
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            self.groups = []
            self.load_error = f'อ่าน config ไม่สำเร็จ: {exc} (ไฟล์เดิมไม่ถูกเขียนทับ)'
        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.grid(row=0, column=0, sticky='ew', padx=24, pady=(24, 12))
        header.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(header, text='>_ MY TOOLS', font=('Consolas', 26, 'bold'), text_color=T['accent']).grid(row=0, column=0, padx=(0, 20))
        self.search = ctk.StringVar()
        search_entry = ctk.CTkEntry(header, **ENTRY_STYLE, placeholder_text='Search groups...')
        search_entry.grid(row=0, column=1, sticky='ew', padx=12)
        search_entry.bind('<KeyRelease>', lambda _: self.search.set(search_entry.get()), add='+')
        ctk.CTkButton(header, text='+ New group', width=120, command=self._open_dialog,
                      state='disabled' if self.load_error else 'normal').grid(row=0, column=2)
        self.status = ctk.CTkLabel(self, text=self.load_error, text_color=T['error'], wraplength=700)
        self.status.grid(row=1, column=0, sticky='w', padx=24)
        self.cards = ctk.CTkScrollableFrame(self, fg_color='transparent')
        self.cards.grid(row=2, column=0, sticky='nsew', padx=16, pady=(0, 20))
        self.search.trace_add('write', lambda *_: self._render_cards())
        self.cards.bind('<Configure>', self._resize, add='+')
        self._render_cards()

    def _resize(self, event):
        columns = 3 if event.width >= 1080 else 2 if event.width >= 620 else 1
        if columns != self.columns:
            self.columns = columns
            self._render_cards()

    def _render_cards(self):
        for widget in self.cards.winfo_children():
            widget.destroy()
        for col in range(3):
            self.cards.grid_columnconfigure(col, weight=1 if col < self.columns else 0, uniform='cards' if col < self.columns else '')
        groups = [g for g in self.groups if self.search.get().strip().casefold() in g['name'].casefold()]
        if not groups:
            label(self.cards, 'No groups found').grid(row=0, column=0, columnspan=self.columns, pady=60)
            return
        height = max(220, 115 + max(len(g['tools']) for g in groups) * 42)
        for i, group in enumerate(groups):
            card = self._build_card(self.cards, group, height)
            card.grid(row=i // self.columns, column=i % self.columns, padx=8, pady=8, sticky='nsew')

    def _build_card(self, parent, group, height):
        accent = COLORS.get(group.get('category_color'), COLORS['purple'])
        card = ctk.CTkFrame(parent, fg_color=T['panel'], border_width=1, border_color=T['border'], corner_radius=12, height=height)
        card.grid_propagate(False)
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(2, weight=1)
        header = ctk.CTkFrame(card, fg_color='transparent')
        header.grid(row=0, column=0, sticky='ew', padx=12, pady=(12, 4))
        header.grid_columnconfigure(0, weight=1)
        name = ctk.CTkLabel(header, text=f"● {group['name']}", text_color=accent, font=('Consolas', 14, 'bold'), anchor='w', wraplength=170)
        name.grid(row=0, column=0, sticky='ew')
        label(header, str(len(group['tools'])), width=26, fg_color=T['card'], corner_radius=8).grid(row=0, column=1, padx=4)
        ctk.CTkButton(header, text='✎', width=28, command=lambda: self._open_dialog(group)).grid(row=0, column=2, padx=2)
        ctk.CTkButton(header, text='🗑', width=28, fg_color=T['error'], command=lambda: self._delete(group)).grid(row=0, column=3, padx=2)
        pages = list(dict.fromkeys(t['page'] for t in group['tools']))
        tags = ' / '.join({'Data Hashing': 'Decode', 'File Inspection': 'Inspect'}.get(p, p) for p in pages)
        label(card, tags, fg_color=T['card'], corner_radius=6, wraplength=250).grid(row=1, column=0, sticky='w', padx=14, pady=(0, 8))
        body = ctk.CTkFrame(card, fg_color='transparent')
        body.grid(row=2, column=0, sticky='nsew', padx=12, pady=(0, 12))
        for tool in group['tools']:
            self._build_chip(body, tool)
        return card

    def _build_chip(self, parent, tool):
        accent = COLORS.get(tool.get('color'), COLORS['purple'])
        text = f"● {tool['name']}"
        chip = ctk.CTkButton(parent, text=text, height=34, anchor='w', font=FONT,
                            fg_color='transparent', text_color=accent, border_width=1,
                            border_color=T['border'], hover_color=T['hover'],
                            command=lambda: self.navigate(tool['page'], tool.get('sub')))
        chip.pack(fill='x', pady=4)
        chip.bind('<Enter>', lambda _: chip.configure(text=text+'  →', border_color=accent), add='+')
        chip.bind('<Leave>', lambda _: chip.configure(text=text, border_color=T['border']), add='+')
        return chip

    def _commit(self, groups):
        if self.load_error:
            return False
        try:
            save_records(self.path, groups)
        except (OSError, ValueError) as exc:
            self.status.configure(text=f'บันทึกไม่สำเร็จ: {exc}')
            return False
        self.groups = groups
        self.status.configure(text='')
        self._render_cards()
        return True

    def _delete(self, group):
        CTkMessagebox(self, f"ลบกลุ่ม {group['name']}?", lambda: self._commit([g for g in self.groups if g['id'] != group['id']]))

    def _open_dialog(self, group=None):
        window = dialog(self, 'Edit group' if group else 'Create a new group')
        label(window, 'Group name').pack(anchor='w', padx=20, pady=(20, 4))
        name = ctk.CTkEntry(window, **ENTRY_STYLE, placeholder_text='e.g. CTF starter kit')
        name.pack(fill='x', padx=20)
        if group:
            name.insert(0, group['name'])
        name_error = ctk.CTkLabel(window, text='', text_color=T['error'])
        name_error.pack(anchor='w', padx=20)
        label(window, 'Select tools').pack(anchor='w', padx=20)
        tools_frame = ctk.CTkScrollableFrame(window, fg_color=T['panel'])
        tools_frame.pack(fill='both', expand=True, padx=20, pady=8)
        options = list(TOOL_OPTIONS)
        selected = {(t['page'], t.get('sub')) for t in group['tools']} if group else set()
        # รักษา custom tool ที่มีในไฟล์เดิม แม้ไม่อยู่ในรายการเริ่มต้น
        for tool in group['tools'] if group else []:
            if (tool['page'], tool.get('sub')) not in {(t['page'], t.get('sub')) for t in options}:
                options.append(tool)
        choices = []
        for tool in options:
            value = ctk.BooleanVar(value=(tool['page'], tool.get('sub')) in selected)
            ctk.CTkCheckBox(tools_frame, text=f"{tool['page']} — {tool['name']}", variable=value, text_color=T['text'], border_color=T['border'], font=('Consolas', 11)).pack(anchor='w', pady=6)
            choices.append((tool, value))
        tools_error = ctk.CTkLabel(window, text='', text_color=T['error'])
        tools_error.pack(anchor='w', padx=20)
        def save():
            chosen = [t for t, value in choices if value.get()]
            name_error.configure(text='' if name.get().strip() else 'กรุณากรอกชื่อกลุ่ม')
            tools_error.configure(text='' if chosen else 'เลือกเครื่องมืออย่างน้อย 1 รายการ')
            if not name.get().strip() or not chosen:
                return
            updated = make_group(name.get(), chosen, group['id'] if group else None)
            groups = [updated if g['id'] == updated['id'] else g for g in self.groups] if group else self.groups + [updated]
            if self._commit(groups):
                window.destroy()
            else:
                tools_error.configure(text='บันทึกไม่สำเร็จ ตรวจสิทธิ์เขียน config')
        actions = ctk.CTkFrame(window, fg_color='transparent')
        actions.pack(fill='x', padx=20, pady=(0, 16))
        ctk.CTkButton(actions, text='Cancel', width=110, command=window.destroy).pack(side='left')
        ctk.CTkButton(actions, text='Save', width=110, command=save).pack(side='right')
        return window
