import os
import platform
from datetime import datetime

import customtkinter as ctk
from Tools.window_layout import fit_window


BG_COLOR = "#0D0D12"
PANEL_COLOR = "#15151E"
CARD_COLOR = "#1E1E2A"
INPUT_BG = "#0A0A0F"
BORDER_COLOR = "#333344"
ACCENT_CYAN = "#00FFFF"
ACCENT_GREEN = "#00FF41"
ACCENT_PURPLE = "#6f63ff"
TEXT_DIM = "#8892B0"
ALERT_RED = "#FF3366"
ALERT_AMBER = "#FFB800"


class DashboardPage(ctk.CTkFrame):
    """หน้า Dashboard ที่เป็นศูนย์ควบคุมและสรุปกิจกรรมของ UNIT."""

    # หน้าที่: เชื่อม DashboardStore ของหน้าต่างหลัก สร้างส่วนแสดงผล และโหลดสถิติเริ่มต้น
    # ที่มา: app.py::UNITApp.__init__ (เรียกตรง)
    # Input: self (DashboardPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: master (tkinter.Misc (widget ของ Tk/CustomTkinter)) — หน้าต่างหรือ widget ที่ผู้เรียกสร้างไว้
    def __init__(self, master):
        super().__init__(master, fg_color=BG_COLOR)
        self.app_root = master.master
        self.store = self.app_root.dashboard_store
        self.stat_value_labels = {}
        self._bound_shortcuts = []

        self.main_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=BORDER_COLOR,
            scrollbar_button_hover_color=ACCENT_PURPLE,
        )
        self.main_frame.pack(fill="both", expand=True, padx=24, pady=20)

        self._build_header()
        self._build_stats_section()
        self._build_favorites_section()
        self._build_detail_sections()

    # หน้าที่: สร้างหัวข้อและคำอธิบายของหน้า Dashboard
    # ที่มา: pages/dashboard.py::DashboardPage.__init__ (เรียกตรง)
    # Input: self (DashboardPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def _build_header(self):
        from Tools.history_hooks import open_history
        from Tools.system_check import open_window
        header = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 12))
        controls = ctk.CTkFrame(header, fg_color="transparent")

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(fill="x")
        ctk.CTkLabel(
            title_box,
            text=">_ UNIT COMMAND DASHBOARD",
            font=("Consolas", 28, "bold"),
            text_color=ACCENT_CYAN,
        ).pack(anchor="w")
        self.persistence_notice = ctk.CTkLabel(
            title_box, text="", font=("Consolas", 11), text_color=ALERT_AMBER
        )
        self.persistence_notice.pack(anchor="w", pady=(4, 0))
        controls.pack(fill='x', pady=(8, 0))
        button_style = dict(height=32, fg_color='transparent', border_width=1,
                            border_color=ACCENT_CYAN, text_color=ACCENT_CYAN,
                            hover_color=CARD_COLOR)
        ctk.CTkButton(controls, text='System Check', width=115, **button_style,
                      command=lambda: open_window(self.winfo_toplevel())).pack(side='right')
        ctk.CTkButton(controls, text='History', width=90, **button_style,
                      command=lambda: open_history(self.winfo_toplevel(), 'All')).pack(side='right', padx=(0, 8))

        system_bar = ctk.CTkFrame(
            self.main_frame,
            fg_color=PANEL_COLOR,
            border_width=1,
            border_color=BORDER_COLOR,
            corner_radius=6,
        )
        system_bar.pack(fill="x", pady=(0, 15))
        system_text = (
            f"SYSTEM READY  •  {platform.system()} {platform.release()}"
            f"  •  WORKSPACE {os.path.basename(os.getcwd())}"
        )
        ctk.CTkLabel(
            system_bar,
            text=system_text,
            font=("Consolas", 11, "bold"),
            text_color=ACCENT_GREEN,
        ).pack(anchor="w", padx=14, pady=10)

    # หน้าที่: สร้างการ์ดตัวเลขสถิติรวมที่อัปเดตภายหลังได้
    # ที่มา: pages/dashboard.py::DashboardPage.__init__ (เรียกตรง)
    # Input: self (DashboardPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def _build_stats_section(self):
        ctk.CTkLabel(
            self.main_frame,
            text="[ USAGE STATISTICS ]",
            font=("Consolas", 15, "bold"),
            text_color=ACCENT_CYAN,
        ).pack(anchor="w", pady=(0, 8))

        stats_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        stats_frame.pack(fill="x", pady=(0, 18))
        for column in range(4):
            stats_frame.grid_columnconfigure(column, weight=1)

        cards = [
            ("operations", "OPERATIONS", ACCENT_CYAN),
            ("flags", "FLAGS FOUND", ACCENT_GREEN),
            ("files", "FILES ANALYZED", ACCENT_PURPLE),
            ("success_rate", "SUCCESS RATE", ALERT_AMBER),
        ]
        for column, (key, title, color) in enumerate(cards):
            card = ctk.CTkFrame(
                stats_frame,
                fg_color=CARD_COLOR,
                border_width=1,
                border_color=BORDER_COLOR,
                corner_radius=7,
            )
            card.grid(
                row=0,
                column=column,
                sticky="nsew",
                padx=(0 if column == 0 else 5, 0 if column == 3 else 5),
            )
            ctk.CTkFrame(card, height=3, fg_color=color, corner_radius=0).pack(
                fill="x"
            )
            value_label = ctk.CTkLabel(
                card,
                text="0",
                font=("Consolas", 28, "bold"),
                text_color=color,
            )
            value_label.pack(anchor="w", padx=15, pady=(12, 0))
            ctk.CTkLabel(
                card,
                text=title,
                font=("Consolas", 11, "bold"),
                text_color=TEXT_DIM,
            ).pack(anchor="w", padx=15, pady=(0, 12))
            self.stat_value_labels[key] = value_label

    # หน้าที่: สร้างพื้นที่แสดงการ์ดทางลัดรายการโปรด โดยไม่มีปุ่มจัดหมวด/ปักหมุดเดิม
    # ที่มา: pages/dashboard.py::DashboardPage.__init__ (เรียกตรง)
    # Input: self (DashboardPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def _build_favorites_section(self):
        header = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(
            header,
            text="[ PINNED TOOLS & SHORTCUTS ]",
            font=("Consolas", 15, "bold"),
            text_color=ACCENT_CYAN,
        ).pack(side="left")

        self.favorites_frame = ctk.CTkFrame(
            self.main_frame,
            fg_color=PANEL_COLOR,
            border_width=1,
            border_color=BORDER_COLOR,
            corner_radius=7,
        )
        self.favorites_frame.pack(fill="x", pady=(0, 18))

    # หน้าที่: สร้าง panel ของการแข่งขัน เครื่องมือยอดนิยม และไฟล์ล่าสุด
    # ที่มา: pages/dashboard.py::DashboardPage.__init__ (เรียกตรง)
    # Input: self (DashboardPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def _build_detail_sections(self):
        detail_row = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        detail_row.pack(fill="x", pady=(0, 18))
        detail_row.grid_columnconfigure(0, weight=2)
        detail_row.grid_columnconfigure(1, weight=1)

        competition_panel = self._create_panel(
            detail_row, "[ CTF COMPETITION STATISTICS ]"
        )
        competition_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        self.competition_stats_frame = ctk.CTkFrame(
            competition_panel, fg_color="transparent"
        )
        self.competition_stats_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        top_panel = self._create_panel(detail_row, "[ TOP 3 TOOLS ]")
        top_panel.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        self.top_tools_frame = ctk.CTkFrame(top_panel, fg_color="transparent")
        self.top_tools_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        recent_panel = self._create_panel(self.main_frame, "[ RECENT FILES ]")
        recent_panel.pack(fill="x", pady=(0, 12))
        self.recent_files_frame = ctk.CTkFrame(recent_panel, fg_color="transparent")
        self.recent_files_frame.pack(fill="x", padx=12, pady=(0, 12))

    # หน้าที่: สร้างกรอบและหัวข้อ panel สำหรับส่วนแสดงรายละเอียด
    # ที่มา: pages/dashboard.py::DashboardPage._build_detail_sections (เรียกตรง)
    # Input: master (tkinter.Misc (widget ของ Tk/CustomTkinter)) — หน้าต่างหรือ widget ที่ผู้เรียกสร้างไว้
    # Input: title (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    @staticmethod
    def _create_panel(master, title):
        panel = ctk.CTkFrame(
            master,
            fg_color=PANEL_COLOR,
            border_width=1,
            border_color=BORDER_COLOR,
            corner_radius=7,
        )
        ctk.CTkLabel(
            panel,
            text=title,
            font=("Consolas", 14, "bold"),
            text_color=ACCENT_CYAN,
        ).pack(anchor="w", padx=14, pady=12)
        return panel

    # หน้าที่: ทำลาย widget ลูกใน frame เพื่อเตรียมวาดข้อมูลใหม่
    # ที่มา: pages/dashboard.py::DashboardPage._render_favorites (เรียกตรง)
    # ที่มา: pages/dashboard.py::DashboardPage._render_competition_stats (เรียกตรง)
    # ที่มา: pages/dashboard.py::DashboardPage._render_top_tools (เรียกตรง)
    # ที่มาเพิ่มเติม: อีก 2 จุดเรียก/อ้างอิงในโปรเจกต์
    # Input: frame (tkinter.Misc (widget ของ Tk/CustomTkinter)) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    @staticmethod
    def _clear_frame(frame):
        for widget in frame.winfo_children():
            widget.destroy()

    # หน้าที่: รีเฟรช Dashboard เมื่อหน้าต่างหลักสลับมาแสดงหน้านี้
    # ที่มา: app.py::UNITApp.switch_page (เรียกตรง)
    # Input: self (DashboardPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def on_show(self):
        self.refresh_dashboard()

    # หน้าที่: อ่าน snapshot จาก store แล้วอัปเดตตัวเลขและรายการบน UI
    # ที่มา: pages/dashboard.py::DashboardPage.on_show (เรียกตรง)
    # ที่มา: pages/dashboard.py::DashboardPage.change_competition (เรียกตรง)
    # ที่มา: pages/dashboard.py::DashboardPage.remove_favorite (เรียกตรง)
    # ที่มาเพิ่มเติม: อีก 4 จุดเรียก/อ้างอิงในโปรเจกต์
    # Input: self (DashboardPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def refresh_dashboard(self):
        error = getattr(self.store, "persistence_error", None)
        self.persistence_notice.configure(
            text=(f"[READ-ONLY] {error} — repair the file to enable saving" if error else "")
        )
        snapshot = self.store.get_snapshot()
        totals = snapshot["totals"]
        self.stat_value_labels["operations"].configure(text=str(totals["operations"]))
        self.stat_value_labels["flags"].configure(text=str(totals["flags"]))
        self.stat_value_labels["files"].configure(text=str(totals["files"]))
        self.stat_value_labels["success_rate"].configure(
            text=f"{totals['success_rate']}%"
        )

        self._render_favorites(snapshot["favorites"], snapshot["categories"])
        self._render_competition_stats(snapshot["competition_stats"])
        self._render_top_tools(snapshot["top_tools"])
        self._render_recent_files(snapshot["recent_files"])

    # หน้าที่: จัดการ์ดรายการโปรดตามหมวดพร้อมปุ่ม OPEN/ลบ โดยไม่แสดงคีย์ลัด
    # ที่มา: pages/dashboard.py::DashboardPage.refresh_dashboard (เรียกตรง)
    # Input: self (DashboardPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: favorites (list[dict[str, Any]]) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: categories (list[str]) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def _render_favorites(self, favorites, categories):
        self._clear_frame(self.favorites_frame)
        if not favorites:
            ctk.CTkLabel(
                self.favorites_frame,
                text="No pinned tools.",
                font=("Consolas", 12),
                text_color=TEXT_DIM,
            ).pack(padx=15, pady=20)
            return

        ordered_categories = list(categories)
        for favorite in favorites:
            category = favorite.get("category", "Core")
            if category not in ordered_categories:
                ordered_categories.append(category)

        for category in ordered_categories:
            category_items = [
                item for item in favorites if item.get("category", "Core") == category
            ]
            if not category_items:
                continue

            group = ctk.CTkFrame(self.favorites_frame, fg_color="transparent")
            group.pack(fill="x", padx=12, pady=(10, 4))
            ctk.CTkLabel(
                group,
                text=f":: {category.upper()}",
                font=("Consolas", 11, "bold"),
                text_color=ACCENT_PURPLE,
            ).pack(anchor="w", pady=(0, 5))

            card_grid = ctk.CTkFrame(group, fg_color="transparent")
            card_grid.pack(fill="x")
            for column in range(3):
                card_grid.grid_columnconfigure(column, weight=1)

            for index, favorite in enumerate(category_items):
                row = index // 3
                column = index % 3
                card = ctk.CTkFrame(
                    card_grid,
                    fg_color=CARD_COLOR,
                    border_width=1,
                    border_color=BORDER_COLOR,
                    corner_radius=5,
                )
                card.grid(row=row, column=column, sticky="nsew", padx=4, pady=4)

                title_row = ctk.CTkFrame(card, fg_color="transparent")
                title_row.pack(fill="x", padx=10, pady=(9, 4))
                ctk.CTkLabel(
                    title_row,
                    text=favorite.get("name", "Tool"),
                    font=("Consolas", 12, "bold"),
                    text_color="white",
                    anchor="w",
                ).pack(side="left", fill="x", expand=True)
                ctk.CTkButton(
                    title_row,
                    text="×",
                    width=24,
                    height=24,
                    fg_color="transparent",
                    text_color=ALERT_RED,
                    hover_color="#4A0011",
                    command=lambda target=favorite.get("target"): self.remove_favorite(
                        target
                    ),
                ).pack(side="right")

                ctk.CTkButton(
                    card,
                    text="OPEN",
                    height=27,
                    fg_color="transparent",
                    border_width=1,
                    border_color=ACCENT_CYAN,
                    text_color=ACCENT_CYAN,
                    hover_color="#003344",
                    command=lambda item=favorite: self.launch_favorite(item),
                ).pack(fill="x", padx=10, pady=(7, 10))

    # หน้าที่: วาดสถิติของแต่ละการแข่งขันลง panel
    # ที่มา: pages/dashboard.py::DashboardPage.refresh_dashboard (เรียกตรง)
    # Input: self (DashboardPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: rows (list[dict[str, Any]]) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def _render_competition_stats(self, rows):
        self._clear_frame(self.competition_stats_frame)
        headers = ["CTF", "OPS", "FILES", "FLAGS", "SUCCESS"]
        weights = [3, 1, 1, 1, 2]
        for column, (header, weight) in enumerate(zip(headers, weights)):
            self.competition_stats_frame.grid_columnconfigure(column, weight=weight)
            ctk.CTkLabel(
                self.competition_stats_frame,
                text=header,
                font=("Consolas", 10, "bold"),
                text_color=TEXT_DIM,
            ).grid(row=0, column=column, sticky="w", padx=5, pady=(0, 5))

        for row_index, row in enumerate(rows, start=1):
            operations = row["operations"]
            success_text = f"{row['success']}/{operations}" if operations else "0/0"
            values = [
                row["name"],
                row["operations"],
                row["files"],
                row["flags"],
                success_text,
            ]
            for column, value in enumerate(values):
                ctk.CTkLabel(
                    self.competition_stats_frame,
                    text=str(value),
                    font=("Consolas", 11, "bold" if column == 0 else "normal"),
                    text_color=ACCENT_GREEN if column == 3 and row["flags"] else "white",
                    anchor="w",
                ).grid(row=row_index, column=column, sticky="w", padx=5, pady=4)

    # หน้าที่: แสดงอันดับเครื่องมือและจำนวนครั้งที่ใช้งาน
    # ที่มา: pages/dashboard.py::DashboardPage.refresh_dashboard (เรียกตรง)
    # Input: self (DashboardPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: top_tools (list[tuple[str, int]]) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def _render_top_tools(self, top_tools):
        self._clear_frame(self.top_tools_frame)
        if not top_tools:
            ctk.CTkLabel(
                self.top_tools_frame,
                text="No activity yet.",
                font=("Consolas", 11),
                text_color=TEXT_DIM,
            ).pack(anchor="w", pady=8)
            return

        colors = [ALERT_AMBER, TEXT_DIM, "#CD7F32"]
        for rank, (tool, count) in enumerate(top_tools, start=1):
            row = ctk.CTkFrame(self.top_tools_frame, fg_color=CARD_COLOR, corner_radius=5)
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(
                row,
                text=f"#{rank}",
                width=35,
                font=("Consolas", 14, "bold"),
                text_color=colors[rank - 1],
            ).pack(side="left", padx=(8, 2), pady=8)
            ctk.CTkLabel(
                row,
                text=tool,
                font=("Consolas", 11, "bold"),
                text_color="white",
                anchor="w",
            ).pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(
                row,
                text=f"{count} uses",
                font=("Consolas", 10),
                text_color=ACCENT_GREEN,
            ).pack(side="right", padx=10)

    # หน้าที่: แสดงไฟล์ล่าสุดพร้อมข้อมูลกิจกรรมและปุ่มเปิดไฟล์
    # ที่มา: pages/dashboard.py::DashboardPage.refresh_dashboard (เรียกตรง)
    # Input: self (DashboardPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: recent_files (list[dict[str, Any]]) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def _render_recent_files(self, recent_files):
        self._clear_frame(self.recent_files_frame)
        if not recent_files:
            ctk.CTkLabel(
                self.recent_files_frame,
                text="No recent files. Analyzed files will appear here.",
                font=("Consolas", 11),
                text_color=TEXT_DIM,
            ).pack(anchor="w", pady=8)
            return

        for item in recent_files:
            row = ctk.CTkFrame(self.recent_files_frame, fg_color=CARD_COLOR, corner_radius=5)
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(
                row,
                text="FILE" if item["exists"] else "MISSING",
                width=65,
                font=("Consolas", 10, "bold"),
                text_color=ACCENT_GREEN if item["exists"] else ALERT_RED,
            ).pack(side="left", padx=(8, 4), pady=8)

            text_box = ctk.CTkFrame(row, fg_color="transparent")
            text_box.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(
                text_box,
                text=item["name"],
                font=("Consolas", 11, "bold"),
                text_color="white",
                anchor="w",
            ).pack(fill="x", anchor="w")
            ctk.CTkLabel(
                text_box,
                text=f"{item['competition']}  •  {item['tool']}  •  {self._format_time(item['timestamp'])}",
                font=("Consolas", 9),
                text_color=TEXT_DIM,
                anchor="w",
            ).pack(fill="x", anchor="w")

            ctk.CTkButton(
                row,
                text="INSPECT",
                width=80,
                height=27,
                fg_color="transparent",
                border_width=1,
                border_color=ACCENT_CYAN,
                text_color=ACCENT_CYAN,
                hover_color="#003344",
                state="normal" if item["exists"] else "disabled",
                command=lambda path=item["path"]: self.open_recent_file(path),
            ).pack(side="right", padx=10)

    # หน้าที่: แปลง timestamp ที่เก็บไว้เป็นข้อความวันเวลาสำหรับหน้าจอ
    # ที่มา: pages/dashboard.py::DashboardPage._render_recent_files (เรียกตรง)
    # Input: timestamp (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    @staticmethod
    def _format_time(timestamp):
        try:
            parsed = datetime.fromisoformat(timestamp)
            return parsed.astimezone().strftime("%Y-%m-%d %H:%M")
        except (TypeError, ValueError):
            return "--"

    # หน้าที่: รวบรวมเป้าหมายหน้าเครื่องมือ Saved Pipelines และ App Portal สำหรับฟอร์มปักหมุด
    # ที่มา: pages/dashboard.py::DashboardPage.open_pin_popup (เรียกตรง)
    # Input: self (DashboardPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def get_available_tools(self):
        tools = []
        pages = getattr(self.app_root, "pages", {})
        for page_name in pages:
            if page_name != "Dashboard":
                tools.append(
                    {
                        "label": f"Page • {page_name}",
                        "name": page_name,
                        "target": f"page:{page_name}",
                    }
                )

        pipeline_page = pages.get("Pipeline")
        if pipeline_page:
            pipeline_names = sorted(
                set(pipeline_page.engine.file_tools) | set(pipeline_page.engine.text_tools)
            )
            for tool_name in pipeline_names:
                tools.append(
                    {
                        "label": f"Pipeline Tool • {tool_name}",
                        "name": tool_name,
                        "target": f"pipeline_tool:{tool_name}",
                    }
                )
            for saved in pipeline_page.load_saved_pipelines():
                name = saved.get("pipeline_name")
                if name:
                    tools.append(
                        {
                            "label": f"Saved Pipeline • {name}",
                            "name": name,
                            "target": f"pipeline_saved:{name}",
                        }
                    )

        portal_page = pages.get("App Portal")
        if portal_page:
            for tool in portal_page.tools:
                name = tool.get("name")
                if name:
                    tools.append(
                        {
                            "label": f"App Portal • {name}",
                            "name": name,
                            "target": f"portal:{name}",
                        }
                    )

        unique = {}
        for tool in tools:
            unique.setdefault(tool["target"], tool)
        return list(unique.values())

    # หน้าที่: สร้างฟอร์มปักหมุดรายการโปรด; helper เดิมที่ไม่ได้มีปุ่มเรียกบนหน้าหลักแล้ว
    # ที่มา: helper ของหน้านี้สำหรับผู้เรียกหรือ callback; ไม่มีจุดเรียกตรงใน flow ปัจจุบันที่ตรวจพบ
    # Input: self (DashboardPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def open_pin_popup(self):
        available = self.get_available_tools()
        if not available:
            return

        popup = self._create_popup("PIN TOOL", "620x450")
        ctk.CTkLabel(
            popup,
            text=">_ PIN TOOL TO DASHBOARD",
            font=("Consolas", 18, "bold"),
            text_color=ACCENT_CYAN,
        ).pack(pady=(18, 12))

        form = ctk.CTkFrame(popup, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=25)
        tool_map = {item["label"]: item for item in available}
        selected_tool = ctk.StringVar(value=available[0]["label"])
        category_values = self.store.list_categories()
        selected_category = ctk.StringVar(value=category_values[0])
        shortcut_values = ["None"] + [f"Ctrl+{i}" for i in range(1, 10)] + [
            f"Alt+{i}" for i in range(1, 10)
        ]
        selected_shortcut = ctk.StringVar(value="None")

        self._form_label(form, "TOOL")
        ctk.CTkOptionMenu(
            form,
            values=list(tool_map),
            variable=selected_tool,
            height=35,
            fg_color=INPUT_BG,
            button_color=CARD_COLOR,
            dropdown_fg_color=PANEL_COLOR,
            text_color="white",
        ).pack(fill="x", pady=(0, 12))
        self._form_label(form, "CATEGORY")
        ctk.CTkOptionMenu(
            form,
            values=category_values,
            variable=selected_category,
            height=35,
            fg_color=INPUT_BG,
            button_color=CARD_COLOR,
            dropdown_fg_color=PANEL_COLOR,
            text_color="white",
        ).pack(fill="x", pady=(0, 12))
        self._form_label(form, "KEYBOARD SHORTCUT")
        ctk.CTkOptionMenu(
            form,
            values=shortcut_values,
            variable=selected_shortcut,
            height=35,
            fg_color=INPUT_BG,
            button_color=CARD_COLOR,
            dropdown_fg_color=PANEL_COLOR,
            text_color="white",
        ).pack(fill="x", pady=(0, 16))

        # หน้าที่: อ่านเครื่องมือ ชื่อ หมวด และคีย์ลัดจากฟอร์มแล้วบันทึกรายการโปรด
        # ที่มา: pages/dashboard.py::DashboardPage.open_pin_popup (อ้างอิง/callback)
        # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
        # Closure: popup (CTkToplevel) — รับจาก scope DashboardPage.open_pin_popup
        # Closure: selected_category (ctk.StringVar) — รับจาก scope DashboardPage.open_pin_popup
        # Closure: selected_shortcut (ctk.StringVar) — รับจาก scope DashboardPage.open_pin_popup
        # Closure: selected_tool (ctk.StringVar) — รับจาก scope DashboardPage.open_pin_popup
        # Closure: self (DashboardPage) — รับจาก scope DashboardPage.open_pin_popup
        # Closure: tool_map (dict) — รับจาก scope DashboardPage.open_pin_popup
        def save_pin():
            selected = tool_map[selected_tool.get()]
            shortcut = selected_shortcut.get()
            try:
                self.store.save_favorite(selected["name"], selected["target"], selected_category.get(), "" if shortcut == "None" else shortcut)
            except (OSError, ValueError) as exc:
                self.persistence_notice.configure(text=f"[READ-ONLY] {exc}")
                return
            popup.destroy()
            self.refresh_dashboard()

        ctk.CTkButton(
            form,
            text="SAVE PIN",
            fg_color=ACCENT_GREEN,
            text_color="black",
            hover_color="#00CC33",
            command=save_pin,
        ).pack(fill="x")

    # หน้าที่: สร้างฟอร์มจัดหมวด; helper เดิมที่ถอดปุ่มเรียกบนหน้าหลักแล้ว
    # ที่มา: helper ของหน้านี้สำหรับผู้เรียกหรือ callback; ไม่มีจุดเรียกตรงใน flow ปัจจุบันที่ตรวจพบ
    # Input: self (DashboardPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def open_category_popup(self):
        popup = self._create_popup("MANAGE CATEGORIES", "550x490")
        ctk.CTkLabel(
            popup,
            text=">_ CUSTOM TOOL CATEGORIES",
            font=("Consolas", 18, "bold"),
            text_color=ACCENT_PURPLE,
        ).pack(pady=(18, 12))

        add_row = ctk.CTkFrame(popup, fg_color="transparent")
        add_row.pack(fill="x", padx=22, pady=(0, 10))
        category_entry = ctk.CTkEntry(
            add_row,
            placeholder_text="New category name...",
            fg_color=INPUT_BG,
            border_color=BORDER_COLOR,
            text_color="white",
        )
        category_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        list_frame = ctk.CTkScrollableFrame(
            popup, fg_color=PANEL_COLOR, border_width=1, border_color=BORDER_COLOR
        )
        list_frame.pack(fill="both", expand=True, padx=22, pady=(0, 18))

        # หน้าที่: วาดรายการหมวดและปุ่มลบในฟอร์มจัดหมวด
        # ที่มา: pages/dashboard.py::DashboardPage.open_category_popup (เรียกตรง)
        # ที่มา: pages/dashboard.py::DashboardPage.open_category_popup.add_category (เรียกตรง)
        # ที่มา: pages/dashboard.py::DashboardPage.open_category_popup.delete_category (เรียกตรง)
        # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
        # Closure: list_frame (ctk.CTkScrollableFrame) — รับจาก scope DashboardPage.open_category_popup
        # Closure: self (DashboardPage) — รับจาก scope DashboardPage.open_category_popup
        def render_categories():
            self._clear_frame(list_frame)
            for category in self.store.list_categories():
                row = ctk.CTkFrame(list_frame, fg_color=CARD_COLOR)
                row.pack(fill="x", pady=3)
                ctk.CTkLabel(
                    row,
                    text=category,
                    font=("Consolas", 12, "bold"),
                    text_color="white",
                ).pack(side="left", padx=10, pady=8)
                if category != "Core":
                    ctk.CTkButton(
                        row,
                        text="DELETE",
                        width=65,
                        height=25,
                        fg_color="transparent",
                        border_width=1,
                        border_color=ALERT_RED,
                        text_color=ALERT_RED,
                        hover_color="#4A0011",
                        command=lambda name=category: delete_category(name),
                    ).pack(side="right", padx=8)

        # หน้าที่: อ่านชื่อหมวดจาก Entry แล้วเพิ่มลง store และรีเฟรช UI
        # ที่มา: pages/dashboard.py::DashboardPage.open_category_popup (เรียกตรง)
        # ที่มา: pages/dashboard.py::DashboardPage.open_category_popup (อ้างอิง/callback)
        # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
        # Closure: category_entry (ctk.CTkEntry) — รับจาก scope DashboardPage.open_category_popup
        # Closure: self (DashboardPage) — รับจาก scope DashboardPage.open_category_popup
        # อ่านภายใน: category_entry ผ่าน .get() — str จากช่องกรอก หรือชนิดที่ Tk Variable กำหนด
        def add_category():
            name = category_entry.get().strip()
            if not name:
                return
            try:
                self.store.add_category(name)
            except (OSError, ValueError) as exc:
                self.persistence_notice.configure(text=f"[READ-ONLY] {exc}")
                return
            category_entry.delete(0, "end")
            render_categories()
            self.refresh_dashboard()

        # หน้าที่: ลบหมวดที่เลือกและรีเฟรช popup กับรายการโปรด
        # ที่มา: pages/dashboard.py::DashboardPage.open_category_popup.render_categories (เรียกตรง)
        # Input: name (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
        # Closure: self (DashboardPage) — รับจาก scope DashboardPage.open_category_popup
        def delete_category(name):
            try:
                self.store.remove_category(name)
            except OSError as exc:
                self.persistence_notice.configure(text=f"[READ-ONLY] {exc}")
                return
            render_categories()
            self.refresh_dashboard()

        ctk.CTkButton(
            add_row,
            text="ADD",
            width=70,
            fg_color=ACCENT_PURPLE,
            hover_color="#584fcc",
            command=add_category,
        ).pack(side="right")
        category_entry.bind("<Return>", lambda _event: add_category())
        render_categories()

    # หน้าที่: เปิดฟอร์มสร้างการแข่งขันใหม่
    # ที่มา: helper ของหน้านี้สำหรับผู้เรียกหรือ callback; ไม่มีจุดเรียกตรงใน flow ปัจจุบันที่ตรวจพบ
    # Input: self (DashboardPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def open_competition_popup(self):
        popup = self._create_popup("ADD CTF COMPETITION", "520x280")
        ctk.CTkLabel(
            popup,
            text=">_ NEW CTF COMPETITION",
            font=("Consolas", 18, "bold"),
            text_color=ACCENT_GREEN,
        ).pack(pady=(22, 14))
        entry = ctk.CTkEntry(
            popup,
            placeholder_text="Example: TCTT2026",
            height=38,
            fg_color=INPUT_BG,
            border_color=BORDER_COLOR,
            text_color="white",
        )
        entry.pack(fill="x", padx=28, pady=(0, 14))

        # หน้าที่: อ่านชื่อจากฟอร์ม เพิ่มการแข่งขัน และรีเฟรช Dashboard
        # ที่มา: pages/dashboard.py::DashboardPage.open_competition_popup (เรียกตรง)
        # ที่มา: pages/dashboard.py::DashboardPage.open_competition_popup (อ้างอิง/callback)
        # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
        # Closure: entry (ctk.CTkEntry) — รับจาก scope DashboardPage.open_competition_popup
        # Closure: popup (CTkToplevel) — รับจาก scope DashboardPage.open_competition_popup
        # Closure: self (DashboardPage) — รับจาก scope DashboardPage.open_competition_popup
        # อ่านภายใน: entry ผ่าน .get() — str จากช่องกรอก หรือชนิดที่ Tk Variable กำหนด
        def save_competition():
            name = entry.get().strip()
            if not name:
                return
            try:
                self.store.add_competition(name)
            except (OSError, ValueError) as exc:
                self.persistence_notice.configure(text=f"[READ-ONLY] {exc}")
                return
            popup.destroy()
            self.refresh_dashboard()

        ctk.CTkButton(
            popup,
            text="CREATE & SET ACTIVE",
            fg_color=ACCENT_GREEN,
            text_color="black",
            hover_color="#00CC33",
            command=save_competition,
        ).pack(fill="x", padx=28)
        entry.bind("<Return>", lambda _event: save_competition())

    # หน้าที่: สร้างหน้าต่างย่อยพร้อมชื่อ ขนาด และธีมของ Dashboard
    # ที่มา: pages/dashboard.py::DashboardPage.open_pin_popup (เรียกตรง)
    # ที่มา: pages/dashboard.py::DashboardPage.open_category_popup (เรียกตรง)
    # ที่มา: pages/dashboard.py::DashboardPage.open_competition_popup (เรียกตรง)
    # Input: self (DashboardPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: title (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: geometry (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def _create_popup(self, title, geometry):
        popup = ctk.CTkToplevel(self)
        popup.title(title)
        fit_window(popup, geometry)
        popup.configure(fg_color=BG_COLOR)
        popup.attributes("-topmost", True)
        popup.grab_set()
        return popup

    # หน้าที่: สร้าง label หัวข้อฟิลด์ในแบบฟอร์ม
    # ที่มา: pages/dashboard.py::DashboardPage.open_pin_popup (เรียกตรง)
    # Input: master (tkinter.Misc (widget ของ Tk/CustomTkinter)) — หน้าต่างหรือ widget ที่ผู้เรียกสร้างไว้
    # Input: text (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    @staticmethod
    def _form_label(master, text):
        ctk.CTkLabel(
            master,
            text=text,
            font=("Consolas", 11, "bold"),
            text_color=TEXT_DIM,
        ).pack(anchor="w", pady=(0, 4))

    # หน้าที่: เปลี่ยนการแข่งขันที่ active ใน store และอัปเดตสถิติ
    # ที่มา: helper ของหน้านี้สำหรับผู้เรียกหรือ callback; ไม่มีจุดเรียกตรงใน flow ปัจจุบันที่ตรวจพบ
    # Input: self (DashboardPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: name (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def change_competition(self, name):
        try:
            self.store.set_active_competition(name)
        except OSError as exc:
            self.persistence_notice.configure(text=f"[READ-ONLY] {exc}")
            return
        self.refresh_dashboard()

    # หน้าที่: ลบรายการโปรดตาม target แล้ววาดการ์ดใหม่
    # ที่มา: pages/dashboard.py::DashboardPage._render_favorites (เรียกตรง)
    # Input: self (DashboardPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: target (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def remove_favorite(self, target):
        try:
            self.store.remove_favorite(target)
        except OSError as exc:
            self.persistence_notice.configure(text=f"[READ-ONLY] {exc}")
            return
        self.refresh_dashboard()

    # หน้าที่: แยกชนิด target เพื่อเปิดหน้า โหลด Pipeline หรือเรียก launcher ของ App Portal
    # ที่มา: pages/dashboard.py::DashboardPage._register_shortcuts (เรียกตรง)
    # ที่มา: pages/dashboard.py::DashboardPage._render_favorites (เรียกตรง)
    # Input: self (DashboardPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: favorite (dict[str, Any]) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def launch_favorite(self, favorite):
        target = favorite.get("target", "")
        name = favorite.get("name", "Tool")
        launched = False

        if target.startswith("page:"):
            page_name = target.split(":", 1)[1]
            if page_name in self.app_root.pages:
                self.app_root.switch_page(page_name)
                launched = True
        elif target.startswith("pipeline_tool:"):
            tool_name = target.split(":", 1)[1]
            pipeline = self.app_root.pages["Pipeline"]
            if tool_name in pipeline.engine.file_tools or tool_name in pipeline.engine.text_tools:
                self.app_root.switch_page("Pipeline")
                launched = bool(pipeline.add_tool_node(tool_name))
        elif target.startswith("pipeline_saved:"):
            pipeline_name = target.split(":", 1)[1]
            self.app_root.switch_page("Pipeline")
            launched = bool(self.app_root.pages["Pipeline"].load_saved_pipeline_to_canvas(pipeline_name))
        elif target.startswith("portal:"):
            portal_name = target.split(":", 1)[1]
            portal_page = self.app_root.pages.get("App Portal")
            if portal_page:
                matched = next(
                    (tool for tool in portal_page.tools if tool.get("name") == portal_name),
                    None,
                )
                if matched:
                    portal_page.launch_app(matched)
                    # Portal records started/failed; spawning is not verified success.
                    return "break"

        if not launched:
            self.persistence_notice.configure(text="Cannot open shortcut: target was removed or Pipeline is still running.", text_color=ALERT_RED)
        self.app_root.record_activity(
            tool=name,
            category="Dashboard",
            action="Quick Launch",
            status="success" if launched else "failed",
        )
        return "break"

    # หน้าที่: ตรวจ path แล้วส่งไฟล์ไปเปิดในหน้า File Inspection
    # ที่มา: pages/dashboard.py::DashboardPage._render_recent_files (เรียกตรง)
    # Input: self (DashboardPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: path (str | PathLike[str]) — path จากตัวเลือกไฟล์/config ที่จุดเรียกส่งมา หรือ default เมื่อไม่ระบุ
    def open_recent_file(self, path):
        if not os.path.isfile(path):
            return
        self.app_root.switch_page("File Inspection")
        self.app_root.pages["File Inspection"].load_files([path])

    # หน้าที่: ผูกคีย์กับรายการโปรด; เก็บ helper เดิมไว้แต่ refresh_dashboard ไม่เรียกแล้ว
    # ที่มา: helper ของหน้านี้สำหรับผู้เรียกหรือ callback; ไม่มีจุดเรียกตรงใน flow ปัจจุบันที่ตรวจพบ
    # Input: self (DashboardPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: favorites (list[dict[str, Any]]) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def _register_shortcuts(self, favorites):
        # ถอนคีย์ลัดเดิมออกจากหน้าต่างหลัก
        for sequence, function_id in self._bound_shortcuts:
            try:
                self.app_root.unbind(sequence, function_id)
            except Exception:
                pass

        self._bound_shortcuts = []

        # ลงทะเบียนคีย์ลัดใหม่กับ UNITApp
        for favorite in favorites:
            sequence = self._shortcut_to_sequence(
                favorite.get("shortcut")
            )

            if not sequence:
                continue

            function_id = self.app_root.bind(
                sequence,
                lambda _event, item=favorite: self.launch_favorite(item),
                add="+",
            )

            self._bound_shortcuts.append(
                (sequence, function_id)
            )

    # หน้าที่: แปลงข้อความคีย์ Ctrl/Alt/Shift เป็นรูปแบบ Tk binding
    # ที่มา: pages/dashboard.py::DashboardPage._register_shortcuts (เรียกตรง)
    # Input: shortcut (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    @staticmethod
    def _shortcut_to_sequence(shortcut):
        if not shortcut:
            return None
        parts = [part.strip() for part in shortcut.split("+") if part.strip()]
        if len(parts) < 2:
            return None

        modifiers = []
        for part in parts[:-1]:
            normalized = part.lower()
            if normalized in ("ctrl", "control"):
                modifiers.append("Control")
            elif normalized == "alt":
                modifiers.append("Alt")
            elif normalized == "shift":
                modifiers.append("Shift")

        key = parts[-1].lower()
        if not modifiers or not key:
            return None
        return f"<{'-'.join(modifiers)}-Key-{key}>"

    # หน้าที่: ถอน key bindings ที่เคยบันทึกไว้ก่อนทำลายหน้า Dashboard
    # ที่มา: Tk/หน้าต่างหลักเรียกเมื่อทำลาย widget
    # Input: self (DashboardPage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def destroy(self):
        for sequence, function_id in self._bound_shortcuts:
            try:
                self.app_root.unbind(sequence, function_id)
            except Exception:
                pass

        self._bound_shortcuts = []
        super().destroy()
