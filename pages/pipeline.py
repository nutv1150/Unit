import json
from copy import deepcopy
from Tools.app_paths import writable_path
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
from Pipeline.pipeline_engine import PipelineEngine
from Pipeline.config_store import read_json, write_json, saved_pipelines, validate_saved_pipelines
from Pipeline.saved_runs import step_recipe, completed_steps, delete_recipe
from pages.pipeline_saved import SavedPipelineDialog
import tempfile
import os
import shlex
import threading
import queue
import uuid
from pathlib import Path
from Tools import history_hooks
from Tools.window_layout import fit_window
from Tools.stream_capture import PREVIEW_BYTES
from Tools.text_view import open_text_view, save_async

from Tools.artifact_bridge import (
    resolve_file_input,
    remove_temp_artifact,
)

# ==========================================
# ธีมสีหลัก (Cyberpunk / Terminal)
# ให้ตรงกับหน้า Gemini CLI / App Portal / File Inspection
# ==========================================
BG_COLOR = "#0D0D12"        # ดำสนิทเหลือบน้ำเงิน (พื้นหลังหน้า)
PANEL_COLOR = "#15151E"     # พื้นหลังกล่อง/แผงควบคุม
CARD_COLOR = "#1E1E2A"      # พื้นหลัง node / การ์ดย่อย
INPUT_BG = "#0A0A0F"        # พื้นหลังช่องกรอกข้อมูล/canvas/กล่องข้อความ
BORDER_COLOR = "#333344"    # เส้นขอบทั่วไป
ACCENT_CYAN = "#00FFFF"     # สีฟ้า Neon (ปุ่มหลัก/หัวข้อ)
ACCENT_GREEN = "#00FF41"    # สีเขียว Terminal (สถานะ/ยืนยัน)
ACCENT_PURPLE = "#6f63ff"   # สีม่วง Neon (node/เส้นเชื่อม pipeline)
TEXT_DIM = "#8892B0"        # สีเทาตัวหนังสือทั่วไป
ALERT_RED = "#FF3366"       # สีแดง-ชมพู (ลบ/ล้าง/อันตราย)


class PipelinePage(ctk.CTkFrame):
    # หน้าที่: สร้างหน้า Pipeline เชื่อม engine และเตรียม canvas, tools, Auto/Step workspaces
    # ที่มา: app.py::UNITApp.__init__ (เรียกตรง)
    # Input: self (PipelinePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: master (tkinter.Misc (widget ของ Tk/CustomTkinter)) — หน้าต่างหรือ widget ที่ผู้เรียกสร้างไว้
    def __init__(self, master):
        super().__init__(master)
        self.app_root = master.master  # ใช้เรียก switch_page / send_to_* ข้ามหน้า
        self.run_logs = []
        self.engine = PipelineEngine() #เชื่อมกับ backend
        self.temp_artifacts = []
        self.active_runs = set()
        self._pipeline_running = False
        self.pipeline_mode = "Auto"
        self._mode_workspaces = {}
        self._completed_recipe = None
        # P0.4B - Original File Routing
        self.original_file_path = None

        self.configure(fg_color=BG_COLOR)
        self.nodes = []      # เก็บข้อมูล Node ทั้งหมด
        self.node_count = 0

        # --- Header ---
        self.title_label = ctk.CTkLabel(
            self, text=">_ PIPELINE :: MULTI-STEP EXEC",
            font=("Consolas", 24, "bold"), text_color=ACCENT_CYAN
        )
        self.title_label.pack(anchor="w", padx=20, pady=(15, 5))

        self.content_row = ctk.CTkFrame(self, fg_color="transparent")
        self.content_row.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # --- Tools Panel (ด้านซ้าย) ---
        self.tools_panel = ctk.CTkScrollableFrame(
            self.content_row,
            fg_color=PANEL_COLOR,
            border_width=1,
            border_color=BORDER_COLOR,
            width=230,
            corner_radius=10
        )

        self.tools_panel.pack(side="left", fill="y", padx=(0, 15))
        self.tools_panel.configure(height=600)

        ctk.CTkLabel(
            self.tools_panel, text="ALL_TOOLS",
            font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
            text_color=ACCENT_CYAN
        ).pack(pady=(15, 10), padx=15, anchor="w")

        tool_categories = self.load_tools_from_json()
        if getattr(self, "config_error", ""):
            ctk.CTkLabel(self.tools_panel, text=self.config_error, text_color=ALERT_RED,
                         wraplength=210).pack(padx=10, pady=10)

        for cat, tools in tool_categories.items():

            # 1. สร้าง Frame แบบใส
            header_frame = ctk.CTkFrame(self.tools_panel, fg_color="transparent")
            header_frame.pack(fill="x", padx=15, pady=(10, 0))

            # 2. ใส่ชื่อหมวดหมู่
            ctk.CTkLabel(
                header_frame,
                text=cat,
                font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
                text_color=ACCENT_GREEN
            ).pack(side="left")

            # 3. แสดงรายชื่อ Tool
            for tool in tools:
                if cat in ["Pipelines", "Saved Pipelines"]:
                    self.add_saved_pipeline_row(tool)
                    continue
                lbl = ctk.CTkLabel(
                    self.tools_panel,
                    text=f"  • {tool}",
                    font=ctk.CTkFont(family="Consolas", size=12),
                    text_color=TEXT_DIM,
                    cursor="hand2"
                )
                lbl.pack(padx=15, anchor="w")

                if cat in ["Pipelines", "Saved Pipelines"]:
                    lbl.bind("<Button-1>", lambda e, name=tool: self.load_saved_pipeline_to_canvas(name))
                else:
                    lbl.bind("<Button-1>", lambda e, t=tool: self.add_tool_node(t))

            # 4. เพิ่มปุ่ม + Add Pipeline ไว้ด้านใต้สุดของหมวด Pipelines
            if cat in ["Pipelines", "Saved Pipelines"]:
                ctk.CTkButton(
                    self.tools_panel,
                    text="+ Add Pipeline",
                    command=self.open_pipeline_wizard,
                    fg_color="transparent",
                    border_width=1,
                    border_color=ACCENT_PURPLE,
                    text_color=ACCENT_PURPLE,
                    hover_color=CARD_COLOR
                ).pack(fill="x", padx=15, pady=(5, 10))

        self.add_btn = ctk.CTkButton(
            self.tools_panel, text="+ Add Tools", command=self.open_add_tool_window,
            fg_color="transparent", border_width=1, border_color=ACCENT_CYAN,
            text_color=ACCENT_CYAN, hover_color=CARD_COLOR
        )
        self.add_btn.pack(fill="x", padx=15, pady=20)

        # --- Work Area (ตรงกลาง) ---
        self.work_area = ctk.CTkFrame(
            self.content_row, fg_color=PANEL_COLOR,
            border_width=1, border_color=BORDER_COLOR, corner_radius=10
        )
        self.work_area.pack(side="left", fill="both", expand=True)

        # --- Top Controls ---
        self.controls = ctk.CTkFrame(self.work_area, fg_color="transparent")
        self.controls.pack(fill="x", padx=15, pady=15)

        self.completed_panel = ctk.CTkFrame(self.work_area, fg_color=CARD_COLOR)
        ctk.CTkLabel(self.completed_panel, text="✓ Pipeline complete",
                     text_color=ACCENT_GREEN).pack(side="left", padx=12, pady=10)
        ctk.CTkButton(self.completed_panel, text="Save Pipeline",
                      command=lambda: self.open_save_pipeline(self._completed_recipe),
                      fg_color=ACCENT_CYAN, text_color="black").pack(side="right", padx=12, pady=10)

        # Auto retains the existing prepared-pipeline workflow.
        self.mode_btn = ctk.CTkButton(
            self.controls, text="Mode: Auto", width=115,
            fg_color=CARD_COLOR, border_width=1, border_color=ACCENT_PURPLE,
            text_color=ACCENT_CYAN, command=self.toggle_pipeline_mode,
        )
        self.mode_btn.pack(side="left", padx=2)

        # Run
        self.run_btn = ctk.CTkButton(
            self.controls,
            text="Run All",
            fg_color=ACCENT_CYAN,
            text_color="black",
            width=80,
            hover_color="#00CCCC",
            command=self.run_pipeline
        )
        self.run_btn.pack(side="left", padx=2)

        # Clear
        self.clear_btn = ctk.CTkButton(
            self.controls,
            text="Clear",
            fg_color="transparent",
            border_width=1,
            border_color=ALERT_RED,
            text_color=ALERT_RED,
            width=80,
            hover_color="#331119",
            command=self.clear_pipeline
        )
        self.clear_btn.pack(side="left", padx=2)

        self.template_opt = ctk.CTkOptionMenu(
            self.controls,
            values=[
                "Templates",
                "Basic Recon",
                "Find Flag",
                "Decode Base64",
                "Stego Scan",
                "Forensics Scan"
            ],
            fg_color=INPUT_BG,
            button_color=PANEL_COLOR,
            button_hover_color=BORDER_COLOR,
            text_color=ACCENT_CYAN,
            dropdown_fg_color=PANEL_COLOR,
            dropdown_text_color=ACCENT_CYAN,
            command=self.load_template
        )

        self.template_opt.pack(side="left", padx=2)
        ctk.CTkButton(self.controls, text='History', width=90,
                      command=lambda: history_hooks.open_history(self.app_root, 'Pipeline')).pack(side='left', padx=6)

        # --- Canvas Area ---
        self.canvas_container = ctk.CTkFrame(self.work_area, fg_color=INPUT_BG, corner_radius=8)
        self.canvas_container.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self.line_canvas = tk.Canvas(self.canvas_container, bg=INPUT_BG, highlightthickness=0)
        self.line_canvas.pack(fill="both", expand=True)

        self.placeholder = ctk.CTkLabel(
            self.line_canvas, text="[ PIPELINE FLOW CANVAS ]",
            font=("Consolas", 12), text_color=TEXT_DIM
        )
        self.placeholder.place(relx=0.5, rely=0.5, anchor="center")

        # หมายเหตุ: เดิมมี popup "Pipeline Manager" ที่ผุดขึ้นบังคับทุกครั้งที่เข้าหน้านี้
        # ตัดออกแล้วเพราะ Saved Pipelines / + Add Pipeline มีอยู่แล้วในแผง ALL_TOOLS ด้านซ้าย
        # ผู้ใช้ยังเรียกดู pipeline ที่บันทึกไว้ได้ตามปกติ ไม่ต้องถูกขัดจังหวะตอนเข้าหน้า
    
    # หน้าที่: ตรวจ path และกำหนดไฟล์ต้นฉบับของ workspace โดยเคารพสถานะกำลังรัน
    # ที่มา: pages/pipeline.py::PipelinePage.open_step_window.set_new_original (เรียกตรง)
    # ที่มา: pages/pipeline.py::PipelinePage.open_step_window.browse_file (เรียกตรง)
    # Input: self (PipelinePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: path (str | PathLike[str]) — path จากตัวเลือกไฟล์/config ที่จุดเรียกส่งมา หรือ default เมื่อไม่ระบุ
    # Input: force (bool) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def set_original_file(self, path, force=False):
        """
        จดจำไฟล์ต้นฉบับของ pipeline

        force=False:
            จะไม่ทับ original เดิม

        force=True:
            ใช้เมื่อ user เลือก source ใหม่ใน step แรก
        """

        if not path:
            return False

        path = os.path.abspath(
            os.path.expanduser(path)
        )

        if not os.path.isfile(path):
            return False

        if force or not self.original_file_path:
            self.original_file_path = path

        return True


    # หน้าที่: คืน path ไฟล์ต้นฉบับที่ยังใช้งานได้และอัปเดตสถานะเมื่อไฟล์หาย
    # ที่มา: pages/pipeline.py::PipelinePage.open_step_window (เรียกตรง)
    # ที่มา: pages/pipeline.py::PipelinePage.open_step_window.use_original (เรียกตรง)
    # ที่มา: pages/pipeline.py::PipelinePage.open_step_window.browse_file (เรียกตรง)
    # Input: self (PipelinePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def get_original_file(self):
        """
        คืน original file ถ้ายังมีอยู่จริง
        """

        if (
            self.original_file_path
            and os.path.isfile(
                self.original_file_path
            )
        ):
            return self.original_file_path

        return None

    # หน้าที่: เติม path ลง Entry ของขั้นตอนโดยจัดการสถานะ readonly ชั่วคราว
    # ที่มา: pages/pipeline.py::PipelinePage.open_step_window.browse_file (เรียกตรง)
    # ที่มา: pages/pipeline.py::PipelinePage.open_step_window.use_previous (เรียกตรง)
    # ที่มา: pages/pipeline.py::PipelinePage.open_step_window.use_original (เรียกตรง)
    # ที่มาเพิ่มเติม: อีก 1 จุดเรียก/อ้างอิงในโปรเจกต์
    # Input: self (PipelinePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: entry (CTkEntry) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: path (str | PathLike[str]) — path จากตัวเลือกไฟล์/config ที่จุดเรียกส่งมา หรือ default เมื่อไม่ระบุ
    def set_step_input_path(self, entry, path):
        """
        Replace path ในช่อง input ของ Step Window
        """

        entry.delete(0, "end")

        if path:
            entry.insert(0, path)
    
    # หน้าที่: เก็บ path ของ artifact ที่หน้าเป็นเจ้าของเพื่อเก็บกวาดภายหลัง
    # ที่มา: pages/pipeline.py::PipelinePage.open_step_window (เรียกตรง)
    # ที่มา: pages/pipeline.py::PipelinePage.open_step_window.show_result (เรียกตรง)
    # ที่มา: pages/pipeline.py::PipelinePage.open_step_window.execute_tool (เรียกตรง)
    # Input: self (PipelinePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: path (str | PathLike[str]) — path จากตัวเลือกไฟล์/config ที่จุดเรียกส่งมา หรือ default เมื่อไม่ระบุ
    def register_temp_artifact(self, path):
        if path and path not in self.temp_artifacts:
            self.temp_artifacts.append(path)


    # หน้าที่: ลบ artifacts ที่ลงทะเบียนไว้แล้วล้างรายการอ้างอิง
    # ที่มา: pages/pipeline.py::PipelinePage._run_step_analysis (เรียกตรง)
    # ที่มา: pages/pipeline.py::PipelinePage._run_pipeline_steps (เรียกตรง)
    # ที่มา: pages/pipeline.py::PipelinePage.clear_pipeline (เรียกตรง)
    # Input: self (PipelinePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def cleanup_pipeline_artifacts(self):
        for path in self.temp_artifacts:
            remove_temp_artifact(path)

        self.temp_artifacts.clear()
        self.engine.prune_captures()

    # หน้าที่: ตั้ง cancel_event ของงาน subprocess ที่ยัง active
    # ที่มา: app.py::UNITApp.on_close (เรียกตรง)
    # Input: self (PipelinePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def cancel_active_runs(self):
        for event in tuple(self.active_runs):
            event.set()

    # หน้าที่: ตรวจว่างาน Pipeline ยังทำงานอยู่และแจ้งห้ามแก้ canvas ระหว่างรัน
    # ที่มา: pages/pipeline.py::PipelinePage.set_pipeline_mode (เรียกตรง)
    # ที่มา: pages/pipeline.py::PipelinePage.add_tool_node (เรียกตรง)
    # ที่มา: pages/pipeline.py::PipelinePage.run_pipeline (เรียกตรง)
    # ที่มาเพิ่มเติม: อีก 4 จุดเรียก/อ้างอิงในโปรเจกต์
    # Input: self (PipelinePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def canvas_busy(self):
        if self._pipeline_running or self.active_runs:
            messagebox.showwarning("Pipeline running", "Close the active step before editing or running another pipeline.", parent=self)
            return True
        return False

    # หน้าที่: สลับระหว่างโหมด Auto และ Step ผ่าน set_pipeline_mode
    # ที่มา: pages/pipeline.py::PipelinePage.__init__ (อ้างอิง/callback)
    # Input: self (PipelinePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def toggle_pipeline_mode(self):
        return self.set_pipeline_mode("Step" if self.pipeline_mode == "Auto" else "Auto")

    # หน้าที่: แยกเก็บและคืน nodes/input/artifacts ของแต่ละโหมดพร้อมปรับปุ่ม UI
    # ที่มา: pages/pipeline.py::PipelinePage.toggle_pipeline_mode (เรียกตรง)
    # ที่มา: pages/pipeline.py::PipelinePage.load_template (เรียกตรง)
    # ที่มา: pages/pipeline.py::PipelinePage.finalize_wizard_pipeline (เรียกตรง)
    # ที่มาเพิ่มเติม: อีก 1 จุดเรียก/อ้างอิงในโปรเจกต์
    # Input: self (PipelinePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: mode (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def set_pipeline_mode(self, mode):
        if mode not in ("Auto", "Step"):
            raise ValueError("Unknown pipeline mode")
        if mode == self.pipeline_mode:
            return True
        if self.canvas_busy():
            return False
        self.set_completed_recipe(None)
        # Keep each mode's nodes, original input and temporary artifacts separate.
        positions = [
            {axis: node['frame']._reverse_widget_scaling(float(node['frame'].place_info()[axis]))
             for axis in ('x', 'y')}
            for node in self.nodes
        ]
        self._mode_workspaces[self.pipeline_mode] = dict(
            nodes=self.nodes, positions=positions, node_count=self.node_count,
            run_logs=self.run_logs, original_file_path=self.original_file_path,
            temp_artifacts=self.temp_artifacts,
        )
        for node in self.nodes:
            node['frame'].place_forget()
        workspace = self._mode_workspaces.pop(mode, {})
        self.nodes = workspace.get('nodes', [])
        self.node_count = workspace.get('node_count', 0)
        self.run_logs = workspace.get('run_logs', [])
        self.original_file_path = workspace.get('original_file_path')
        self.temp_artifacts = workspace.get('temp_artifacts', [])
        for node, position in zip(self.nodes, workspace.get('positions', [])):
            node['frame'].place(**position)
        self.pipeline_mode = mode
        self.mode_btn.configure(text=f"Mode: {mode}")
        self.run_btn.configure(text="Run All" if mode == "Auto" else "Run Step")
        self.draw_connections()
        self.after_idle(self.draw_connections)
        return True

    # เพิ่ม node (tool) ลง canvas
    # หน้าที่: เพิ่ม tool ที่ผู้ใช้เลือกลง canvas; ในโหมด Step เริ่ม exploration ใหม่
    # ที่มา: app.py::UNITApp.navigate_to (เรียกตรง)
    # ที่มา: pages/dashboard.py::DashboardPage.launch_favorite (เรียกตรง)
    # ที่มา: pages/pipeline.py::PipelinePage.load_template (เรียกตรง)
    # ที่มาเพิ่มเติม: อีก 3 จุดเรียก/อ้างอิงในโปรเจกต์
    # Input: self (PipelinePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: tool_name (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: user_desc (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def add_tool_node(self, tool_name, user_desc=""):
        if self.canvas_busy():
            return
        if self.pipeline_mode == "Step":
            # A sidebar choice starts a new exploration, never a prebuilt chain.
            self.clear_pipeline()
        return self._append_tool_node(tool_name, user_desc)

    # หน้าที่: สร้างการ์ด node พร้อม metadata และ event สำหรับลากตำแหน่ง
    # ที่มา: pages/pipeline.py::PipelinePage.add_tool_node (เรียกตรง)
    # ที่มา: pages/pipeline.py::PipelinePage._run_step_analysis (เรียกตรง)
    # Input: self (PipelinePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: tool_name (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: user_desc (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def _append_tool_node(self, tool_name, user_desc=""):
        """Internal append; the Step runner may append while canvas edits are locked."""
        self.set_completed_recipe(None)
        self.node_count += 1

        node = ctk.CTkFrame(self.line_canvas, fg_color=CARD_COLOR, corner_radius=4,
                            border_width=1, border_color=ACCENT_PURPLE, width=110, height=35)

        x_pos = 50 + (len(self.nodes) * 160)
        y_pos = 50 + ((len(self.nodes) % 3) * 60)
        node.place(x=x_pos, y=y_pos)

        lbl = ctk.CTkLabel(node, text=tool_name, font=ctk.CTkFont(family="Consolas", size=11, weight="bold"), text_color=ACCENT_CYAN)
        lbl.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkFrame(node, width=6, height=6, corner_radius=3, fg_color=TEXT_DIM).place(relx=0, rely=0.5, anchor="center")
        ctk.CTkFrame(node, width=6, height=6, corner_radius=3, fg_color=ACCENT_GREEN).place(relx=1, rely=0.5, anchor="center")

        node_data = {
            'frame': node,
            'name': tool_name,
            'params': "",
            'user_description': user_desc,
            'options': []
        }
        self.nodes.append(node_data)

        for item in [node, lbl]:
            item.bind("<Button-1>", lambda e, n=node_data: self.on_node_press(e, n))
            item.bind("<B1-Motion>", lambda e, n=node_data: self.on_node_drag(e, n))

        self.draw_connections()
        self.after_idle(self.draw_connections)
        return True

    # เริ่มลาก node
    # หน้าที่: เก็บ node ที่เลือกและตำแหน่งเริ่มลากจาก mouse event
    # ที่มา: pages/pipeline.py::PipelinePage._append_tool_node (เรียกตรง)
    # ที่มา: pages/pipeline.py::PipelinePage.load_saved_pipeline_to_canvas (เรียกตรง)
    # Input: self (PipelinePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: event (tkinter.Event) — Tk/TkDND ส่งมาจาก event binding; บางจุดเรียกตรงโดยไม่ส่ง event
    # Input: node_data (dict[str, Any]) — dictionary ที่ event binding จับไว้ตอนสร้างการ์ดบน canvas
    def on_node_press(self, event, node_data):
        self.current_node = node_data
        node_data['drag_data'] = {
            'x': event.x,
            'y': event.y
        }
        node_data['frame'].lift()

    # ลาก node
    # หน้าที่: ย้าย node ตาม mouse event แล้วเรียงลำดับและวาดเส้นใหม่เมื่ออนุญาตให้แก้ canvas
    # ที่มา: pages/pipeline.py::PipelinePage._append_tool_node (เรียกตรง)
    # ที่มา: pages/pipeline.py::PipelinePage.load_saved_pipeline_to_canvas (เรียกตรง)
    # Input: self (PipelinePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: event (tkinter.Event) — Tk/TkDND ส่งมาจาก event binding; บางจุดเรียกตรงโดยไม่ส่ง event
    # Input: node_data (dict[str, Any]) — dictionary ที่ event binding จับไว้ตอนสร้างการ์ดบน canvas
    def on_node_drag(self, event, node_data):
        if self.pipeline_mode == "Step" or self._pipeline_running or self.active_runs:
            return
        if 'drag_data' not in node_data:
            return

        deltax = event.x - node_data['drag_data']['x']
        deltay = event.y - node_data['drag_data']['y']

        new_x = node_data['frame'].winfo_x() + deltax
        new_y = node_data['frame'].winfo_y() + deltay

        node_data['frame'].place(x=new_x, y=new_y)
        self.reorder_nodes_by_position()
        self.draw_connections()

    # เรียง self.nodes ใหม่ตามตำแหน่ง x จริงบน canvas
    # เพื่อให้ลำดับที่ผู้ใช้ "เห็น" (ซ้าย -> ขวา) ตรงกับลำดับที่ Run All จะรันจริงเสมอ
    # หน้าที่: เรียง self.nodes ตามตำแหน่ง x เพื่อให้ลำดับรันตรงกับที่มองเห็น
    # ที่มา: pages/pipeline.py::PipelinePage.on_node_drag (เรียกตรง)
    # Input: self (PipelinePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def reorder_nodes_by_position(self):
        self.set_completed_recipe(None)
        self.nodes.sort(key=lambda n: n['frame'].winfo_x())

    

    # วาดเส้นเชื่อมระหว่าง node
    # หน้าที่: วาดเส้นเชื่อมระหว่าง nodes และสลับ placeholder เมื่อ canvas ว่าง
    # ที่มา: pages/pipeline.py::PipelinePage.set_pipeline_mode (เรียกตรง)
    # ที่มา: pages/pipeline.py::PipelinePage.set_pipeline_mode (อ้างอิง/callback)
    # ที่มา: pages/pipeline.py::PipelinePage._append_tool_node (เรียกตรง)
    # ที่มาเพิ่มเติม: อีก 5 จุดเรียก/อ้างอิงในโปรเจกต์
    # Input: self (PipelinePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def draw_connections(self):
        if self.nodes:
            self.placeholder.place_forget()
        else:
            self.placeholder.place(relx=0.5, rely=0.5, anchor="center")
        self.line_canvas.delete("line")
        if len(self.nodes) < 2: return

        for i in range(len(self.nodes) - 1):
            n1 = self.nodes[i]['frame']
            n2 = self.nodes[i+1]['frame']

            x1 = n1.winfo_x() + n1.winfo_width()
            y1 = n1.winfo_y() + (n1.winfo_height() / 2)
            x2 = n2.winfo_x()
            y2 = n2.winfo_y() + (n2.winfo_height() / 2)

            if x1 < 10 or x2 < 10: continue

            dist = abs(x2 - x1) / 2
            self.line_canvas.create_line(
                x1, y1, x1 + dist, y1, x2 - dist, y2, x2, y2,
                fill=ACCENT_CYAN, width=2, smooth=True, tags="line", arrow=tk.LAST
            )
    
    # รัน pipeline ทั้งหมด
    # หน้าที่: ตรวจว่า widget ของหน้ายังอยู่โดยรองรับ TclError ระหว่างปิดแอป
    # ที่มา: pages/pipeline.py::PipelinePage.run_pipeline (เรียกตรง)
    # ที่มา: pages/pipeline.py::PipelinePage._run_step_analysis (เรียกตรง)
    # Input: self (PipelinePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def _page_exists(self):
        try:
            return bool(self.winfo_exists())
        except tk.TclError:
            # Closing the application also destroys the Tcl widget hierarchy.
            return False

    # หน้าที่: ตรวจความพร้อม ตั้งสถานะรัน และ dispatch ไป runner ของโหมด Auto/Step
    # ที่มา: pages/pipeline.py::PipelinePage.__init__ (อ้างอิง/callback)
    # Input: self (PipelinePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def run_pipeline(self):
        if self.canvas_busy():
            return
        self.set_completed_recipe(None)
        for node in self.nodes:
            node.pop("_successful_step", None)
        self._pipeline_running = True
        self._history_group_id = uuid.uuid4().hex
        self.mode_btn.configure(state="disabled")
        self.run_btn.configure(state="disabled")
        try:
            if self.pipeline_mode == "Step":
                self._run_step_analysis()
            else:
                self._run_pipeline_steps()
        finally:
            self._pipeline_running = False
            if self._page_exists():
                self.mode_btn.configure(state="normal")
                self.run_btn.configure(state="normal")

    # หน้าที่: รัน exploration ทีละขั้น รับ decision และส่งผลไป tool ถัดไปที่ผู้ใช้เลือก
    # ที่มา: pages/pipeline.py::PipelinePage.run_pipeline (เรียกตรง)
    # Input: self (PipelinePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def _run_step_analysis(self):
        if not self.nodes:
            messagebox.showwarning("No tool selected", "Select a tool before clicking Run Step.", parent=self)
            return
        # Running again starts at the first tool, not at stale downstream results.
        for node in self.nodes[1:]:
            node['frame'].destroy()
        self.nodes[:] = self.nodes[:1]
        self.node_count = 1
        self.draw_connections()
        self.cleanup_pipeline_artifacts()
        self.run_logs = []
        current_data = b""
        while True:
            node = self.nodes[-1]
            decision = self.open_step_window(
                node, current_data, current_data, self.run_logs, False,
                step_index=len(self.nodes), step_mode=True,
            )
            if not self._page_exists():
                return
            if decision is None:
                return
            self.run_logs.append(dict(tool=node['name'], output=decision['output'], files=decision['files'],
                                      history_id=decision.get('history_id')))
            next_tool = decision['next_tool']
            if next_tool is None:
                self.set_completed_recipe(completed_steps(self.nodes))
                return
            current_data = decision['output']
            self._append_tool_node(next_tool)

    # หน้าที่: วน nodes ตามลำดับ เปิดหน้าต่างแต่ละขั้น และส่ง output ไปขั้นถัดไป
    # ที่มา: pages/pipeline.py::PipelinePage.run_pipeline (เรียกตรง)
    # Input: self (PipelinePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def _run_pipeline_steps(self):
        if not self.nodes:
            return

    # ลบ artifact จาก run ก่อนหน้า
        self.cleanup_pipeline_artifacts()

        current_data = b""
        self.run_logs = [] # เอา output ของตัวก่อน → input ตัวถัดไป

        for i, node in enumerate(self.nodes):
            tool = node["name"]
            is_last = (i == len(self.nodes) - 1)

            output = self.open_step_window(
                node,
                current_data,
                current_data,
                self.run_logs,
                is_last,
                step_index=i + 1,
                total_steps=len(self.nodes)
            )

            if output is None:
                return

            self.run_logs.append({
                "tool": tool,
                "output": output,
                "history_id": getattr(self, '_last_history_id', None),
            })

            current_data = output

        self.set_completed_recipe(completed_steps(self.nodes))

    # ล้าง pipeline
    # หน้าที่: ล้าง nodes, input และ artifacts ของ workspace เมื่อไม่ได้กำลังรัน
    # ที่มา: pages/pipeline.py::PipelinePage.load_template (เรียกตรง)
    # ที่มา: pages/pipeline.py::PipelinePage.__init__ (อ้างอิง/callback)
    # ที่มา: pages/pipeline.py::PipelinePage.add_tool_node (เรียกตรง)
    # ที่มาเพิ่มเติม: อีก 2 จุดเรียก/อ้างอิงในโปรเจกต์
    # Input: self (PipelinePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def clear_pipeline(self):
        if self.canvas_busy():
            return
        self.set_completed_recipe(None)
        print("Clearing pipeline...")
        for node in self.nodes:
            node['frame'].destroy()
        self.nodes.clear()
        self.node_count = 0
        self.run_logs = []
        self.draw_connections()
        self.cleanup_pipeline_artifacts()
        # P0.4B
        self.original_file_path = None

    # สร้างไฟล์ temp จาก data
    # หน้าที่: เขียน bytes ลงไฟล์ชั่วคราวแล้วคืน path สำหรับส่งต่อ
    # ที่มา: helper ของหน้านี้สำหรับผู้เรียกหรือ callback; ไม่มีจุดเรียกตรงใน flow ปัจจุบันที่ตรวจพบ
    # Input: self (PipelinePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: data (bytes) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def write_temp_file(self, data):
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.write(data)
        tmp.close()
        return tmp.name

    # เปิด popup ของแต่ละ step
    # หน้าที่: เปิดหน้าต่างตั้งค่า/รันหนึ่งขั้น พร้อม input, options, preview, output และการส่งต่อ
    # ที่มา: pages/pipeline.py::PipelinePage._run_step_analysis (เรียกตรง)
    # ที่มา: pages/pipeline.py::PipelinePage._run_pipeline_steps (เรียกตรง)
    # Input: self (PipelinePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: node (dict[str, Any]) — node ใน self.nodes ที่ runner เลือกมาประมวลผล
    # Input: previous_output (bytes | Path | None) — current_data จาก runner: output/Path ของขั้นก่อนหน้า หรือ bytes ว่างในขั้นแรก
    # Input: original_data (bytes | Path | None) — runner ส่ง current_data เช่นเดียวกับ previous_output; ไฟล์ต้นฉบับจริงอ่านผ่าน get_original_file
    # Input: logs (list[dict[str, Any]]) — self.run_logs ที่ runner สะสมจากขั้นตอนก่อนหน้า
    # Input: is_last (bool) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: step_index (int) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: total_steps (int) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: step_mode (bool) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # อ่านภายใน: input_entry ผ่าน .get() — str จากช่องกรอก หรือชนิดที่ Tk Variable กำหนด
    def open_step_window(self, node, previous_output, original_data, logs, is_last, step_index=1, total_steps=1, step_mode=False):

        tool_name = node["name"]
        saved_settings = node.get("run_settings", {})
        routing = {"source": saved_settings.get(
            "input_source", "previous" if step_index > 1 else "manual"), "value": ""}
        history_group = getattr(self, '_history_group_id', None) if self._pipeline_running else None
        history_group = history_group or uuid.uuid4().hex
        input_source = {'text': None, 'id': None}
        history_tags = {}
        # A selected output file is distinct from stdout containing a path.
        forwarded_file = previous_output if isinstance(previous_output, Path) else None
        if forwarded_file is not None:
            previous_output = str(forwarded_file).encode("utf-8")

        win = ctk.CTkToplevel(self)
        step_label = f"Step {step_index}" if step_mode else f"Step {step_index}/{total_steps}"
        win.title(f"{step_label} — {tool_name}")
        fit_window(win, "1200x780")
        win.attributes("-topmost", True)
        win.configure(fg_color=BG_COLOR)

        # ---------------- แถบ Progress (Step X / N) ----------------
        progress_header = ctk.CTkFrame(win, fg_color=PANEL_COLOR, corner_radius=8)
        progress_header.pack(fill="x", padx=10, pady=(10, 0))

        ctk.CTkLabel(
            progress_header,
            text=f"{step_label.upper()}  ·  {tool_name}",
            font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
            text_color=ACCENT_CYAN
        ).pack(side="left", padx=15, pady=10)

        progress_bar = ctk.CTkProgressBar(
            progress_header, width=220, progress_color=ACCENT_GREEN, fg_color=INPUT_BG
        )
        progress_bar.pack(side="right", padx=15, pady=10)
        progress_bar.set(0 if step_mode else (step_index / total_steps if total_steps else 1))
        if step_mode:
            progress_bar.pack_forget()  # The number of exploration steps is not known yet.

        container = ctk.CTkFrame(win, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # ---------------- LEFT PANEL ----------------
        left = ctk.CTkFrame(container, width=520, fg_color=PANEL_COLOR, border_width=1, border_color=BORDER_COLOR)
        left.pack(side="left", fill="both", expand=True, padx=(0, 5))

        ctk.CTkLabel(
            left, text="PIPELINE OUTPUT HISTORY",
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"), text_color=ACCENT_CYAN
        ).pack(anchor="w", padx=10, pady=(10, 0))

        # Allocate controls first, then let history use the remaining height.
        output_footer = ctk.CTkFrame(left, fg_color="transparent")
        output_footer.pack(side="bottom", fill="x")

        output_box = ctk.CTkTextbox(
            left, fg_color=INPUT_BG, border_width=1, border_color=BORDER_COLOR,
            text_color=ACCENT_GREEN, font=("Consolas", 12)
        )
        output_box.pack(fill="both", expand=True, padx=10, pady=10)

        # หน้าที่: หา History ID ที่สัมพันธ์กับข้อความ input/output ที่เลือก
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window.send_selected_to_input (เรียกตรง)
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window.send_selected_to_hashing (เรียกตรง)
        # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
        # Closure: history_tags (dict) — รับจาก scope PipelinePage.open_step_window
        # Closure: output_box (ctk.CTkTextbox) — รับจาก scope PipelinePage.open_step_window
        # Closure: result (dict) — รับจาก scope PipelinePage.open_step_window
        def selected_history_id():
            try:
                start, end = output_box.index('sel.first'), output_box.index('sel.last')
            except tk.TclError:
                return result.get('history_id')
            for tag, event_id in history_tags.items():
                ranges = output_box.tag_ranges(tag)
                if len(ranges) == 2 and output_box.compare(start, '>=', ranges[0]) and output_box.compare(end, '<=', ranges[1]):
                    return event_id
            return None

        # หน้าที่: นำข้อความที่เลือกไปใส่ช่อง input ของขั้นตอนปัจจุบัน
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window (อ้างอิง/callback)
        # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
        # Closure: input_entry (ctk.CTkEntry) — รับจาก scope PipelinePage.open_step_window
        # Closure: input_source (dict) — รับจาก scope PipelinePage.open_step_window
        # Closure: output_box (ctk.CTkTextbox) — รับจาก scope PipelinePage.open_step_window
        # อ่านภายใน: output_box ผ่าน .get() — str จากช่องกรอก หรือชนิดที่ Tk Variable กำหนด
        def send_selected_to_input():
            try:
                selected = output_box.get("sel.first", "sel.last")
                source_id = selected_history_id()
                input_entry.delete(0, "end")
                input_entry.insert(0, selected.strip())
                input_source.update(text=selected.strip(), id=source_id)
            except tk.TclError:
                pass

        # หน้าที่: คืนข้อความที่เลือก หรือข้อความ output เมื่อไม่มี selection
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window.send_selected_to_gemini (เรียกตรง)
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window.send_selected_to_hashing (เรียกตรง)
        # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
        # Closure: output_box (ctk.CTkTextbox) — รับจาก scope PipelinePage.open_step_window
        # Closure: result (dict) — รับจาก scope PipelinePage.open_step_window
        # Closure: win (ctk.CTkToplevel) — รับจาก scope PipelinePage.open_step_window
        # อ่านภายใน: output_box ผ่าน .get() — str จากช่องกรอก หรือชนิดที่ Tk Variable กำหนด
        def get_selected_or_output_text():
            # ถ้าผู้ใช้ select ข้อความไว้ ใช้ส่วนที่ select
            # ถ้าไม่ได้ select อะไรเลย ใช้ output ล่าสุดของ step นี้แทน (สะดวกกว่าปล่อยว่าง)
            try:
                return output_box.get("sel.first", "sel.last").strip()
            except Exception:
                pass
            if result["output"] is not None:
                if isinstance(result["output"], Path):
                    messagebox.showinfo('Select output',
                        'Large output is stored in a file. Select text from the preview, or open View Full Output.', parent=win)
                    return ""
                try:
                    return result["output"].decode(errors="ignore").strip()
                except Exception:
                    return str(result["output"]).strip()
            return ""

        # หน้าที่: ส่งข้อความจากขั้นตอนปัจจุบันไปหน้า Gemini
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window (อ้างอิง/callback)
        # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
        # Closure: self (PipelinePage) — รับจาก scope PipelinePage.open_step_window
        def send_selected_to_gemini():
            text = get_selected_or_output_text()
            if text and hasattr(self.app_root, "send_to_gemini"):
                self.app_root.send_to_gemini(text)

        # หน้าที่: ส่งข้อความจากขั้นตอนปัจจุบันไป Data Hashing พร้อม History ต้นทาง
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window (อ้างอิง/callback)
        # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
        # Closure: self (PipelinePage) — รับจาก scope PipelinePage.open_step_window
        def send_selected_to_hashing():
            text = get_selected_or_output_text()
            if text and hasattr(self.app_root, "send_to_hashing"):
                source_id = selected_history_id()
                if source_id:
                    self.app_root.send_to_hashing(text, source_history_id=source_id)
                else:
                    self.app_root.send_to_hashing(text)

        context_menu = tk.Menu(output_box, tearoff=0)
        context_menu.add_command(
            label="Send to Input",
            command=send_selected_to_input
        )
        context_menu.add_separator()
        context_menu.add_command(
            label="Send to Gemini",
            command=send_selected_to_gemini
        )
        context_menu.add_command(
            label="Send to Data Hashing",
            command=send_selected_to_hashing
        )

        # หน้าที่: เลือกเมนูคลิกขวาตาม widget ที่รับ event และเก็บข้อความที่เลือก
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window (อ้างอิง/callback)
        # Input: event (tkinter.Event) — Tk/TkDND ส่งมาจาก event binding; บางจุดเรียกตรงโดยไม่ส่ง event
        # Closure: context_menu (tk.Menu) — รับจาก scope PipelinePage.open_step_window
        def show_context_menu(event):
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()

        output_box.bind("<Button-3>", show_context_menu)

        result = {"output": None, "run": None, "selected_file": None, "decision": None, "history_id": None}

        continuation_panel = ctk.CTkFrame(output_footer, fg_color=CARD_COLOR)
        save_panel = ctk.CTkFrame(output_footer, fg_color=CARD_COLOR)
        ctk.CTkLabel(save_panel, text="✓ Pipeline complete", text_color=ACCENT_GREEN).pack(
            side="left", padx=10, pady=10)
        ctk.CTkButton(
            save_panel, text="Save Pipeline", fg_color=ACCENT_CYAN, text_color="black",
            command=lambda: self.open_save_pipeline(completed_steps(self.nodes), parent=win),
        ).pack(side="right", padx=10, pady=10)

        output_box.insert("end", ">>> original input\n")

        if isinstance(original_data, Path):
            preview = f"[Selected file] {original_data}"
        elif original_data:
            preview = original_data[:2000].decode(errors="ignore")
        else:
            preview = "[No file input]"

        output_box.insert("end", preview + "\n")

        for log in logs[-8:]:
            tool = log["tool"]
            out = log["output"]

            if isinstance(out, bytes):
                out = out[:16384].decode(errors="ignore")

            start = output_box.index('end-1c')
            output_box.insert("end", f"\n>>> {tool}\n")
            output_box.insert("end", str(out) + "\n")
            if log.get('history_id'):
                tag = 'history_' + log['history_id']
                output_box.tag_add(tag, start, 'end-1c')
                history_tags[tag] = log['history_id']

        file_selection = tk.StringVar(value="")
        file_panel = ctk.CTkFrame(output_footer, fg_color=CARD_COLOR)
        file_status = ctk.CTkLabel(
            file_panel, text="", text_color=ACCENT_GREEN, wraplength=430, justify="left",
        )
        file_status.pack(anchor="w", padx=10, pady=(5, 0))
        # Bound the picker so its scrollbar's requested height cannot squeeze
        # history down to a single line when Step continuation controls appear.
        file_list_area = ctk.CTkFrame(file_panel, height=110, fg_color="transparent")
        file_list_area.pack(fill="x", padx=10, pady=5)
        file_list_area.pack_propagate(False)
        file_list = ctk.CTkScrollableFrame(file_list_area, height=90, fg_color=INPUT_BG)
        file_list.pack(fill="both", expand=True)
        file_choices = {}

        # หน้าที่: แสดงรายละเอียดของไฟล์ผลลัพธ์ที่เลือกในรายการ
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window.browse_result_file (เรียกตรง)
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window.add_result_file (อ้างอิง/callback)
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window.show_result_panel (อ้างอิง/callback)
        # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
        # Closure: file_choices (dict) — รับจาก scope PipelinePage.open_step_window
        # Closure: file_selection (tk.StringVar) — รับจาก scope PipelinePage.open_step_window
        # Closure: file_status (ctk.CTkLabel) — รับจาก scope PipelinePage.open_step_window
        # Closure: result (dict) — รับจาก scope PipelinePage.open_step_window
        def show_selected_file():
            selected = file_choices.get(file_selection.get())
            result["selected_file"] = selected
            file_status.configure(text=(
                f"Forward file: {selected}" if selected else "Forward stdout"
            ))

        # หน้าที่: ตรวจและเพิ่ม path ในรายการไฟล์ผลลัพธ์ที่ใช้ส่งต่อได้
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window.browse_result_file (เรียกตรง)
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window.show_result (เรียกตรง)
        # Input: path (str | PathLike[str]) — path จากตัวเลือกไฟล์/config ที่จุดเรียกส่งมา หรือ default เมื่อไม่ระบุ
        # Closure: file_choices (dict) — รับจาก scope PipelinePage.open_step_window
        # Closure: file_list (ctk.CTkScrollableFrame) — รับจาก scope PipelinePage.open_step_window
        # Closure: file_selection (tk.StringVar) — รับจาก scope PipelinePage.open_step_window
        # Closure: file_status (ctk.CTkLabel) — รับจาก scope PipelinePage.open_step_window
        def add_result_file(path):
            path = Path(path).absolute()
            try:
                size = path.stat().st_size
                if not path.is_file():
                    raise ValueError("Please select a file.")
            except (OSError, ValueError) as error:
                file_status.configure(text=f"Cannot read file: {error}")
                return None
            key = str(path)
            if key not in file_choices:
                file_choices[key] = path
                ctk.CTkRadioButton(
                    file_list, text=f"{path.name} ({size:,} bytes)",
                    variable=file_selection, value=key, command=show_selected_file,
                    text_color="white", fg_color=ACCENT_CYAN,
                ).pack(anchor="w", padx=5, pady=3)
            return key

        # หน้าที่: ให้ผู้ใช้เลือกไฟล์ผลลัพธ์เพิ่มเองผ่าน file dialog
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window (อ้างอิง/callback)
        # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
        # Closure: file_selection (tk.StringVar) — รับจาก scope PipelinePage.open_step_window
        # Closure: result (dict) — รับจาก scope PipelinePage.open_step_window
        # Closure: self (PipelinePage) — รับจาก scope PipelinePage.open_step_window
        # Closure: win (ctk.CTkToplevel) — รับจาก scope PipelinePage.open_step_window
        def browse_result_file():
            if result["run"] is None or not result["run"].succeeded:
                return
            win.attributes("-topmost", False)
            try:
                path = filedialog.askopenfilename(parent=win, title="Select an output file to forward")
            finally:
                win.attributes("-topmost", True)
            if path:
                key = add_result_file(path)
                if key:
                    show_result_panel()
                    file_selection.set(key)
                    show_selected_file()
                    history_hooks.attach_file(self.app_root, result.get('history_id'), path)

        browse_result_button = ctk.CTkButton(
            output_footer, text="Browse result file", command=browse_result_file,
            fg_color=BORDER_COLOR, text_color=ACCENT_CYAN,
        )

        # หน้าที่: อัปเดตส่วนแสดง stdout/stderr และไฟล์ที่ค้นพบจากผลรัน
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window.browse_result_file (เรียกตรง)
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window.show_result (เรียกตรง)
        # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
        # Closure: browse_result_button (ctk.CTkButton) — รับจาก scope PipelinePage.open_step_window
        # Closure: file_list (ctk.CTkScrollableFrame) — รับจาก scope PipelinePage.open_step_window
        # Closure: file_panel (ctk.CTkFrame) — รับจาก scope PipelinePage.open_step_window
        # Closure: file_selection (tk.StringVar) — รับจาก scope PipelinePage.open_step_window
        # Closure: result (dict) — รับจาก scope PipelinePage.open_step_window
        def show_result_panel():
            # The list is useful only when there is an actual file to select.
            browse_result_button.pack_forget()
            file_panel.pack(fill="x", padx=10, pady=5)
            browse_result_button.pack(pady=(0, 5))
            if result["output"] and not any(
                isinstance(widget, ctk.CTkRadioButton) and widget.cget("value") == "stdout"
                for widget in file_list.winfo_children()
            ):
                ctk.CTkRadioButton(
                    file_list, text="Forward stdout", variable=file_selection,
                    value="stdout", command=show_selected_file,
                    text_color="white", fg_color=ACCENT_CYAN,
                ).pack(anchor="w", padx=5, pady=3)

        # หน้าที่: เลือก destination แล้วบันทึก output เต็มโดยคง bytes ต้นฉบับ
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window (อ้างอิง/callback)
        # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
        # Closure: result (dict) — รับจาก scope PipelinePage.open_step_window
        # Closure: self (PipelinePage) — รับจาก scope PipelinePage.open_step_window
        # Closure: win (ctk.CTkToplevel) — รับจาก scope PipelinePage.open_step_window
        def save_output():
            if result["output"] is None:
                return
            win.attributes("-topmost", False)
            path = filedialog.asksaveasfilename(parent=win, defaultextension=".txt")
            win.attributes("-topmost", True)

            if path:
                event_id = result.get('history_id')
                source = result["output"]
                save_async(win, source, path,
                    lambda: history_hooks.attach_file(self.app_root, event_id, path))

        ctk.CTkButton(
            output_footer, text="Save Output as File", command=save_output,
            fg_color="transparent", border_width=1, border_color=ACCENT_CYAN,
            text_color=ACCENT_CYAN, hover_color=CARD_COLOR
        ).pack(pady=5)

        full_buttons = ctk.CTkFrame(output_footer, fg_color='transparent')
        # หน้าที่: เปิด viewer ของ stdout หรือ stderr ฉบับเต็มตาม stream ที่เลือก
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window (เรียกตรง)
        # Input: which (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
        # Closure: result (dict) — รับจาก scope PipelinePage.open_step_window
        # Closure: win (ctk.CTkToplevel) — รับจาก scope PipelinePage.open_step_window
        def view_stream(which):
            run = result.get('run')
            path = getattr(run, which + '_file', None)
            if path:
                open_text_view(win, path)
        ctk.CTkButton(full_buttons, text='View Full Output', width=145,
                      command=lambda: view_stream('stdout')).pack(side='left', padx=5)
        ctk.CTkButton(full_buttons, text='View Full Error', width=145,
                      command=lambda: view_stream('stderr')).pack(side='left', padx=5)

        # ---------------- RIGHT PANEL ----------------
        right_shell = ctk.CTkFrame(container, width=380, fg_color=PANEL_COLOR, border_width=1, border_color=BORDER_COLOR)
        right_shell.pack(side="left", fill="y", padx=(5, 0))
        run_controls = ctk.CTkFrame(right_shell, fg_color="transparent")
        run_controls.pack(side="bottom", fill="x", pady=10)
        right = ctk.CTkScrollableFrame(right_shell, width=340, fg_color="transparent")
        right.pack(fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(
            right, text=tool_name, font=ctk.CTkFont(family="Consolas", size=16, weight="bold"),
            text_color=ACCENT_CYAN
        ).pack(pady=10)

        # -------- Input --------
        ctk.CTkLabel(right, text="Input", text_color=TEXT_DIM).pack(anchor="w", padx=20)

        input_frame = ctk.CTkFrame(right, fg_color="transparent")
        input_frame.pack(fill="x", padx=20, pady=5)

        input_var = tk.StringVar(master=win)
        input_entry = ctk.CTkEntry(input_frame, textvariable=input_var, fg_color=INPUT_BG, border_color=BORDER_COLOR, text_color="white")
        input_entry.pack(side="left", fill="x", expand=True)

        # หน้าที่: เลือกไฟล์ input ของขั้นตอนแล้วอัปเดต Entry/preview
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window (อ้างอิง/callback)
        # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
        # Closure: input_entry (ctk.CTkEntry) — รับจาก scope PipelinePage.open_step_window
        # Closure: output_box (ctk.CTkTextbox) — รับจาก scope PipelinePage.open_step_window
        # Closure: self (PipelinePage) — รับจาก scope PipelinePage.open_step_window
        # Closure: win (ctk.CTkToplevel) — รับจาก scope PipelinePage.open_step_window
        def browse_file():
            win.attributes("-topmost", False)
            path = filedialog.askopenfilename(parent=win)
            win.attributes("-topmost", True)

            if path:
                self.set_step_input_path(
                    input_entry,
                    path
                )

                # P0.4B:
                # ไฟล์แรกที่ Browse จะเป็น Original File
                if not self.get_original_file():
                    self.set_original_file(path)

                    output_box.insert(
                        "end",
                        "\n>>> ORIGINAL FILE SET\n"
                        f"[+] {path}\n"
                    )

                routing.update(source="manual", value=input_entry.get())
                update_preview()

        ctk.CTkButton(
            input_frame, text="Browse", width=80, command=browse_file,
            fg_color=BORDER_COLOR, text_color=ACCENT_CYAN, hover_color=CARD_COLOR
        ).pack(side="right", padx=5)

        if tool_name in self.engine.file_tools:

            resolved = resolve_file_input(
                previous_output
            )

            mode = resolved["mode"]

            # --------------------------------------------------------
            # CASE 1:
            # output ก่อนหน้าคือ file path จริง
            #
            # flow เดิมยังทำงาน
            # --------------------------------------------------------

            if mode == "existing_path":

                input_entry.insert(
                    0,
                    resolved["path"]
                )

                output_box.insert(
                    "end",
                    "\n>>> INPUT ROUTING\n"
                )

                output_box.insert(
                    "end",
                    "[+] Existing file path detected\n"
                )

                output_box.insert(
                    "end",
                    f"[+] Path: {resolved['path']}\n"
                )

            # --------------------------------------------------------
            # CASE 2:
            # output ก่อนหน้าเป็น binary
            #
            # Artifact Bridge
            # --------------------------------------------------------

            elif mode == "artifact":

                artifact_path = resolved["path"]

                self.register_temp_artifact(
                    artifact_path
                )

                input_entry.insert(
                    0,
                    artifact_path
                )

                output_box.insert(
                    "end",
                    "\n>>> UNIT ARTIFACT BRIDGE\n"
                )

                output_box.insert(
                    "end",
                    f"[+] Type : {resolved['type']}\n"
                )

                output_box.insert(
                    "end",
                    f"[+] Size : {resolved['size']:,} bytes\n"
                )

                output_box.insert(
                    "end",
                    f"[+] Temp : {artifact_path}\n"
                )

                magic = resolved.get("magic")

                if magic:

                    output_box.insert(
                        "end",
                        f"[+] Magic: {magic['magic']}\n"
                    )

                output_box.insert(
                    "end",
                    "[+] Binary output converted "
                    "to temporary file automatically\n"
                )

            # --------------------------------------------------------
            # CASE 3:
            # ไม่มี previous output
            # หรือ previous เป็น text ปกติ
            #
            # ไม่ทำอะไร
            # user Browse เองเหมือนเดิม
            # --------------------------------------------------------

            else:

                if previous_output:

                    output_box.insert(
                        "end",
                        "\n>>> INPUT ROUTING\n"
                    )

                    output_box.insert(
                        "end",
                        "[i] Previous output is text, "
                        "not a file path.\n"
                    )

                    output_box.insert(
                        "end",
                        "[i] Select a file manually "
                        "if this tool requires one.\n"
                    )

        # -------- Options --------
        ctk.CTkLabel(right, text="Options", text_color=TEXT_DIM).pack(anchor="w", padx=20)

        options_frame = ctk.CTkFrame(right, height=1, fg_color="transparent")
        options_frame.pack(fill="x", padx=20, pady=5)

        option_vars = []
        output_box.insert(
            "end",
            "[i] Select a file manually "
            "if this tool requires one.\n"
        )
                # ============================================================
        # P0.4B - ORIGINAL FILE ROUTING
        # ============================================================

        if tool_name in self.engine.file_tools:

            source_frame = ctk.CTkFrame(
                right,
                fg_color="transparent"
            )
            source_frame.pack(
                fill="x",
                padx=20,
                pady=(5, 10)
            )

            ctk.CTkLabel(
                source_frame,
                text="INPUT SOURCE",
                font=("Consolas", 11, "bold"),
                text_color=TEXT_DIM
            ).pack(anchor="w", pady=(0, 5))

            source_buttons = ctk.CTkFrame(
                source_frame,
                fg_color="transparent"
            )
            source_buttons.pack(fill="x")

            # ----------------------------------------------
            # เก็บ path ของ Previous ที่ Artifact Bridge
            # resolve ไว้แล้ว
            # ----------------------------------------------

            previous_file_path = None

            if mode in ("existing_path", "artifact"):
                previous_file_path = resolved.get("path")

            # ----------------------------------------------
            # PREVIOUS
            # ----------------------------------------------

            # หน้าที่: นำ output หรือไฟล์จากขั้นก่อนหน้ามาใช้เป็น input ของขั้นนี้
            # ที่มา: pages/pipeline.py::PipelinePage.open_step_window (อ้างอิง/callback)
            # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
            # Closure: input_entry (ctk.CTkEntry) — รับจาก scope PipelinePage.open_step_window
            # Closure: output_box (ctk.CTkTextbox) — รับจาก scope PipelinePage.open_step_window
            # Closure: previous_file_path (str | None) — รับจาก scope PipelinePage.open_step_window
            # Closure: self (PipelinePage) — รับจาก scope PipelinePage.open_step_window
            def use_previous():

                if not previous_file_path:
                    output_box.insert(
                        "end",
                        "\n[!] Previous output is not "
                        "a usable file.\n"
                    )
                    return

                self.set_step_input_path(
                    input_entry,
                    previous_file_path
                )
                routing.update(source="previous", value=input_entry.get())

                output_box.insert(
                    "end",
                    "\n>>> INPUT SOURCE: PREVIOUS\n"
                    f"[+] {previous_file_path}\n"
                )

                update_preview()

            # ----------------------------------------------
            # ORIGINAL
            # ----------------------------------------------

            # หน้าที่: ใช้ข้อมูลหรือ path ไฟล์ต้นฉบับเป็น input ของขั้นนี้
            # ที่มา: pages/pipeline.py::PipelinePage.open_step_window (อ้างอิง/callback)
            # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
            # Closure: input_entry (ctk.CTkEntry) — รับจาก scope PipelinePage.open_step_window
            # Closure: output_box (ctk.CTkTextbox) — รับจาก scope PipelinePage.open_step_window
            # Closure: self (PipelinePage) — รับจาก scope PipelinePage.open_step_window
            def use_original():

                original = self.get_original_file()

                if not original:
                    output_box.insert(
                        "end",
                        "\n[!] Original File has not "
                        "been selected yet.\n"
                    )
                    return

                self.set_step_input_path(
                    input_entry,
                    original
                )
                routing.update(source="original", value=input_entry.get())

                output_box.insert(
                    "end",
                    "\n>>> INPUT SOURCE: ORIGINAL\n"
                    f"[+] {original}\n"
                )

                update_preview()

            # ----------------------------------------------
            # SET ORIGINAL
            # ----------------------------------------------

            # หน้าที่: เลือกและตั้งไฟล์ต้นฉบับใหม่จากหน้าต่างขั้นตอน
            # ที่มา: pages/pipeline.py::PipelinePage.open_step_window (อ้างอิง/callback)
            # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
            # Closure: input_entry (ctk.CTkEntry) — รับจาก scope PipelinePage.open_step_window
            # Closure: original_status (ctk.CTkLabel) — รับจาก scope PipelinePage.open_step_window
            # Closure: output_box (ctk.CTkTextbox) — รับจาก scope PipelinePage.open_step_window
            # Closure: self (PipelinePage) — รับจาก scope PipelinePage.open_step_window
            # Closure: win (ctk.CTkToplevel) — รับจาก scope PipelinePage.open_step_window
            def set_new_original():

                win.attributes(
                    "-topmost",
                    False
                )

                path = filedialog.askopenfilename(
                    parent=win
                )

                win.attributes(
                    "-topmost",
                    True
                )

                if not path:
                    return

                self.set_original_file(
                    path,
                    force=True
                )

                self.set_step_input_path(
                    input_entry,
                    path
                )

                routing.update(source="original", value=input_entry.get())
                original_status.configure(
                    text=(
                        "ORIGINAL: "
                        + os.path.basename(path)
                    )
                )

                output_box.insert(
                    "end",
                    "\n>>> ORIGINAL FILE CHANGED\n"
                    f"[+] {path}\n"
                )

                update_preview()

            # ----------------------------------------------
            # Buttons
            # ----------------------------------------------

            ctk.CTkButton(
                source_buttons,
                text="PREVIOUS",
                width=90,
                height=28,
                command=use_previous,
                fg_color="transparent",
                border_width=1,
                border_color=ACCENT_PURPLE,
                text_color=ACCENT_PURPLE,
                hover_color=CARD_COLOR
            ).pack(
                side="left",
                padx=(0, 4)
            )

            ctk.CTkButton(
                source_buttons,
                text="ORIGINAL",
                width=90,
                height=28,
                command=use_original,
                fg_color="transparent",
                border_width=1,
                border_color=ACCENT_CYAN,
                text_color=ACCENT_CYAN,
                hover_color=CARD_COLOR
            ).pack(
                side="left",
                padx=4
            )

            ctk.CTkButton(
                source_buttons,
                text="SET",
                width=60,
                height=28,
                command=set_new_original,
                fg_color="transparent",
                border_width=1,
                border_color=ACCENT_GREEN,
                text_color=ACCENT_GREEN,
                hover_color=CARD_COLOR
            ).pack(
                side="left",
                padx=4
            )

            # ----------------------------------------------
            # Status
            # ----------------------------------------------

            original = self.get_original_file()

            original_status = ctk.CTkLabel(
                source_frame,
                text=(
                    "ORIGINAL: "
                    + (
                        os.path.basename(original)
                        if original
                        else "NONE"
                    )
                ),
                font=("Consolas", 10),
                text_color=TEXT_DIM
            )

            original_status.pack(
                anchor="w",
                pady=(5, 0)
            )

        # ---------------- แก้ไขบักการรวม Option ----------------
        # ป้องกันบักที่ Option ปรับแต่งไปลบ Option ดั้งเดิมของโปรแกรม
        custom_opts = node.get("options", [])
        default_opts = self.engine.tool_options.get(tool_name, [])
        tool_options = []
        seen_flags = set()
        for opt in default_opts + custom_opts:
            if opt["flag"] not in seen_flags:
                tool_options.append(opt)
                seen_flags.add(opt["flag"])
        # ----------------------------------------------------

        preview_ready = False

        # หน้าที่: อ่าน options ที่เลือกแล้วประกอบ argument tokens ของเครื่องมือ
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window.command_for (เรียกตรง)
        # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
        # Closure: node (dict[str, Any]) — รับจาก scope PipelinePage.open_step_window
        # Closure: option_vars (list) — รับจาก scope PipelinePage.open_step_window
        # Closure: self (PipelinePage) — รับจาก scope PipelinePage.open_step_window
        # Closure: switch_after_var (ctk.BooleanVar) — รับจาก scope PipelinePage.open_step_window
        # Closure: switch_before_var (ctk.BooleanVar) — รับจาก scope PipelinePage.open_step_window
        # อ่านภายใน: switch_before_var, switch_after_var ผ่าน .get() — str จากช่องกรอก หรือชนิดที่ Tk Variable กำหนด
        def option_arguments():
            params_list = self.engine.arguments(node.get("params", ""))
            if switch_before_var.get():
                params_list += self.engine.arguments(preview_before_args())
            for flag, var, opt_type in option_vars:
                if opt_type == "checkbox":
                    if var.get():
                        params_list += self.engine.arguments(flag)
                elif opt_type in ["text", "file"]:
                    val = var.get()
                    if val:
                        params_list += self.engine.arguments(flag) + [val]
            after = self.engine.arguments(preview_after_args()) if switch_after_var.get() else []
            return params_list, after

        # หน้าที่: รวม tool, options และ path input เป็น argument list ผ่าน engine
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window.update_preview (เรียกตรง)
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window.execute_tool (เรียกตรง)
        # Input: path (str | PathLike[str] | None) — path จากตัวเลือกไฟล์/config ที่จุดเรียกส่งมา หรือ default เมื่อไม่ระบุ
        # Closure: self (PipelinePage) — รับจาก scope PipelinePage.open_step_window
        # Closure: tool_name (str) — รับจาก scope PipelinePage.open_step_window
        def command_for(path=None):
            before, after = option_arguments()
            return self.engine.build_command(tool_name, before, path, after)

        # หน้าที่: อัปเดตข้อความคำสั่ง preview เมื่อค่าที่เกี่ยวข้องเปลี่ยน
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window (เรียกตรง)
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window.add_before_row (อ้างอิง/callback)
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window.add_before_row (เรียกตรง)
        # ที่มาเพิ่มเติม: อีก 13 จุดเรียก/อ้างอิงในโปรเจกต์
        # Input: *args (tuple[str, ...] (arguments ของ Tk variable trace)) — Tk trace_add ส่งชื่อ variable/index/operation เมื่อค่าเปลี่ยน
        # Closure: input_entry (ctk.CTkEntry) — รับจาก scope PipelinePage.open_step_window
        # Closure: preview_label (ctk.CTkLabel) — รับจาก scope PipelinePage.open_step_window
        # Closure: preview_ready (bool) — รับจาก scope PipelinePage.open_step_window
        # Closure: self (PipelinePage) — รับจาก scope PipelinePage.open_step_window
        # Closure: tool_name (str) — รับจาก scope PipelinePage.open_step_window
        # อ่านภายใน: input_entry ผ่าน .get() — str จากช่องกรอก หรือชนิดที่ Tk Variable กำหนด
        def update_preview(*args):
            if not preview_ready:
                return
            sync_successful_step()
            try:
                path = input_entry.get().strip() if tool_name in self.engine.file_tools else None
                preview = shlex.join(command_for(path))
                if tool_name in self.engine.text_tools:
                    # Compact display only: execution still sends text via stdin,
                    # never as shell code or an extra command-line argument.
                    text_input = input_entry.get()
                    if text_input:
                        preview += " " + text_input
                preview_label.configure(text=preview)
            except ValueError as error:
                preview_label.configure(text=f"Invalid arguments: {error}")

        saved_values = {(opt["flag"], opt["type"]): opt["value"]
                        for opt in saved_settings.get("option_values", [])}
        for opt in tool_options:
            flag = opt["flag"]
            desc = opt.get("description", "").strip()
            opt_type = opt["type"]

            # จัดรูปแบบใหม่: เอาวงเล็บออก และถ้าไม่มีคำอธิบายให้โชว์แค่ flag
            display_text = f"{flag}  {desc}" if desc else flag

            row = ctk.CTkFrame(options_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)

            if opt_type == "checkbox":
                var = tk.BooleanVar(value=saved_values.get((flag, opt_type), False))
                chk = ctk.CTkCheckBox(
                    row, text=display_text, variable=var, command=update_preview,
                    text_color="white", fg_color=ACCENT_CYAN, hover_color="#00CCCC",
                    checkmark_color="black", border_color=BORDER_COLOR
                )
                chk.pack(anchor="w")
                option_vars.append((flag, var, "checkbox"))

            elif opt_type in ["text", "file"]:
                ctk.CTkLabel(row, text=f"{display_text}:", text_color=TEXT_DIM).pack(side="left", padx=(0, 5))
                var = tk.StringVar(value=saved_values.get((flag, opt_type), ""))
                var.trace_add("write", update_preview)
                ent = ctk.CTkEntry(row, textvariable=var, width=120, fg_color=INPUT_BG, border_color=BORDER_COLOR, text_color="white")
                ent.pack(side="left", fill="x", expand=True)
                option_vars.append((flag, var, opt_type))

        # =================================================================
        # -------- Advanced Options (ยุบ/ขยาย) --------
        # เก็บ Manual Options (before/after) ไว้ในนี้เพื่อไม่ให้หน้าต่างรก
        # auto-ขยายให้เองถ้า tool ไม่มี default option เลย (เช่น openssl enc)
        # =================================================================
        advanced_frame = ctk.CTkFrame(right, fg_color="transparent")

        # หน้าที่: แสดงหรือซ่อนส่วนตั้งค่า arguments ขั้นสูง
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window (อ้างอิง/callback)
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window (เรียกตรง)
        # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
        # Closure: advanced_frame (ctk.CTkFrame) — รับจาก scope PipelinePage.open_step_window
        # Closure: advanced_toggle_btn (ctk.CTkButton) — รับจาก scope PipelinePage.open_step_window
        def toggle_advanced():
            if advanced_frame.winfo_ismapped():
                advanced_frame.pack_forget()
                advanced_toggle_btn.configure(text="▸ Advanced Options")
            else:
                advanced_frame.pack(fill="x", padx=20, pady=(0, 5))
                advanced_toggle_btn.configure(text="▾ Advanced Options")

        advanced_toggle_btn = ctk.CTkButton(
            right, text="▸ Advanced Options", command=toggle_advanced,
            fg_color="transparent", border_width=1, border_color=BORDER_COLOR,
            text_color=TEXT_DIM, hover_color=CARD_COLOR, anchor="w"
        )
        advanced_toggle_btn.pack(fill="x", padx=20, pady=(15, 0))

        # =================================================================
        # -------- สวิตช์และ Dynamic Rows (Before Input) --------
        # =================================================================
        switch_before_var = ctk.BooleanVar(value=saved_settings.get("before_enabled", False))
        before_container = ctk.CTkFrame(advanced_frame, fg_color="transparent")
        before_rows = []

        # หน้าที่: อ่านแถว options ก่อน input แล้วประกอบ tokens สำหรับ preview
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window.option_arguments (เรียกตรง)
        # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
        # Closure: before_rows (list) — รับจาก scope PipelinePage.open_step_window
        def preview_before_args():
            args = []
            for row in before_rows:
                f = row["flag"].get().strip()
                if f:
                    if row["type"] == "checkbox":
                        args.append(f)
                    else:
                        v = row["val"].get().strip()
                        if v:
                            args.append(f"{f} {shlex.quote(v)}")
                        else:
                            args.append(f)
            return " ".join(args)

        # หน้าที่: สร้างแถว option เพิ่มเติมในส่วน arguments ก่อน input
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window (เรียกตรง)
        # Input: opt_type (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
        # Closure: before_container (ctk.CTkFrame) — รับจาก scope PipelinePage.open_step_window
        # Closure: before_rows (list) — รับจาก scope PipelinePage.open_step_window
        def add_before_row(opt_type="checkbox"):
            row = ctk.CTkFrame(before_container, fg_color="transparent")
            row.pack(fill="x", pady=2)

            flag_var = tk.StringVar()
            flag_var.trace_add("write", update_preview)
            flag_entry = ctk.CTkEntry(row, width=70, placeholder_text="-n", fg_color=INPUT_BG, border_color=BORDER_COLOR, text_color="white")
            flag_entry.pack(side="left", padx=(0, 5))
            flag_entry.configure(textvariable=flag_var)

            val_var = tk.StringVar()
            if opt_type in ("text", "file"):
                val_var.trace_add("write", update_preview)
                val_entry = ctk.CTkEntry(row, placeholder_text="value", fg_color=INPUT_BG, border_color=BORDER_COLOR, text_color="white")
                val_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
                val_entry.configure(textvariable=val_var)
            else:
                lbl = ctk.CTkLabel(row, text="No Param", fg_color="#3498db", text_color="white", corner_radius=4, height=26)
                lbl.pack(side="left", fill="x", expand=True, padx=(0, 5))

            row_data = {"frame": row, "type": opt_type, "flag": flag_var, "val": val_var}
            before_rows.append(row_data)

            # หน้าที่: ลบแถว option ที่ closure จับไว้และอัปเดต preview
            # ที่มา: pages/pipeline.py::PipelinePage.open_step_window.add_before_row (อ้างอิง/callback)
            # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
            # Closure: row (ctk.CTkFrame) — รับจาก scope PipelinePage.open_step_window.add_before_row
            # Closure: row_data (dict) — รับจาก scope PipelinePage.open_step_window.add_before_row
            # Closure: before_rows (list) — รับจาก scope PipelinePage.open_step_window
            def delete_row():
                before_rows.remove(row_data)
                row.destroy()
                update_preview()

            ctk.CTkButton(row, text="X", width=28, fg_color=ALERT_RED, hover_color="#C0294B", text_color="white", command=delete_row).pack(side="right")
            update_preview()

        before_btn_frame = ctk.CTkFrame(before_container, fg_color="transparent")
        before_btn_frame.pack(fill="x", pady=(5, 5))
        ctk.CTkButton(before_btn_frame, text="+ No Param", width=90, height=24, fg_color="#3498db", hover_color="#2980b9", command=lambda: add_before_row("checkbox")).pack(side="left", padx=2)
        ctk.CTkButton(before_btn_frame, text="+ With Param", width=90, height=24, fg_color="#9b59b6", hover_color="#8e44ad", command=lambda: add_before_row("text")).pack(side="left", padx=2)

        # หน้าที่: แสดงหรือซ่อนส่วน arguments ก่อน input
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window (อ้างอิง/callback)
        # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
        # Closure: before_container (ctk.CTkFrame) — รับจาก scope PipelinePage.open_step_window
        # Closure: switch_before (ctk.CTkSwitch) — รับจาก scope PipelinePage.open_step_window
        # Closure: switch_before_var (ctk.BooleanVar) — รับจาก scope PipelinePage.open_step_window
        # อ่านภายใน: switch_before_var ผ่าน .get() — str จากช่องกรอก หรือชนิดที่ Tk Variable กำหนด
        def toggle_before():
            if switch_before_var.get():
                before_container.pack(after=switch_before, fill="x", pady=(0, 5))
            else:
                before_container.pack_forget()
            update_preview()

        switch_before = ctk.CTkSwitch(advanced_frame, text="Add Manual Options (Before Input)", variable=switch_before_var, command=toggle_before, progress_color=ACCENT_GREEN, text_color="white", button_color=TEXT_DIM)
        switch_before.pack(anchor="w", pady=(10, 0))

        # =================================================================
        # -------- สวิตช์และ Dynamic Rows (After Input) --------
        # =================================================================
        switch_after_var = ctk.BooleanVar(value=saved_settings.get("after_enabled", False))
        after_container = ctk.CTkFrame(advanced_frame, fg_color="transparent")
        after_rows = []

        # หน้าที่: อ่านแถว options หลัง input แล้วประกอบ tokens สำหรับ preview
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window.option_arguments (เรียกตรง)
        # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
        # Closure: after_rows (list) — รับจาก scope PipelinePage.open_step_window
        def preview_after_args():
            args = []
            for row in after_rows:
                f = row["flag"].get().strip()
                if f:
                    if row["type"] == "checkbox":
                        args.append(f)
                    else:
                        v = row["val"].get().strip()
                        if v:
                            args.append(f"{f} {shlex.quote(v)}")
                        else:
                            args.append(f)
            return " ".join(args)

        # หน้าที่: สร้างแถว option เพิ่มเติมในส่วน arguments หลัง input
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window (เรียกตรง)
        # Input: opt_type (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
        # Closure: after_container (ctk.CTkFrame) — รับจาก scope PipelinePage.open_step_window
        # Closure: after_rows (list) — รับจาก scope PipelinePage.open_step_window
        def add_after_row(opt_type="checkbox"):
            row = ctk.CTkFrame(after_container, fg_color="transparent")
            row.pack(fill="x", pady=2)

            flag_var = tk.StringVar()
            flag_var.trace_add("write", update_preview)
            flag_entry = ctk.CTkEntry(row, width=70, placeholder_text="-n", fg_color=INPUT_BG, border_color=BORDER_COLOR, text_color="white")
            flag_entry.pack(side="left", padx=(0, 5))
            flag_entry.configure(textvariable=flag_var)

            val_var = tk.StringVar()
            if opt_type in ("text", "file"):
                val_var.trace_add("write", update_preview)
                val_entry = ctk.CTkEntry(row, placeholder_text="value", fg_color=INPUT_BG, border_color=BORDER_COLOR, text_color="white")
                val_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
                val_entry.configure(textvariable=val_var)
            else:
                lbl = ctk.CTkLabel(row, text="No Param", fg_color="#3498db", text_color="white", corner_radius=4, height=26)
                lbl.pack(side="left", fill="x", expand=True, padx=(0, 5))

            row_data = {"frame": row, "type": opt_type, "flag": flag_var, "val": val_var}
            after_rows.append(row_data)

            # หน้าที่: ลบแถว option ที่ closure จับไว้และอัปเดต preview
            # ที่มา: pages/pipeline.py::PipelinePage.open_step_window.add_after_row (อ้างอิง/callback)
            # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
            # Closure: row (ctk.CTkFrame) — รับจาก scope PipelinePage.open_step_window.add_after_row
            # Closure: row_data (dict) — รับจาก scope PipelinePage.open_step_window.add_after_row
            # Closure: after_rows (list) — รับจาก scope PipelinePage.open_step_window
            def delete_row():
                after_rows.remove(row_data)
                row.destroy()
                update_preview()

            ctk.CTkButton(row, text="X", width=28, fg_color=ALERT_RED, hover_color="#C0294B", text_color="white", command=delete_row).pack(side="right")
            update_preview()

        after_btn_frame = ctk.CTkFrame(after_container, fg_color="transparent")
        after_btn_frame.pack(fill="x", pady=(5, 5))
        ctk.CTkButton(after_btn_frame, text="+ No Param", width=90, height=24, fg_color="#3498db", hover_color="#2980b9", command=lambda: add_after_row("checkbox")).pack(side="left", padx=2)
        ctk.CTkButton(after_btn_frame, text="+ With Param", width=90, height=24, fg_color="#9b59b6", hover_color="#8e44ad", command=lambda: add_after_row("text")).pack(side="left", padx=2)

        # หน้าที่: แสดงหรือซ่อนส่วน arguments หลัง input
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window (อ้างอิง/callback)
        # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
        # Closure: after_container (ctk.CTkFrame) — รับจาก scope PipelinePage.open_step_window
        # Closure: switch_after (ctk.CTkSwitch) — รับจาก scope PipelinePage.open_step_window
        # Closure: switch_after_var (ctk.BooleanVar) — รับจาก scope PipelinePage.open_step_window
        # อ่านภายใน: switch_after_var ผ่าน .get() — str จากช่องกรอก หรือชนิดที่ Tk Variable กำหนด
        def toggle_after():
            if switch_after_var.get():
                after_container.pack(after=switch_after, fill="x", pady=(0, 5))
            else:
                after_container.pack_forget()
            update_preview()

        switch_after = ctk.CTkSwitch(advanced_frame, text="Add Additional Arguments (After Input)", variable=switch_after_var, command=toggle_after, progress_color=ACCENT_GREEN, text_color="white", button_color=TEXT_DIM)
        switch_after.pack(anchor="w", pady=(10, 0))

        for side, rows, add_row in (
            ("before", before_rows, add_before_row), ("after", after_rows, add_after_row)
        ):
            for saved_row in saved_settings.get(side + "_rows", []):
                add_row(saved_row["type"])
                rows[-1]["flag"].set(saved_row["flag"])
                rows[-1]["val"].set(saved_row["value"])
        toggle_before()
        toggle_after()
        if not tool_options or switch_before_var.get() or switch_after_var.get():
            # tool นี้ไม่มี option สำเร็จรูปเลย (เช่น openssl enc) ต้องพึ่ง manual options
            # อย่างเดียว เลยเปิด Advanced ให้อัตโนมัติจะได้ไม่ต้องเดา
            toggle_advanced()

        # -------- Command Preview --------
        preview_header = ctk.CTkFrame(right, fg_color="transparent")
        preview_header.pack(fill="x", padx=20, pady=(15, 0))

        ctk.CTkLabel(preview_header, text="Command Preview", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT_DIM).pack(side="left")

        preview_label = ctk.CTkLabel(right, text=tool_name, text_color=ACCENT_GREEN, font=ctk.CTkFont(family="Consolas", size=13), wraplength=320)
        preview_label.pack(anchor="w", padx=20, pady=5)

        # A recipe stores a source choice, never a previous run's input/temp path.
        if saved_settings.get("input_source") == "original":
            input_entry.delete(0, "end")
            original = self.get_original_file()
            if original:
                input_entry.insert(0, original)
            routing["source"] = "original"
        elif saved_settings.get("input_source") == "manual":
            input_entry.delete(0, "end")
            routing["source"] = "manual"
        routing["value"] = input_entry.get()

        def capture_settings():
            return {
                "input_source": routing["source"],
                "option_values": [{"flag": flag, "type": kind, "value": var.get()}
                                  for flag, var, kind in option_vars],
                "before_enabled": switch_before_var.get(),
                "after_enabled": switch_after_var.get(),
                "before_rows": [{"flag": row["flag"].get(), "type": row["type"],
                                 "value": row["val"].get()} for row in before_rows],
                "after_rows": [{"flag": row["flag"].get(), "type": row["type"],
                                "value": row["val"].get()} for row in after_rows],
            }

        def sync_successful_step():
            snapshot = result.get("recipe")
            current = step_recipe(node, capture_settings())
            valid = (result["run"] is not None and result["run"].succeeded
                     and current == snapshot and input_entry.get() == result.get("input_value"))
            if valid:
                node["_successful_step"] = deepcopy(snapshot)
            else:
                node.pop("_successful_step", None)
            save_panel.pack_forget()
            if valid and is_last and not step_mode and completed_steps(self.nodes):
                save_panel.pack(fill="x", padx=10, pady=10)

        # Observe all edits, including Send to Input, paste and file selection.
        if routing["source"] == "previous" and logs and (previous_output or forwarded_file is not None):
            input_source.update(text=input_entry.get(), id=logs[-1].get('history_id'))
        # หน้าที่: ล้างการอ้างอิง source เดิมเมื่อแก้ input และปรับ preview
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window (อ้างอิง/callback)
        # Input: *args (tuple[str, ...] (arguments ของ Tk variable trace)) — Tk trace_add ส่งชื่อ variable/index/operation เมื่อค่าเปลี่ยน
        # Closure: input_source (dict) — รับจาก scope PipelinePage.open_step_window
        def input_changed(*args):
            if input_entry.get() != routing["value"]:
                routing.update(source="manual", value=input_entry.get())
            input_source.update(text=None, id=None)
            update_preview()
        input_var.trace_add("write", input_changed)
        update_preview()

        # -------- Description --------
        desc = node.get("user_description", "")
        if desc:
            ctk.CTkLabel(right, text="Description", font=ctk.CTkFont(weight="bold"), text_color=TEXT_DIM).pack(anchor="w", padx=20, pady=(10, 0))
            ctk.CTkLabel(right, text=desc, text_color=TEXT_DIM, wraplength=300).pack(anchor="w", padx=20)

        # -------- Run Tool --------
        # หน้าที่: อ่าน UI และตรวจ input เพื่อเตรียม (command, stdin, input_path); ยังไม่รัน subprocess
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window.run_tool (เรียกตรง)
        # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
        # Closure: forwarded_file (Path | None) — รับจาก scope PipelinePage.open_step_window
        # Closure: input_entry (ctk.CTkEntry) — รับจาก scope PipelinePage.open_step_window
        # Closure: output_box (ctk.CTkTextbox) — รับจาก scope PipelinePage.open_step_window
        # Closure: previous_output (bytes | Path | None) — รับจาก scope PipelinePage.open_step_window
        # Closure: self (PipelinePage) — รับจาก scope PipelinePage.open_step_window
        # Closure: tool_name (str) — รับจาก scope PipelinePage.open_step_window
        # อ่านภายใน: input_entry ผ่าน .get() — str จากช่องกรอก หรือชนิดที่ Tk Variable กำหนด
        def execute_tool():
            # รวม options → params
            # ตรวจว่าเป็น file tool หรือ text tool
            # เรียก PipelineEngine
            # แสดง output
            update_preview()
            if (saved_settings.get("input_source") == "original"
                    and routing["source"] == "original" and not input_entry.get().strip()):
                raise ValueError("Select the original file before running this saved step")

            if tool_name in self.engine.file_tools:
                # =====================================================
                # FILE TOOL
                # input_entry จะถูกเติมโดย
                # PREVIOUS / ORIGINAL / BROWSE
                # =====================================================

                path = input_entry.get().strip()

                # ถ้าช่อง path ว่าง
                # ลอง route previous_output อัตโนมัติอีกครั้ง
                if not path and previous_output and not (
                    saved_settings.get("input_source") in ("manual", "original")
                    and routing["source"] != "previous"
                ):

                    try:
                        resolved = resolve_file_input(previous_output)

                        if resolved["mode"] in (
                            "existing_path",
                            "artifact"
                        ):
                            path = resolved["path"]

                            if resolved["mode"] == "artifact":
                                self.register_temp_artifact(path)

                            # แสดงให้ user เห็นว่า UNIT เลือกอะไรให้
                            input_entry.delete(0, "end")
                            input_entry.insert(0, path)
                            routing.update(source="previous", value=input_entry.get())

                    except Exception as e:
                        output_box.insert(
                            "end",
                            f"\n[!] Input routing error: {e}\n"
                        )

                if not path:
                    raise ValueError(
                        "File tool requires a file.\n"
                        "Select PREVIOUS, ORIGINAL, or BROWSE."
                    )

                if not os.path.isfile(path):
                    raise ValueError("Input must be an existing file")
                return command_for(path), None, path

            else:
                # =====================================================
                # TEXT TOOL
                # behavior เดิม
                # =====================================================

                inp_data = input_entry.get()

                if routing["source"] == "original":
                    input_bytes = Path(inp_data)
                elif saved_settings.get("input_source") == "manual" and routing["source"] == "manual":
                    input_bytes = inp_data.encode("utf-8")
                elif not inp_data and forwarded_file is not None:
                    input_bytes = forwarded_file
                elif not inp_data and previous_output:
                    input_bytes = previous_output
                else:
                    input_bytes = inp_data.encode("utf-8")

                return command_for(), input_bytes, None

        # หน้าที่: นำ CommandResult มาอัปเดต stdout/stderr ไฟล์ผลลัพธ์ และสถานะของขั้นตอน
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window.run_tool.poll (เรียกตรง)
        # Input: res (CommandResult) — ผลหรือสถานะจากงานเบื้องหลังที่ผู้เรียกส่งต่อมา
        # Closure: browse_result_button (ctk.CTkButton) — รับจาก scope PipelinePage.open_step_window
        # Closure: continuation_panel (ctk.CTkFrame) — รับจาก scope PipelinePage.open_step_window
        # Closure: file_choices (dict) — รับจาก scope PipelinePage.open_step_window
        # Closure: file_status (ctk.CTkLabel) — รับจาก scope PipelinePage.open_step_window
        # Closure: full_buttons (ctk.CTkFrame) — รับจาก scope PipelinePage.open_step_window
        # Closure: history_tags (dict) — รับจาก scope PipelinePage.open_step_window
        # Closure: ยังอ่านตัวแปรร่วมอีก 5 ตัวจาก scope แม่
        # อ่านภายใน: output_box ผ่าน .get() — str จากช่องกรอก หรือชนิดที่ Tk Variable กำหนด
        def show_result(res):
            start = output_box.index('end-1c')
            result["run"] = res
            for stream_path in (res.stdout_file, res.stderr_file):
                if stream_path:
                    self.register_temp_artifact(str(stream_path))
            result["output"] = (res.stdout_file or res.stdout) if res.succeeded else None
            # Bound the visible run log; complete streams remain on disk.
            if int(output_box.index('end-1c').split('.')[0]) > 3000 or len(output_box.get('1.0', 'end-1c')) > PREVIEW_BYTES:
                output_box.delete('1.0', 'end')
                output_box.insert('end', '[Earlier preview cleared; saved history is unchanged.]\n')
            output_box.insert("end", f"\n>>> output ({tool_name})\n")
            if res.stdout:
                output_box.insert("end", res.stdout.decode(errors="replace") + "\n")
            if res.stderr:
                output_box.insert("end", "[stderr]\n" + res.stderr.decode(errors="replace") + "\n")
            if res.stdout_file or res.stderr_file:
                full_buttons.pack(pady=5)
                output_box.insert('end', '[Preview only. Full streams are retained; use View Full Output/Error or Save Output as File.]\n')
            else:
                full_buttons.pack_forget()
            if res.succeeded:
                output_box.insert("end", "[Success]\n")
                if not res.stdout:
                    output_box.insert("end", "No stdout output\n")
                file_status.configure(text="New or modified files from this run — select a file to forward")
                for path in res.files:
                    add_result_file(path)
                    output_box.insert("end", f"[Output file] {path}\n")
                if file_choices:
                    show_result_panel()
                elif not res.stdout or res.discovery_note:
                    # Quiet commands or incomplete discovery retain a compact
                    # manual fallback without reserving an empty file list.
                    browse_result_button.pack(pady=(0, 5))
                if res.discovery_note:
                    output_box.insert("end", f"[i] {res.discovery_note}\n")
                if step_mode:
                    continuation_panel.pack(side="bottom", fill="x", padx=10, pady=10)
            else:
                output_box.insert("end", "[Failed]\n")
            output_box.see("end")
            # File/continuation controls resize history after this callback.
            output_box.after_idle(output_box.see, "end")
            if result.get('history_id'):
                tag = 'history_' + result['history_id']
                output_box.tag_add(tag, start, 'end-1c')
                history_tags[tag] = result['history_id']
            sync_successful_step()

        # หน้าที่: ตรวจ input เก็บ snapshot/History และเริ่ม worker รันคำสั่งโดยไม่บล็อก UI
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window (อ้างอิง/callback)
        # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
        # Closure: browse_result_button (ctk.CTkButton) — รับจาก scope PipelinePage.open_step_window
        # Closure: cancel_button (ctk.CTkButton) — รับจาก scope PipelinePage.open_step_window
        # Closure: cancel_event (threading.Event) — รับจาก scope PipelinePage.open_step_window
        # Closure: continuation_panel (ctk.CTkFrame) — รับจาก scope PipelinePage.open_step_window
        # Closure: file_choices (dict) — รับจาก scope PipelinePage.open_step_window
        # Closure: file_list (ctk.CTkScrollableFrame) — รับจาก scope PipelinePage.open_step_window
        # Closure: ยังอ่านตัวแปรร่วมอีก 15 ตัวจาก scope แม่
        # อ่านภายใน: input_entry ผ่าน .get() — str จากช่องกรอก หรือชนิดที่ Tk Variable กำหนด
        def run_tool():
            if running[0]:
                return
            # A retry must never forward a file or stdout from the previous run.
            result.update(output=None, run=None, selected_file=None, decision=None)
            node.pop("_successful_step", None)
            save_panel.pack_forget()
            continuation_panel.pack_forget()
            file_selection.set("")
            file_choices.clear()
            for widget in file_list.winfo_children():
                widget.destroy()
            file_panel.pack_forget()
            browse_result_button.pack_forget()
            try:
                command, input_data, input_path = execute_tool()
            except (OSError, ValueError) as error:
                failed_id = history_hooks.begin(self.app_root, category='Pipeline', tool=tool_name,
                    input_data=input_entry.get(), options=node.get('params', ''), group_id=history_group)
                history_hooks.finish(self.app_root, failed_id, 'Failed', error=str(error))
                output_box.insert("end", f"\n[Failed] {error}\n")
                output_box.see("end")
                return
            # Freeze exactly what this invocation used, before the worker starts.
            result["recipe"] = step_recipe(node, capture_settings())
            result["input_value"] = input_entry.get()
            parent_id = input_source['id'] if input_source['text'] == input_entry.get() else None
            source_files = [input_path] if input_path else ([str(forwarded_file)] if forwarded_file is not None and not input_entry.get() else [])
            result['history_id'] = history_hooks.begin(self.app_root, category='Pipeline', tool=tool_name,
                input_data=input_data if input_data is not None else input_path,
                options=command, files=source_files, group_id=history_group, parent_id=parent_id)
            self._last_history_id = result['history_id']
            running[0] = True
            cancel_event.clear()
            self.active_runs.add(cancel_event)
            run_button.configure(state="disabled")
            next_button.configure(state="disabled")
            cancel_button.configure(state="normal")
            output_box.insert("end", "\n[Running]\n")

            # หน้าที่: รันคำสั่งที่เตรียมแล้วผ่าน engine._run_command และส่ง CommandResult หรือ exception ลง queue
            # ที่มา: pages/pipeline.py::PipelinePage.open_step_window.run_tool (อ้างอิง/callback)
            # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
            # Closure: command (list[str]) — รับจาก scope PipelinePage.open_step_window.run_tool
            # Closure: input_data (bytes | Path | None) — รับจาก scope PipelinePage.open_step_window.run_tool
            # Closure: input_path (str | None) — รับจาก scope PipelinePage.open_step_window.run_tool
            # Closure: cancel_event (threading.Event) — รับจาก scope PipelinePage.open_step_window
            # Closure: results (queue.Queue) — รับจาก scope PipelinePage.open_step_window
            # Closure: self (PipelinePage) — รับจาก scope PipelinePage.open_step_window
            def worker():
                try:
                    outcome = self.engine._run_command(command, input_data, input_path,
                                                       detailed=True, cancel_event=cancel_event)
                except Exception as error:
                    outcome = error
                results.put(outcome)

            # หน้าที่: ตรวจ queue ตามรอบ Tk timer แล้วนำผล worker มาแสดง
            # ที่มา: pages/pipeline.py::PipelinePage.open_step_window.run_tool (อ้างอิง/callback)
            # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
            # Closure: source_files (list[str]) — รับจาก scope PipelinePage.open_step_window.run_tool
            # Closure: cancel_button (ctk.CTkButton) — รับจาก scope PipelinePage.open_step_window
            # Closure: cancel_event (threading.Event) — รับจาก scope PipelinePage.open_step_window
            # Closure: closing (list[bool]) — รับจาก scope PipelinePage.open_step_window
            # Closure: next_button (ctk.CTkButton) — รับจาก scope PipelinePage.open_step_window
            # Closure: output_box (ctk.CTkTextbox) — รับจาก scope PipelinePage.open_step_window
            # Closure: ยังอ่านตัวแปรร่วมอีก 6 ตัวจาก scope แม่
            def poll():
                try:
                    outcome = results.get_nowait()
                except queue.Empty:
                    win.after(40, poll)
                    return
                self.active_runs.discard(cancel_event)
                running[0] = False
                run_button.configure(state="normal")
                next_button.configure(state="normal")
                cancel_button.configure(state="disabled")
                if isinstance(outcome, Exception):
                    history_hooks.finish(self.app_root, result['history_id'], 'Failed', error=str(outcome))
                    output_box.insert("end", f"\n[Failed] {outcome}\n")
                else:
                    history_hooks.finish(self.app_root, result['history_id'],
                        'Success' if outcome.succeeded else 'Failed', output_data=outcome.stdout,
                        error=outcome.stderr, files=source_files + [str(p) for p in outcome.files])
                    if outcome.succeeded:
                        node["run_settings"] = deepcopy(result["recipe"]["run_settings"])
                    show_result(outcome)
                if closing[0]:
                    result["output"] = None
                    win.destroy()

            threading.Thread(target=worker, daemon=True).start()
            win.after(40, poll)

        running, closing = [False], [False]
        cancel_event = threading.Event()
        results = queue.Queue()

        # หน้าที่: ยกเลิกงานที่ยังทำอยู่และปิดหน้าต่างขั้นตอนพร้อมคืนสถานะ
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window (อ้างอิง/callback)
        # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
        # Closure: cancel_event (threading.Event) — รับจาก scope PipelinePage.open_step_window
        # Closure: closing (list[bool]) — รับจาก scope PipelinePage.open_step_window
        # Closure: result (dict) — รับจาก scope PipelinePage.open_step_window
        # Closure: running (list[bool]) — รับจาก scope PipelinePage.open_step_window
        # Closure: win (ctk.CTkToplevel) — รับจาก scope PipelinePage.open_step_window
        def close_window():
            if running[0]:
                closing[0] = True
                cancel_event.set()
            else:
                result["output"] = None
                win.destroy()

        win.protocol("WM_DELETE_WINDOW", close_window)

        # buttons
        run_button = ctk.CTkButton(
            run_controls, text="Run", fg_color=ACCENT_GREEN, text_color="black",
            hover_color="#00CC33", command=run_tool
        )
        run_button.pack(pady=(15, 5))
        cancel_button = ctk.CTkButton(run_controls, text="Cancel", state="disabled",
                                      command=cancel_event.set, fg_color=BORDER_COLOR)
        cancel_button.pack(pady=(0, 5))

        # หน้าที่: ตรวจและเลือก output ที่จะส่งต่อแล้วปิดหน้าต่างเพื่อให้ runner ทำขั้นถัดไป
        # ที่มา: pages/pipeline.py::PipelinePage.open_step_window (อ้างอิง/callback)
        # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
        # Closure: file_choices (dict) — รับจาก scope PipelinePage.open_step_window
        # Closure: file_selection (tk.StringVar) — รับจาก scope PipelinePage.open_step_window
        # Closure: file_status (ctk.CTkLabel) — รับจาก scope PipelinePage.open_step_window
        # Closure: is_last (bool) — รับจาก scope PipelinePage.open_step_window
        # Closure: result (dict) — รับจาก scope PipelinePage.open_step_window
        # Closure: running (list[bool]) — รับจาก scope PipelinePage.open_step_window
        # Closure: ยังอ่านตัวแปรร่วมอีก 1 ตัวจาก scope แม่
        def next_step(): # ปิด window แล้วส่ง output กลับ pipeline
            if running[0]:
                return
            sync_successful_step()
            selected = result["selected_file"]
            if selected is not None:
                if not selected.is_file():
                    file_status.configure(text="Selected file not found. Please select another file.")
                    return
                result["output"] = selected
            elif not is_last and file_choices and not file_selection.get():
                file_status.configure(text="Select an output file before clicking Next.")
                return
            if is_last:
                win.destroy()
                return
            if result["output"] is None:
                return
            win.destroy()

        if step_mode:
            next_tools = sorted(set(self.engine.file_tools) | set(self.engine.text_tools))
            next_tool_menu = ctk.CTkComboBox(continuation_panel, values=next_tools, width=300)
            next_tool_menu.set("Select the next tool")
            next_tool_menu.pack(fill="x", padx=10, pady=5)
            decision_status = ctk.CTkLabel(continuation_panel, text="", text_color=ALERT_RED, wraplength=430)
            decision_status.pack(fill="x", padx=10)

            # หน้าที่: ตั้ง decision ของโหมด Step ว่าจะจบหรือส่งต่อไปเครื่องมือที่เลือก
            # ที่มา: pages/pipeline.py::PipelinePage.open_step_window (อ้างอิง/callback)
            # ที่มา: pages/pipeline.py::PipelinePage.open_step_window (เรียกตรง)
            # Input: finish (bool) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
            # Closure: decision_status (ctk.CTkLabel) — รับจาก scope PipelinePage.open_step_window
            # Closure: file_choices (dict) — รับจาก scope PipelinePage.open_step_window
            # Closure: file_selection (tk.StringVar) — รับจาก scope PipelinePage.open_step_window
            # Closure: next_tool_menu (ctk.CTkComboBox) — รับจาก scope PipelinePage.open_step_window
            # Closure: result (dict) — รับจาก scope PipelinePage.open_step_window
            # Closure: running (list[bool]) — รับจาก scope PipelinePage.open_step_window
            # Closure: ยังอ่านตัวแปรร่วมอีก 2 ตัวจาก scope แม่
            def complete_step(finish=False):
                if running[0] or result['run'] is None or not result['run'].succeeded:
                    return
                sync_successful_step()
                next_tool = None if finish else next_tool_menu.get().strip()
                if not finish and next_tool not in self.engine.file_tools and next_tool not in self.engine.text_tools:
                    decision_status.configure(text="Please select a tool from the list.")
                    return
                selected = result['selected_file']
                if selected is not None and not selected.is_file():
                    decision_status.configure(text="Selected file not found. Please select another file.")
                    return
                if not finish and file_choices and not file_selection.get():
                    decision_status.configure(text="Select an output file or stdout to forward before continuing.")
                    return
                result['decision'] = dict(
                    output=selected if selected is not None else result['output'],
                    files=list(file_choices.values()), next_tool=next_tool, history_id=result['history_id'],
                )
                win.destroy()

            decision_buttons = ctk.CTkFrame(continuation_panel, fg_color="transparent")
            decision_buttons.pack(fill="x", padx=10, pady=(0, 10))
            ctk.CTkButton(decision_buttons, text="Continue", width=120,
                          command=complete_step, fg_color=ACCENT_CYAN, text_color="black").pack(side="left", padx=(0, 5))
            ctk.CTkButton(decision_buttons, text="Finish", width=120,
                          command=lambda: complete_step(True), fg_color=ACCENT_GREEN, text_color="black").pack(side="left")

        next_button = ctk.CTkButton(
            run_controls,
            text="Close Analysis" if step_mode else ("Close" if is_last else "Next"),
            fg_color=BORDER_COLOR if is_last else ACCENT_CYAN,
            text_color="white" if is_last else "black",
            hover_color=CARD_COLOR if is_last else "#00CCCC",
            command=close_window if step_mode else next_step
        )
        next_button.pack()
        preview_ready = True
        update_preview()

        self.wait_window(win)

        return result["decision"] if step_mode else result["output"]

    #โหลด template pipeline สำเร็จรูป
    # หน้าที่: เลือกชุด tool จากชื่อ template แล้วสร้าง nodes ในโหมด Auto
    # ที่มา: pages/pipeline.py::PipelinePage.__init__ (อ้างอิง/callback)
    # Input: self (PipelinePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: template (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def load_template(self, template):
        if self.canvas_busy():
            return
        self.set_pipeline_mode("Auto")
        self.clear_pipeline()

        if template == "Basic Recon":
            tools = ["file", "strings", "uniq"]
        elif template == "Find Flag":
            tools = ["strings", "grep"]
        elif template == "Decode Base64":
            tools = ["strings", "grep", "base64_decode"]
        elif template == "Stego Scan":
            tools = ["file", "zsteg", "strings"]
        elif template == "Forensics Scan":
            tools = ["file", "binwalk", "strings"]
        else:
            return

        for tool in tools:
            self.add_tool_node(tool)

    #โหลด tool จาก JSON
    # หน้าที่: อ่านและตรวจ definitions ของ tools พร้อมเก็บ config error สำหรับ UI
    # ที่มา: pages/pipeline.py::PipelinePage.__init__ (เรียกตรง)
    # ที่มา: pages/pipeline.py::PipelinePage.refresh_tools_panel (เรียกตรง)
    # ที่มา: pages/pipeline.py::PipelinePage.open_pipeline_wizard (เรียกตรง)
    # Input: self (PipelinePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def load_tools_from_json(self):
        self.config_error = self.engine.load_error
        tools_path = str(writable_path('Pipeline/custom_tools.json'))
        tools_path = os.path.abspath(tools_path)
        main_data = {}
        try:
            main_data = read_json(tools_path, {})
            self.engine.validate_tools(main_data)
        except (OSError, ValueError, TypeError) as error:
            main_data = {}
            self.config_error = str(error)

        saved_path = str(writable_path('Pipeline/saved_pipelines.json'))
        saved_path = os.path.abspath(saved_path)
        saved_list = []
        if os.path.exists(saved_path):
            try:
                saved_list = saved_pipelines(saved_path)["saved_pipelines"]
            except Exception as e:
                self.config_error = f"Saved Pipelines: {e} (original file unchanged)"

        categories = {"Saved Pipelines": []}

        if saved_list:
            categories["Saved Pipelines"] = [p["pipeline_name"] for p in saved_list]

        for category in main_data:
            if category == "saved_pipelines":
                continue
            if isinstance(main_data[category], list):
                categories[category] = [tool["name"] for tool in main_data[category]]

        return categories

    def set_completed_recipe(self, steps):
        self._completed_recipe = deepcopy(steps)
        self.completed_panel.pack_forget()
        if steps:
            self.completed_panel.pack(fill="x", padx=15, pady=(0, 10), after=self.controls)

    def open_save_pipeline(self, steps, parent=None):
        if steps:
            return SavedPipelineDialog(self, steps, parent=parent)

    def add_saved_pipeline_row(self, name):
        row = ctk.CTkFrame(self.tools_panel, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=2)
        ctk.CTkButton(row, text="🗑️", width=30, fg_color="transparent",
                      text_color=ALERT_RED, hover_color=CARD_COLOR,
                      command=lambda: self.delete_saved_pipeline(name)).pack(side="right")
        ctk.CTkButton(row, text="🔨", width=30, fg_color="transparent",
                      text_color=ACCENT_CYAN, hover_color=CARD_COLOR,
                      command=lambda: self.edit_saved_pipeline(name)).pack(side="right")
        label = ctk.CTkLabel(row, text=f"• {name}", anchor="w", wraplength=140,
                            text_color=TEXT_DIM, cursor="hand2")
        label.pack(side="left", fill="x", expand=True)
        label.bind("<Button-1>", lambda event: self.load_saved_pipeline_to_canvas(name))

    def edit_saved_pipeline(self, name):
        if self.canvas_busy():
            return
        try:
            entries = saved_pipelines(writable_path("Pipeline/saved_pipelines.json"))["saved_pipelines"]
            entry = next(p for p in entries if p["pipeline_name"] == name)
            if not entry["steps"]:
                raise ValueError("This pipeline has no steps to edit")
            dialog = SavedPipelineDialog(self, entry["steps"], name, editing=True)
            dialog.expected = deepcopy(entry)
            return dialog
        except (OSError, ValueError, TypeError, StopIteration) as error:
            messagebox.showerror("Edit Pipeline", f"Cannot edit pipeline: {error}", parent=self)

    def delete_saved_pipeline(self, name):
        if self.canvas_busy():
            return
        try:
            entries = saved_pipelines(writable_path("Pipeline/saved_pipelines.json"))["saved_pipelines"]
            entry = next(p for p in entries if p["pipeline_name"] == name)
            if not messagebox.askyesno("Delete Pipeline", f'Delete saved pipeline "{name}"?', parent=self):
                return
            delete_recipe(writable_path("Pipeline/saved_pipelines.json"), name, expected=entry)
            self.refresh_tools_panel()
        except (OSError, ValueError, TypeError, StopIteration) as error:
            messagebox.showerror("Delete Pipeline", f"Delete failed: {error}", parent=self)

    #refresh panel tool 
    # หน้าที่: วาดรายการ tools และ Saved Pipelines ในแผงเลือกเครื่องมือใหม่
    # ที่มา: pages/pipeline.py::PipelinePage.finalize_wizard_pipeline (เรียกตรง)
    # ที่มา: pages/pipeline.py::PipelinePage.open_add_tool_window.save_tool (เรียกตรง)
    # Input: self (PipelinePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def refresh_tools_panel(self):
        for widget in self.tools_panel.winfo_children():
            widget.destroy()

        tool_categories = self.load_tools_from_json()
        if self.config_error:
            ctk.CTkLabel(self.tools_panel, text=self.config_error, text_color=ALERT_RED,
                         wraplength=210).pack(padx=10, pady=10)

        for cat, tools in tool_categories.items():
            header_frame = ctk.CTkFrame(self.tools_panel, fg_color="transparent")
            header_frame.pack(fill="x", padx=15, pady=(10, 0))

            ctk.CTkLabel(
                header_frame,
                text=cat,
                font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
                text_color=ACCENT_GREEN
            ).pack(side="left")

            for tool in tools:
                if cat in ["Pipelines", "Saved Pipelines"]:
                    self.add_saved_pipeline_row(tool)
                    continue
                lbl = ctk.CTkLabel(
                    self.tools_panel,
                    text=f"  • {tool}",
                    font=ctk.CTkFont(family="Consolas", size=12),
                    text_color=TEXT_DIM,
                    cursor="hand2"
                )
                lbl.pack(anchor="w", padx=15)

                if cat in ["Pipelines", "Saved Pipelines"]:
                    lbl.bind("<Button-1>", lambda e, name=tool: self.load_saved_pipeline_to_canvas(name))
                else:
                    lbl.bind("<Button-1>", lambda e, t=tool: self.add_tool_node(t))

            if cat in ["Pipelines", "Saved Pipelines"]:
                ctk.CTkButton(
                    self.tools_panel,
                    text="+ Add Pipeline",
                    command=self.open_pipeline_wizard,
                    fg_color="transparent",
                    border_width=1,
                    border_color=ACCENT_PURPLE,
                    text_color=ACCENT_PURPLE,
                    hover_color=CARD_COLOR
                ).pack(fill="x", padx=15, pady=(5, 10))

        self.add_btn = ctk.CTkButton(
            self.tools_panel, text="+ Add Tools", command=self.open_add_tool_window,
            fg_color="transparent", border_width=1, border_color=ACCENT_CYAN,
            text_color=ACCENT_CYAN, hover_color=CARD_COLOR)
        self.add_btn.pack(fill="x", padx=15, pady=20)

    #เช็ค pipeline ที่เคย save
    # หน้าที่: ตรวจรายการที่บันทึกแล้วและเลือกแสดงตัวช่วยเริ่มต้น Pipeline
    # ที่มา: helper ของหน้านี้สำหรับผู้เรียกหรือ callback; ไม่มีจุดเรียกตรงใน flow ปัจจุบันที่ตรวจพบ
    # Input: self (PipelinePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def check_pipeline_status(self):
        saved_data = self.load_saved_pipelines()
        self.show_startup_popup(saved_data)

    # popup หน้าเริ่มต้น (Pipeline Manager)
    # หน้าที่: แสดงตัวเลือกสร้าง Pipeline ใหม่หรือเปิดรายการที่บันทึกไว้
    # ที่มา: pages/pipeline.py::PipelinePage.check_pipeline_status (เรียกตรง)
    # Input: self (PipelinePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: saved_data (list[dict[str, Any]]) — รายการใน key saved_pipelines ที่ load_saved_pipelines อ่านจาก JSON
    def show_startup_popup(self, saved_data):
        popup = ctk.CTkToplevel(self)
        popup.title("Pipeline Manager")
        fit_window(popup, "460x480")
        popup.attributes("-topmost", True)
        popup.configure(fg_color=BG_COLOR)

        ctk.CTkLabel(
            popup, text=">_ UNIT PIPELINE", font=("Consolas", 20, "bold"), text_color=ACCENT_CYAN
        ).pack(pady=(20, 5))

        # หน้าที่: ปิด popup เริ่มต้นแล้วเปิด wizard สร้าง Pipeline
        # ที่มา: pages/pipeline.py::PipelinePage.show_startup_popup (อ้างอิง/callback)
        # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
        # Closure: popup (ctk.CTkToplevel) — รับจาก scope PipelinePage.show_startup_popup
        # Closure: self (PipelinePage) — รับจาก scope PipelinePage.show_startup_popup
        def create_new():
            popup.destroy()
            self.open_pipeline_wizard()

        # หน้าที่: ปิด popup เริ่มต้นแล้วโหลด Pipeline ตามชื่อที่เลือก
        # ที่มา: pages/pipeline.py::PipelinePage.show_startup_popup (เรียกตรง)
        # Input: p_name (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
        # Closure: popup (ctk.CTkToplevel) — รับจาก scope PipelinePage.show_startup_popup
        # Closure: self (PipelinePage) — รับจาก scope PipelinePage.show_startup_popup
        def load_existing(p_name):
            popup.destroy()
            self.load_saved_pipeline_to_canvas(p_name)

        bottom_frame = ctk.CTkFrame(popup, fg_color="transparent")
        bottom_frame.pack(side="bottom", fill="x", pady=20)

        ctk.CTkButton(
            bottom_frame, text="+ Create New Pipeline", fg_color=ACCENT_PURPLE, text_color="white",
            hover_color="#5c50e0", font=ctk.CTkFont(weight="bold"), height=40, command=create_new
        ).pack()

        content_frame = ctk.CTkFrame(popup, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=30)

        if not saved_data:
            ctk.CTkLabel(
                content_frame, text="No saved pipelines yet.\nStart creating your first pipeline!",
                text_color=TEXT_DIM
            ).pack(pady=40)
        else:
            ctk.CTkLabel(content_frame, text="Open a saved pipeline or create a new one", text_color=TEXT_DIM).pack(pady=(0, 10))

            list_frame = ctk.CTkScrollableFrame(content_frame, fg_color=PANEL_COLOR, border_width=1, border_color=BORDER_COLOR, corner_radius=10)
            list_frame.pack(fill="both", expand=True)

            for p in saved_data:
                p_name = p.get("pipeline_name", "Untitled Pipeline")

                row = ctk.CTkFrame(list_frame, fg_color="transparent")
                row.pack(fill="x", pady=5)

                ctk.CTkLabel(row, text=f"📄 {p_name}", font=ctk.CTkFont(weight="bold"), text_color="white").pack(side="left", padx=10)

                btn = ctk.CTkButton(
                    row, text="Open", width=60, fg_color=ACCENT_GREEN, text_color="black", hover_color="#00CC33",
                    command=lambda name=p_name: load_existing(name)
                )
                btn.pack(side="right", padx=10)

    #โหลด saved pipeline จากไฟล์
    # หน้าที่: อ่านและตรวจ Saved Pipelines จาก JSON แล้วคืนรายการหรือแจ้ง error
    # ที่มา: pages/dashboard.py::DashboardPage.get_available_tools (เรียกตรง)
    # ที่มา: pages/pipeline.py::PipelinePage.check_pipeline_status (เรียกตรง)
    # Input: self (PipelinePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def load_saved_pipelines(self):
        save_path = str(writable_path('Pipeline/saved_pipelines.json'))
        save_path = os.path.abspath(save_path)

        if os.path.exists(save_path):
            try:
                return saved_pipelines(save_path)["saved_pipelines"]
            except (OSError, ValueError) as error:
                messagebox.showerror("Saved Pipelines", str(error), parent=self)
        return []

    # แสดงจำนวน pipeline (debug)
    # หน้าที่: พิมพ์จำนวน Saved Pipelines สำหรับตรวจสถานะ
    # ที่มา: helper ของหน้านี้สำหรับผู้เรียกหรือ callback; ไม่มีจุดเรียกตรงใน flow ปัจจุบันที่ตรวจพบ
    # Input: self (PipelinePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: saved_data (list[dict[str, Any]]) — รายการใน key saved_pipelines ที่ load_saved_pipelines อ่านจาก JSON
    def show_saved_pipelines_list(self, saved_data):
        print(f"You have {len(saved_data)} saved pipelines available in the sidebar.")

    # Wizard สร้าง pipeline
    # หน้าที่: เปิดฟอร์มสร้าง Pipeline ทีละขั้นพร้อม tool/options ของแต่ละขั้น
    # ที่มา: pages/pipeline.py::PipelinePage.show_startup_popup.create_new (เรียกตรง)
    # ที่มา: pages/pipeline.py::PipelinePage.open_pipeline_wizard.add_next_tool (เรียกตรง)
    # ที่มา: pages/pipeline.py::PipelinePage.__init__ (อ้างอิง/callback)
    # ที่มาเพิ่มเติม: อีก 1 จุดเรียก/อ้างอิงในโปรเจกต์
    # Input: self (PipelinePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: current_step (int) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: pipeline_data (list[dict[str, Any]] | None) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # อ่านภายใน: tool_var ผ่าน .get() — str จากช่องกรอก หรือชนิดที่ Tk Variable กำหนด
    def open_pipeline_wizard(self, current_step=1, pipeline_data=None):
        if pipeline_data is None:
            pipeline_data = []

        wizard = ctk.CTkToplevel(self)
        wizard.title(f"Create Pipeline - Step {current_step}")
        fit_window(wizard, "600x740")
        wizard.attributes("-topmost", True)
        wizard.configure(fg_color=BG_COLOR)

        main_frame = ctk.CTkScrollableFrame(wizard, fg_color="transparent")
        main_frame.pack(fill="both", expand=True)

        name_entry = None
        if current_step == 1:
            ctk.CTkLabel(main_frame, text="Pipeline Name:", font=("Consolas", 13, "bold"), text_color=ACCENT_CYAN).pack(anchor="w", padx=40, pady=(15, 0))
            name_entry = ctk.CTkEntry(main_frame, placeholder_text="Enter your Pipeline name here...", fg_color=INPUT_BG, border_color=BORDER_COLOR, text_color="white")
            name_entry.pack(fill="x", padx=40, pady=10)
            self.current_pipeline_name = ""

        ctk.CTkLabel(main_frame, text=f"Step {current_step}: Command Builder", font=("Consolas", 18, "bold"), text_color=ACCENT_CYAN).pack(pady=20)

        ctk.CTkLabel(main_frame, text="Choose Tool:", text_color=TEXT_DIM).pack(anchor="w", padx=40)
        all_categories = self.load_tools_from_json()
        all_tools_list = []
        for cat in all_categories:
            if cat != "Saved Pipelines":
                all_tools_list.extend(all_categories[cat])

        all_tools_list.append("Custom")

        tool_var = ctk.StringVar(value=all_tools_list[0] if all_tools_list else "None")
        tool_menu = ctk.CTkOptionMenu(
            main_frame, values=all_tools_list, variable=tool_var,
            fg_color=INPUT_BG, button_color=PANEL_COLOR, button_hover_color=BORDER_COLOR,
            text_color=ACCENT_CYAN, dropdown_fg_color=PANEL_COLOR, dropdown_text_color=ACCENT_CYAN
        )
        tool_menu.pack(fill="x", padx=40, pady=(5, 10))

        custom_tool_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        custom_tool_entry = ctk.CTkEntry(custom_tool_frame, placeholder_text="Enter your Custom Tool command here...", fg_color=INPUT_BG, border_color=BORDER_COLOR, text_color="white")
        custom_tool_entry.pack(fill="x")

        desc_label = ctk.CTkLabel(main_frame, text="System Info: Select a tool", text_color=TEXT_DIM, wraplength=400)
        desc_label.pack(pady=10)

        has_option_var = ctk.BooleanVar(value=False)
        has_option_checkbox = ctk.CTkCheckBox(
            main_frame, text="Add options?", variable=has_option_var,
            text_color="white", fg_color=ACCENT_CYAN, hover_color="#00CCCC", checkmark_color="black", border_color=BORDER_COLOR
        )
        add_option_btn = ctk.CTkButton(main_frame, text="+ Add Option", fg_color=ACCENT_PURPLE, text_color="white", hover_color="#5c50e0")

        ctk.CTkLabel(main_frame, text="Note / Description", text_color=TEXT_DIM).pack(anchor="w", padx=40, pady=(15, 0))
        user_desc_entry = ctk.CTkEntry(main_frame, placeholder_text="..........", fg_color=INPUT_BG, border_color=BORDER_COLOR, text_color="white")
        user_desc_entry.pack(fill="x", padx=40, pady=(5, 10))

        # ==========================================
        # Popup Add Option (อัปเกรดแก้บัก State & Live Preview)
        # ==========================================
        self.temp_options_list = []
        # popup เพิ่ม option
        # หน้าที่: เปิดฟอร์มกำหนด options เพิ่มเติมให้ tool ใน wizard
        # ที่มา: pages/pipeline.py::PipelinePage.open_pipeline_wizard (อ้างอิง/callback)
        # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
        # Closure: self (PipelinePage) — รับจาก scope PipelinePage.open_pipeline_wizard
        # Closure: wizard (ctk.CTkToplevel) — รับจาก scope PipelinePage.open_pipeline_wizard
        def open_add_option_popup():
            popup = ctk.CTkToplevel(wizard)
            popup.title("Add Custom Option")
            fit_window(popup, "700x400")
            popup.attributes("-topmost", True)
            popup.configure(fg_color=BG_COLOR)

            ctk.CTkLabel(popup, text="Add Custom Option", font=("Consolas", 14, "bold"), text_color=ACCENT_CYAN).pack(pady=(10, 0))

            preview_label = ctk.CTkLabel(popup, text="Preview: ...", text_color=ACCENT_GREEN, font=ctk.CTkFont(family="Consolas", size=13))
            preview_label.pack(pady=(5, 10))

            options_container = ctk.CTkScrollableFrame(popup, fg_color="transparent", height=150)
            options_container.pack(fill="both", expand=True, padx=10)

            option_rows = []

            # อัปเดตพรีวิวแบบ Real-time ทันทีที่พิมพ์
            # หน้าที่: ประกอบคำสั่งตัวอย่างจาก options ในฟอร์มของ wizard
            # ที่มา: pages/pipeline.py::PipelinePage.open_pipeline_wizard.open_add_option_popup (เรียกตรง)
            # ที่มา: pages/pipeline.py::PipelinePage.open_pipeline_wizard.open_add_option_popup.add_option_row (อ้างอิง/callback)
            # ที่มา: pages/pipeline.py::PipelinePage.open_pipeline_wizard.open_add_option_popup.add_option_row (เรียกตรง)
            # ที่มาเพิ่มเติม: อีก 1 จุดเรียก/อ้างอิงในโปรเจกต์
            # Input: *args (tuple[str, ...] (arguments ของ Tk variable trace)) — Tk trace_add ส่งชื่อ variable/index/operation เมื่อค่าเปลี่ยน
            # Closure: option_rows (list) — รับจาก scope PipelinePage.open_pipeline_wizard.open_add_option_popup
            # Closure: preview_label (ctk.CTkLabel) — รับจาก scope PipelinePage.open_pipeline_wizard.open_add_option_popup
            # Closure: custom_tool_entry (ctk.CTkEntry) — รับจาก scope PipelinePage.open_pipeline_wizard
            # Closure: tool_var (ctk.StringVar) — รับจาก scope PipelinePage.open_pipeline_wizard
            # อ่านภายใน: tool_var, custom_tool_entry, flag_var ผ่าน .get() — str จากช่องกรอก หรือชนิดที่ Tk Variable กำหนด
            def preview_command(*args):
                base_tool = tool_var.get()
                if base_tool == "Custom":
                    base_tool = custom_tool_entry.get().strip() or "custom_tool"

                flags = []
                for flag_var, desc_var, opt_type in option_rows:
                    f = flag_var.get().strip()
                    if f:
                        if opt_type == "checkbox":
                            flags.append(f)
                        else:
                            flags.append(f"{f} <value>")

                cmd = f"{base_tool} {' '.join(flags)}"
                preview_label.configure(text=f"Preview: {cmd}")

            # หน้าที่: สร้างแถว checkbox/text/file option พร้อม flag และคำอธิบายเริ่มต้น
            # ที่มา: pages/pipeline.py::PipelinePage.open_pipeline_wizard.open_add_option_popup (เรียกตรง)
            # Input: opt_type (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
            # Input: default_flag (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
            # Input: default_desc (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
            # Closure: option_rows (list) — รับจาก scope PipelinePage.open_pipeline_wizard.open_add_option_popup
            # Closure: options_container (ctk.CTkScrollableFrame) — รับจาก scope PipelinePage.open_pipeline_wizard.open_add_option_popup
            def add_option_row(opt_type="checkbox", default_flag="", default_desc=""):
                row = ctk.CTkFrame(options_container, fg_color="transparent")
                row.pack(fill="x", pady=5)

                # ผูก trace_add เพื่อให้พรีวิวเด้งออโต้
                flag_var = tk.StringVar(value=default_flag)
                flag_var.trace_add("write", preview_command)
                flag_entry = ctk.CTkEntry(row, width=80, textvariable=flag_var, placeholder_text="-n", fg_color=INPUT_BG, border_color=BORDER_COLOR, text_color="white")
                flag_entry.pack(side="left", padx=5)

                desc_var = tk.StringVar(value=default_desc)
                desc_entry = ctk.CTkEntry(row, textvariable=desc_var, placeholder_text="description", fg_color=INPUT_BG, border_color=BORDER_COLOR, text_color="white")
                desc_entry.pack(side="left", fill="x", expand=True, padx=5)

                type_text = "No Param" if opt_type == "checkbox" else "With Param"
                type_color = "#3498db" if opt_type == "checkbox" else "#9b59b6"
                type_label = ctk.CTkLabel(row, text=type_text, width=100, fg_color=type_color, text_color="white", corner_radius=4)
                type_label.pack(side="left", padx=5)

                row_data = (flag_var, desc_var, opt_type)
                option_rows.append(row_data)

                # หน้าที่: ลบแถว option ที่จับไว้ใน closure แล้วปรับ preview
                # ที่มา: pages/pipeline.py::PipelinePage.open_pipeline_wizard.open_add_option_popup.add_option_row (อ้างอิง/callback)
                # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
                # Closure: row (ctk.CTkFrame) — รับจาก scope PipelinePage.open_pipeline_wizard.open_add_option_popup.add_option_row
                # Closure: row_data (tuple) — รับจาก scope PipelinePage.open_pipeline_wizard.open_add_option_popup.add_option_row
                # Closure: option_rows (list) — รับจาก scope PipelinePage.open_pipeline_wizard.open_add_option_popup
                def delete_this_row():
                    if row_data in option_rows:
                        option_rows.remove(row_data)
                    row.destroy()
                    preview_command()

                del_btn = ctk.CTkButton(row, text="X", width=30, fg_color=ALERT_RED, hover_color="#C0294B", text_color="white", command=delete_this_row)
                del_btn.pack(side="left", padx=5)

                preview_command()

            # โหลดข้อมูลเก่าที่เคยแอดไว้ขึ้นมาโชว์ (ถ้ามีการเปิดปิดหน้าต่างหลายรอบ)
            for opt in self.temp_options_list:
                add_option_row(opt["type"], opt["flag"], opt["description"])

            # หน้าที่: เก็บ options ที่กำหนดใน popup กลับสู่ขั้นตอนของ wizard
            # ที่มา: pages/pipeline.py::PipelinePage.open_pipeline_wizard.open_add_option_popup (อ้างอิง/callback)
            # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
            # Closure: option_rows (list) — รับจาก scope PipelinePage.open_pipeline_wizard.open_add_option_popup
            # Closure: popup (ctk.CTkToplevel) — รับจาก scope PipelinePage.open_pipeline_wizard.open_add_option_popup
            # Closure: self (PipelinePage) — รับจาก scope PipelinePage.open_pipeline_wizard
            # อ่านภายใน: flag_var, desc_var ผ่าน .get() — str จากช่องกรอก หรือชนิดที่ Tk Variable กำหนด
            def save_option_from_popup():
                self.temp_options_list.clear() # เคลียร์ของเก่าทิ้งก่อนบันทึกใหม่
                for flag_var, desc_var, opt_type in option_rows:
                    flag = flag_var.get().strip()
                    desc = desc_var.get().strip()
                    if flag:
                        self.temp_options_list.append({"flag": flag, "type": opt_type, "description": desc})
                        print(f"Added Option: {flag} ({opt_type})")
                popup.destroy()

            btn_row = ctk.CTkFrame(popup, fg_color="transparent")
            btn_row.pack(fill="x", pady=15, padx=20)

            ctk.CTkButton(btn_row, text="+ No Param", command=lambda: add_option_row("checkbox"), width=100, fg_color="#3498db", hover_color="#2980b9").pack(side="left", padx=5)
            ctk.CTkButton(btn_row, text="+ With Param", command=lambda: add_option_row("text"), width=100, fg_color="#9b59b6", hover_color="#8e44ad").pack(side="left", padx=5)

            # เอาปุ่ม Preview ออกไปเลย เพราะตอนนี้อัปเดตแบบเรียลไทม์แล้ว
            ctk.CTkButton(btn_row, text="Save & Close", command=save_option_from_popup, fg_color=ACCENT_GREEN, hover_color="#00CC33", text_color="black", width=110).pack(side="right", padx=5)

            preview_command() # รันพรีวิวครั้งแรก

        add_option_btn.configure(command=open_add_option_popup)
        # ==========================================

        # อัปเดต info tool ที่เลือก
        # หน้าที่: ปรับข้อมูลและ controls เมื่อเลือก tool ใหม่ใน wizard
        # ที่มา: pages/pipeline.py::PipelinePage.open_pipeline_wizard (เรียกตรง)
        # ที่มา: pages/pipeline.py::PipelinePage.open_pipeline_wizard (อ้างอิง/callback)
        # Input: choice (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
        # Closure: add_option_btn (ctk.CTkButton) — รับจาก scope PipelinePage.open_pipeline_wizard
        # Closure: custom_tool_frame (ctk.CTkFrame) — รับจาก scope PipelinePage.open_pipeline_wizard
        # Closure: desc_label (ctk.CTkLabel) — รับจาก scope PipelinePage.open_pipeline_wizard
        # Closure: has_option_checkbox (ctk.CTkCheckBox) — รับจาก scope PipelinePage.open_pipeline_wizard
        # Closure: has_option_var (ctk.BooleanVar) — รับจาก scope PipelinePage.open_pipeline_wizard
        # Closure: self (PipelinePage) — รับจาก scope PipelinePage.open_pipeline_wizard
        # Closure: ยังอ่านตัวแปรร่วมอีก 2 ตัวจาก scope แม่
        def update_tool_selection(choice):
            if choice == "Custom":
                custom_tool_frame.pack(after=tool_menu, fill="x", padx=40, pady=(0, 10))
                desc_label.configure(text="System Info: Custom Tool Mode")
            else:
                custom_tool_frame.pack_forget()
                desc = self.engine.tool_descriptions.get(choice, "No info available")
                desc_label.configure(text=f"System Info: {desc}")

            has_option_checkbox.pack(before=user_desc_entry.master.winfo_children()[-2], anchor="w", padx=40, pady=5)
            has_option_var.set(False)
            add_option_btn.pack_forget()

        # toggle ปุ่ม add option
        # หน้าที่: ปรับการแสดงส่วนกำหนด options ตามตัวเลือกของ wizard
        # ที่มา: pages/pipeline.py::PipelinePage.open_pipeline_wizard (อ้างอิง/callback)
        # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
        # Closure: add_option_btn (ctk.CTkButton) — รับจาก scope PipelinePage.open_pipeline_wizard
        # Closure: has_option_checkbox (ctk.CTkCheckBox) — รับจาก scope PipelinePage.open_pipeline_wizard
        # Closure: has_option_var (ctk.BooleanVar) — รับจาก scope PipelinePage.open_pipeline_wizard
        # อ่านภายใน: has_option_var ผ่าน .get() — str จากช่องกรอก หรือชนิดที่ Tk Variable กำหนด
        def toggle_add_option_btn():
            if has_option_var.get():
                add_option_btn.pack(after=has_option_checkbox, pady=5, padx=40, anchor="w")
            else:
                add_option_btn.pack_forget()

        has_option_checkbox.configure(command=toggle_add_option_btn)
        tool_menu.configure(command=update_tool_selection)
        update_tool_selection(tool_var.get())

        btn_frame = ctk.CTkFrame(wizard, fg_color="transparent")
        btn_frame.pack(side="bottom", pady=30, fill="x", padx=40)

        # เพิ่ม tool step ถัดไป
        # หน้าที่: บันทึกข้อมูลขั้นปัจจุบันแล้วเปิด wizard ของขั้นถัดไป
        # ที่มา: pages/pipeline.py::PipelinePage.open_pipeline_wizard (อ้างอิง/callback)
        # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
        # Closure: current_step (int) — รับจาก scope PipelinePage.open_pipeline_wizard
        # Closure: custom_tool_entry (ctk.CTkEntry) — รับจาก scope PipelinePage.open_pipeline_wizard
        # Closure: name_entry (CTkEntry | None) — รับจาก scope PipelinePage.open_pipeline_wizard
        # Closure: pipeline_data (list[dict[str, Any]] | None) — รับจาก scope PipelinePage.open_pipeline_wizard
        # Closure: self (PipelinePage) — รับจาก scope PipelinePage.open_pipeline_wizard
        # Closure: tool_var (ctk.StringVar) — รับจาก scope PipelinePage.open_pipeline_wizard
        # Closure: ยังอ่านตัวแปรร่วมอีก 2 ตัวจาก scope แม่
        # อ่านภายใน: name_entry, tool_var, custom_tool_entry, user_desc_entry ผ่าน .get() — str จากช่องกรอก หรือชนิดที่ Tk Variable กำหนด
        def add_next_tool():
            if current_step == 1 and name_entry:
                self.current_pipeline_name = name_entry.get()

            selected_tool = tool_var.get()
            if selected_tool == "Custom":
                selected_tool = custom_tool_entry.get()

            node_data = {
                "name": selected_tool,
                "params": "",
                "user_description": user_desc_entry.get(),
                "options": self.temp_options_list
            }
            pipeline_data.append(node_data)
            wizard.destroy()
            self.open_pipeline_wizard(current_step + 1, pipeline_data)

        # finish wizard + save pipeline
        # หน้าที่: บันทึกขั้นสุดท้ายและขอชื่อก่อนส่งชุดข้อมูลไป finalize
        # ที่มา: pages/pipeline.py::PipelinePage.open_pipeline_wizard (อ้างอิง/callback)
        # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
        # Closure: current_step (int) — รับจาก scope PipelinePage.open_pipeline_wizard
        # Closure: custom_tool_entry (ctk.CTkEntry) — รับจาก scope PipelinePage.open_pipeline_wizard
        # Closure: name_entry (CTkEntry | None) — รับจาก scope PipelinePage.open_pipeline_wizard
        # Closure: pipeline_data (list[dict[str, Any]] | None) — รับจาก scope PipelinePage.open_pipeline_wizard
        # Closure: self (PipelinePage) — รับจาก scope PipelinePage.open_pipeline_wizard
        # Closure: tool_var (ctk.StringVar) — รับจาก scope PipelinePage.open_pipeline_wizard
        # Closure: ยังอ่านตัวแปรร่วมอีก 2 ตัวจาก scope แม่
        # อ่านภายใน: name_entry, tool_var, custom_tool_entry, user_desc_entry ผ่าน .get() — str จากช่องกรอก หรือชนิดที่ Tk Variable กำหนด
        def finish_pipeline():
            if current_step == 1 and name_entry:
                self.current_pipeline_name = name_entry.get()

            pipeline_name = self.current_pipeline_name if getattr(self, "current_pipeline_name", "") else "Untitled"

            selected_tool = tool_var.get()
            if selected_tool == "Custom":
                selected_tool = custom_tool_entry.get()

            node_data = {
                "name": selected_tool,
                "params": "",
                "user_description": user_desc_entry.get(),
                "options": self.temp_options_list
            }
            pipeline_data.append(node_data)
            wizard.destroy()
            self.finalize_wizard_pipeline(pipeline_data, pipeline_name)

        ctk.CTkButton(btn_frame, text="+ Add Another Tool", fg_color=ACCENT_PURPLE, text_color="white", hover_color="#5c50e0", command=add_next_tool).pack(side="left", expand=True, padx=5)
        ctk.CTkButton(btn_frame, text="Finish & Save", fg_color=ACCENT_GREEN, text_color="black", hover_color="#00CC33", command=finish_pipeline).pack(side="left", expand=True, padx=5)

    # สร้าง pipeline ลง canvas + save
    # หน้าที่: ตรวจและบันทึก Pipeline ที่สร้างจาก wizard แล้วโหลด nodes ลง canvas
    # ที่มา: pages/pipeline.py::PipelinePage.open_pipeline_wizard.finish_pipeline (เรียกตรง)
    # Input: self (PipelinePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: pipeline_data (list[dict[str, Any]]) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    # Input: pipeline_name (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def finalize_wizard_pipeline(self, pipeline_data, pipeline_name):
        if self.canvas_busy():
            return
        save_path = str(writable_path('Pipeline/saved_pipelines.json'))
        save_path = os.path.abspath(save_path)

        try:
            data = saved_pipelines(save_path)
            if not pipeline_name.strip():
                raise ValueError("Pipeline name is required")
            if any(p["pipeline_name"] == pipeline_name for p in data["saved_pipelines"]):
                raise ValueError("Pipeline name already exists; choose a different name")
            if any(step["name"] not in self.engine.file_tools and step["name"] not in self.engine.text_tools for step in pipeline_data):
                raise ValueError("Add/register custom tools before saving a pipeline")

            new_entry = {
                "pipeline_name": pipeline_name,
                "steps": pipeline_data
            }
            data["saved_pipelines"].append(new_entry)
            validate_saved_pipelines(data)
            write_json(save_path, data)
            self.set_pipeline_mode("Auto")
            self.clear_pipeline()
            for tool_info in pipeline_data:
                self.add_tool_node(tool_info["name"], user_desc=tool_info.get("user_description", ""))
                self.nodes[-1]["params"] = tool_info.get("params", "")
                self.nodes[-1]["options"] = tool_info.get("options", [])
            self.refresh_tools_panel()
            print(f"Saved pipeline '{pipeline_name}' successfully!")

        except Exception as e:
            messagebox.showerror("Save Pipeline", f"Save failed. The original file was not overwritten:\n{e}", parent=self)

    # โหลด pipeline มาแสดงบน canvas
    # หน้าที่: ค้นหา Pipeline ตามชื่อและคืนค่า nodes/params/options ลง canvas
    # ที่มา: pages/dashboard.py::DashboardPage.launch_favorite (เรียกตรง)
    # ที่มา: pages/pipeline.py::PipelinePage.show_startup_popup.load_existing (เรียกตรง)
    # ที่มา: pages/pipeline.py::PipelinePage.__init__ (เรียกตรง)
    # ที่มาเพิ่มเติม: อีก 1 จุดเรียก/อ้างอิงในโปรเจกต์
    # Input: self (PipelinePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    # Input: pipeline_name (str) — argument จากจุดเรียก/ตัวเชื่อม callback ที่ระบุด้านบน
    def load_saved_pipeline_to_canvas(self, pipeline_name):
        if self.canvas_busy():
            return
        save_path = str(writable_path('Pipeline/saved_pipelines.json'))
        save_path = os.path.abspath(save_path)

        if not os.path.exists(save_path):
            return

        try:
            data = saved_pipelines(save_path)
        except (OSError, ValueError, TypeError) as error:
            messagebox.showerror("Saved Pipeline", str(error), parent=self)
            return

        for p in data.get("saved_pipelines", []):
            if p["pipeline_name"] == pipeline_name:
                self.set_pipeline_mode("Auto")
                self.clear_pipeline()
                x = 80
                y = 120

                for step in p["steps"]:
                    self.node_count += 1
                    node = ctk.CTkFrame(
                        self.line_canvas,
                        fg_color=CARD_COLOR,
                        corner_radius=4,
                        border_width=1,
                        border_color=ACCENT_PURPLE,
                        width=110,
                        height=35
                    )
                    node.place(x=x, y=y)

                    lbl = ctk.CTkLabel(
                        node,
                        text=step["name"],
                        font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
                        text_color=ACCENT_CYAN
                    )
                    lbl.place(relx=0.5, rely=0.5, anchor="center")

                    node_data = {
                        "frame": node,
                        "name": step["name"],
                        "params": step.get("params", ""),
                        "user_description": step.get("user_description", ""),
                        "options": step.get("options", [])
                    }
                    if "run_settings" in step:
                        node_data["run_settings"] = deepcopy(step["run_settings"])
                    self.nodes.append(node_data)

                    for item in [node, lbl]:
                        item.bind(
                            "<Button-1>",
                            lambda e, n=node_data: self.on_node_press(e, n)
                        )
                        item.bind(
                            "<B1-Motion>",
                            lambda e, n=node_data: self.on_node_drag(e, n)
                        )
                    x += 160

                self.draw_connections()
                return True
        return False

    # popup เพิ่ม tool ใหม่
    # หน้าที่: เปิดฟอร์มสร้าง definition ของ custom tool ใหม่
    # ที่มา: pages/pipeline.py::PipelinePage.__init__ (อ้างอิง/callback)
    # Input: self (PipelinePage) — Python ส่ง instance ของคลาสเมื่อเรียกเมธอด
    def open_add_tool_window(self):
        win = ctk.CTkToplevel(self)
        win.title("Add Tool")
        fit_window(win, "350x290")
        win.configure(fg_color=BG_COLOR)

        ctk.CTkLabel(win, text="Tool Name", text_color=TEXT_DIM).pack(pady=5)
        name_entry = ctk.CTkEntry(win, fg_color=INPUT_BG, border_color=BORDER_COLOR, text_color="white")
        name_entry.pack(pady=5)

        ctk.CTkLabel(win, text="Linux Command", text_color=TEXT_DIM).pack(pady=5)
        cmd_entry = ctk.CTkEntry(win, fg_color=INPUT_BG, border_color=BORDER_COLOR, text_color="white")
        cmd_entry.pack(pady=5)

        mode_var = ctk.StringVar(value="text")

        ctk.CTkOptionMenu(
            win,
            values=["text", "file"],
            variable=mode_var,
            fg_color=INPUT_BG, button_color=PANEL_COLOR, button_hover_color=BORDER_COLOR,
            text_color=ACCENT_CYAN, dropdown_fg_color=PANEL_COLOR, dropdown_text_color=ACCENT_CYAN
        ).pack(pady=5)

        # หน้าที่: อ่านฟอร์ม custom tool แล้วให้ engine ตรวจ/บันทึกและรีเฟรชรายการ tools
        # ที่มา: pages/pipeline.py::PipelinePage.open_add_tool_window (อ้างอิง/callback)
        # Input: ไม่มีพารามิเตอร์โดยตรง; ใช้ค่าที่จับไว้จาก scope ภายนอกตามด้านล่าง
        # Closure: cmd_entry (ctk.CTkEntry) — รับจาก scope PipelinePage.open_add_tool_window
        # Closure: mode_var (ctk.StringVar) — รับจาก scope PipelinePage.open_add_tool_window
        # Closure: name_entry (ctk.CTkEntry) — รับจาก scope PipelinePage.open_add_tool_window
        # Closure: self (PipelinePage) — รับจาก scope PipelinePage.open_add_tool_window
        # Closure: win (ctk.CTkToplevel) — รับจาก scope PipelinePage.open_add_tool_window
        # อ่านภายใน: name_entry, cmd_entry, mode_var ผ่าน .get() — str จากช่องกรอก หรือชนิดที่ Tk Variable กำหนด
        def save_tool():
            name = name_entry.get()
            cmd = cmd_entry.get()
            mode = mode_var.get()

            if not name or not cmd:
                return

            try:
                self.engine.save_custom_tool(name, cmd, mode, "Custom")
                self.refresh_tools_panel()
            except (OSError, ValueError) as error:
                messagebox.showerror("Add Tool", str(error), parent=win)
                return
            win.destroy()

        ctk.CTkButton(
            win, text="Add Tool", command=save_tool,
            fg_color=ACCENT_GREEN, text_color="black", hover_color="#00CC33"
        ).pack(pady=10)
