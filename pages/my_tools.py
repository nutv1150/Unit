import customtkinter as ctk
from Pipeline.config_store import read_json
from Pipeline.pipeline_engine import PipelineEngine
from Tools.app_paths import writable_path
from Tools.tool_catalog import (
    DATA_HASH_BITWISE_ALGORITHMS,
    DATA_HASH_DECODE_ALGORITHMS,
    FILE_INSPECTION_TOOLS,
)
from Tools.workspace_store import CONFIG_DIR, load_records, save_records, make_group
from pages.workspace_ui import THEME_COLORS as T, COLORS, FONT, label, dialog, CTkMessagebox, ENTRY_STYLE

TOOL_OPTIONS = [
    *(
        {'name': f'{algo} decode', 'page': 'Data Hashing', 'sub': algo,
         'mode': 'Decode', 'color': 'blue'}
        for algo in DATA_HASH_DECODE_ALGORITHMS
    ),
    *(
        {'name': f'{algo} bitwise', 'page': 'Data Hashing', 'sub': algo,
         'mode': 'Bitwise', 'color': 'blue'}
        for algo in DATA_HASH_BITWISE_ALGORITHMS
    ),
    {'name': 'File Inspection', 'page': 'File Inspection', 'sub': None, 'color': 'green'},
    *(
        {'name': tool, 'page': 'File Inspection', 'sub': tool, 'color': 'green'}
        for tool in FILE_INSPECTION_TOOLS
    ),
    {'name': 'Pipeline', 'page': 'Pipeline', 'sub': None, 'color': 'purple'},
    {'name': 'Wireshark', 'page': 'App Portal', 'sub': 'Wireshark', 'color': 'amber'},
    {'name': 'Burp Suite', 'page': 'App Portal', 'sub': 'Burp Suite', 'color': 'amber'},
]


# หน้าที่: รวมรายการ Decode/Bitwise/File Inspection และ Pipeline จาก config สำหรับสร้างกลุ่มเครื่องมือ
# ที่มา: pages/my_tools.py::MyToolsPage._open_dialog (เรียกตรง)
# ที่มา: tests/test_my_tools_catalog.py::MyToolsCatalogTests.test_pipeline_tools_are_loaded_from_config (เรียกตรง)
# Input: pipeline_path (str | PathLike[str] | None) — path จากตัวเลือกไฟล์/config ที่จุดเรียกส่งมา หรือ default เมื่อไม่ระบุ
def available_tool_options(pipeline_path=None):
    """Return static shortcuts plus every valid Pipeline tool in config order."""
    path = pipeline_path or writable_path('Pipeline/custom_tools.json')
    try:
        data = read_json(path, {})
        PipelineEngine.validate_tools(data)
    except (OSError, ValueError, TypeError):
        data = {}

    pipeline_options = []
    for category, tools in data.items():
        if not isinstance(tools, list):
            continue
        pipeline_options.extend(
            {'name': tool['name'], 'page': 'Pipeline', 'sub': tool['name'],
             'category': category, 'color': 'purple'}
            for tool in tools
        )

    # Keep App Portal entries at the end while inserting Pipeline tools directly
    # after the generic Pipeline shortcut.
    insert_at = next(
        (index for index, tool in enumerate(TOOL_OPTIONS) if tool['page'] == 'App Portal'),
        len(TOOL_OPTIONS),
    )
    return TOOL_OPTIONS[:insert_at] + pipeline_options + TOOL_OPTIONS[insert_at:]


class MyToolsPage(ctk.CTkFrame):
    # หน้าที่: โหลดกลุ่มที่ผู้ใช้บันทึกไว้และสร้างหน้า My Tools พร้อม callback เปิดเครื่องมือ
    # ที่มา: app.py::UNITApp.__init__ (เรียกตรง)
    # Input: self (MyToolsPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: parent (tkinter.Misc (widget ของ Tk/CustomTkinter)) — หน้าต่างหรือ widget ที่ผู้เรียกสร้างไว้
    # Input: navigate_callback (Callable[[str, str | None, str | None], None]) — callable ที่ผู้เรียกลงทะเบียนไว้ให้เรียกต่อ
    # Input: storage_path (str | PathLike[str] | None) — path จากตัวเลือกไฟล์/config ที่จุดเรียกส่งมา หรือ default เมื่อไม่ระบุ
    # Input: **kwargs (dict[str, Any]) — keyword options ของ widget ที่ผู้เรียกส่งเพิ่มมา
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
            self.load_error = f'Could not read configuration: {exc} (original file preserved)'
        self._build_ui()

    # หน้าที่: สร้างหัวข้อ ปุ่มเพิ่มกลุ่ม และพื้นที่การ์ดเครื่องมือ
    # ที่มา: pages/my_tools.py::MyToolsPage.__init__ (เรียกตรง)
    # Input: self (MyToolsPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # อ่านภายใน: search_entry ผ่าน .get() — str จากช่องกรอก หรือชนิดที่ Tk Variable กำหนด
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

    # หน้าที่: คำนวณจำนวนคอลัมน์ใหม่ตามความกว้าง event แล้ววาดการ์ดเมื่อ layout เปลี่ยน
    # ที่มา: pages/my_tools.py::MyToolsPage._build_ui (อ้างอิง/callback)
    # Input: self (MyToolsPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: event (tkinter.Event) — Tk/TkDND ส่งมาจาก event binding; บางจุดเรียกตรงโดยไม่ส่ง event
    def _resize(self, event):
        columns = 3 if event.width >= 1080 else 2 if event.width >= 620 else 1
        if columns != self.columns:
            self.columns = columns
            self._render_cards()

    # หน้าที่: ล้างและวางการ์ดกลุ่มใหม่ตามจำนวนคอลัมน์ที่เหมาะกับพื้นที่
    # ที่มา: pages/my_tools.py::MyToolsPage._build_ui (เรียกตรง)
    # ที่มา: pages/my_tools.py::MyToolsPage._commit (เรียกตรง)
    # ที่มา: pages/my_tools.py::MyToolsPage._resize (เรียกตรง)
    # Input: self (MyToolsPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
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

    # หน้าที่: สร้างการ์ดกลุ่มพร้อมชื่อ ปุ่มจัดการ และ chips ของเครื่องมือ
    # ที่มา: pages/my_tools.py::MyToolsPage._render_cards (เรียกตรง)
    # Input: self (MyToolsPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: parent (tkinter.Misc (widget ของ Tk/CustomTkinter)) — หน้าต่างหรือ widget ที่ผู้เรียกสร้างไว้
    # Input: group (dict[str, Any]) — record จาก self.groups ที่โหลดจาก JSON หรือ None เมื่อสร้างกลุ่มใหม่
    # Input: height (int) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
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

    # หน้าที่: สร้างปุ่มเปิดเครื่องมือที่ส่ง page/sub/mode ผ่าน navigate_callback
    # ที่มา: pages/my_tools.py::MyToolsPage._build_card (เรียกตรง)
    # Input: self (MyToolsPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: parent (tkinter.Misc (widget ของ Tk/CustomTkinter)) — หน้าต่างหรือ widget ที่ผู้เรียกสร้างไว้
    # Input: tool (dict[str, Any]) — descriptor จาก catalog/config ของเครื่องมือที่เลือกไว้ในกลุ่ม
    def _build_chip(self, parent, tool):
        accent = COLORS.get(tool.get('color'), COLORS['purple'])
        text = f"● {tool['name']}"
        chip = ctk.CTkButton(parent, text=text, height=34, anchor='w', font=FONT,
                            fg_color='transparent', text_color=accent, border_width=1,
                            border_color=T['border'], hover_color=T['hover'],
                            command=lambda: self.navigate(
                                tool['page'], tool.get('sub'), tool.get('mode')
                            ))
        chip.pack(fill='x', pady=4)
        chip.bind('<Enter>', lambda _: chip.configure(text=text+'  →', border_color=accent), add='+')
        chip.bind('<Leave>', lambda _: chip.configure(text=text, border_color=T['border']), add='+')
        return chip

    # หน้าที่: บันทึกรายการกลุ่มลง JSON แล้วอัปเดตข้อมูลและการ์ดในหน่วยความจำ
    # ที่มา: pages/my_tools.py::MyToolsPage._open_dialog.save (เรียกตรง)
    # ที่มา: pages/my_tools.py::MyToolsPage._delete (เรียกตรง)
    # Input: self (MyToolsPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: groups (list[dict[str, Any]]) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def _commit(self, groups):
        if self.load_error:
            return False
        try:
            save_records(self.path, groups)
        except (OSError, ValueError) as exc:
            self.status.configure(text=f'Could not save: {exc}')
            return False
        self.groups = groups
        self.status.configure(text='')
        self._render_cards()
        return True

    # หน้าที่: ขอยืนยันก่อนลบกลุ่มที่เลือกออกจากรายการ
    # ที่มา: pages/my_tools.py::MyToolsPage._build_card (เรียกตรง)
    # Input: self (MyToolsPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: group (dict[str, Any]) — record จาก self.groups ที่โหลดจาก JSON หรือ None เมื่อสร้างกลุ่มใหม่
    def _delete(self, group):
        CTkMessagebox(self, f"Delete group {group['name']}?", lambda: self._commit([g for g in self.groups if g['id'] != group['id']]))

    # หน้าที่: เปิดฟอร์มสร้าง/แก้ชื่อกลุ่มและเลือกเครื่องมือด้วย checkboxes
    # ที่มา: pages/my_tools.py::MyToolsPage._build_ui (อ้างอิง/callback)
    # ที่มา: pages/my_tools.py::MyToolsPage._build_card (เรียกตรง)
    # Input: self (MyToolsPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: group (dict[str, Any] | None) — record จาก self.groups ที่โหลดจาก JSON หรือ None เมื่อสร้างกลุ่มใหม่
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
        options = available_tool_options()
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
        # หน้าที่: อ่านชื่อและเครื่องมือที่เลือก ตรวจข้อมูล แล้วบันทึกกลุ่มและปิดฟอร์ม
        # ที่มา: pages/my_tools.py::MyToolsPage._open_dialog (อ้างอิง/callback)
        # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
        # Closure: choices (list) — รับจาก scope MyToolsPage._open_dialog
        # Closure: group (dict[str, Any] | None) — รับจาก scope MyToolsPage._open_dialog
        # Closure: name (ctk.CTkEntry) — รับจาก scope MyToolsPage._open_dialog
        # Closure: name_error (ctk.CTkLabel) — รับจาก scope MyToolsPage._open_dialog
        # Closure: self (MyToolsPage) — รับจาก scope MyToolsPage._open_dialog
        # Closure: tools_error (ctk.CTkLabel) — รับจาก scope MyToolsPage._open_dialog
        # Closure: ยังอ่านตัวแปรร่วมอีก 1 ตัวจาก scope แม่
        def save():
            chosen = [t for t, value in choices if value.get()]
            name_error.configure(text='' if name.get().strip() else 'Enter a group name')
            tools_error.configure(text='' if chosen else 'Select at least one tool')
            if not name.get().strip() or not chosen:
                return
            updated = make_group(name.get(), chosen, group['id'] if group else None)
            groups = [updated if g['id'] == updated['id'] else g for g in self.groups] if group else self.groups + [updated]
            if self._commit(groups):
                window.destroy()
            else:
                tools_error.configure(text='Could not save. Check configuration write permissions.')
        actions = ctk.CTkFrame(window, fg_color='transparent')
        actions.pack(fill='x', padx=20, pady=(0, 16))
        ctk.CTkButton(actions, text='Cancel', width=110, command=window.destroy).pack(side='left')
        ctk.CTkButton(actions, text='Save', width=110, command=save).pack(side='right')
        return window
