import json
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
from Pipeline.pipeline_engine import PipelineEngine
import tempfile
import os

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
    def __init__(self, master):
        super().__init__(master)
        self.app_root = master.master  # ใช้เรียก switch_page / send_to_* ข้ามหน้า
        self.run_logs = []
        self.engine = PipelineEngine() #เชื่อมกับ backend
        self.temp_artifacts = []
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

        # --- Canvas Area ---
        self.canvas_container = ctk.CTkFrame(self.work_area, fg_color=INPUT_BG, corner_radius=8)
        self.canvas_container.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self.line_canvas = tk.Canvas(self.canvas_container, bg=INPUT_BG, highlightthickness=0)
        self.line_canvas.pack(fill="both", expand=True)

        self.placeholder = ctk.CTkLabel(
            self.line_canvas, text="[ PIPELINE FLOW CANVAS — คลิก tool ด้านซ้ายเพื่อเริ่ม ]",
            font=("Consolas", 12), text_color=TEXT_DIM
        )
        self.placeholder.place(relx=0.5, rely=0.5, anchor="center")

        # หมายเหตุ: เดิมมี popup "Pipeline Manager" ที่ผุดขึ้นบังคับทุกครั้งที่เข้าหน้านี้
        # ตัดออกแล้วเพราะ Saved Pipelines / + Add Pipeline มีอยู่แล้วในแผง ALL_TOOLS ด้านซ้าย
        # ผู้ใช้ยังเรียกดู pipeline ที่บันทึกไว้ได้ตามปกติ ไม่ต้องถูกขัดจังหวะตอนเข้าหน้า
    
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

    def set_step_input_path(self, entry, path):
        """
        Replace path ในช่อง input ของ Step Window
        """

        entry.delete(0, "end")

        if path:
            entry.insert(0, path)
    
    def register_temp_artifact(self, path):
        if path and path not in self.temp_artifacts:
            self.temp_artifacts.append(path)


    def cleanup_pipeline_artifacts(self):
        for path in self.temp_artifacts:
            remove_temp_artifact(path)

        self.temp_artifacts.clear()
    # เพิ่ม node (tool) ลง canvas
    def add_tool_node(self, tool_name, user_desc=""):
        if self.node_count == 0:
            self.placeholder.place_forget()

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

    # เริ่มลาก node
    def on_node_press(self, event, node_data):
        self.current_node = node_data
        node_data['drag_data'] = {
            'x': event.x,
            'y': event.y
        }
        node_data['frame'].lift()

    # ลาก node
    def on_node_drag(self, event, node_data):
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
    def reorder_nodes_by_position(self):
        self.nodes.sort(key=lambda n: n['frame'].winfo_x())

    

    # วาดเส้นเชื่อมระหว่าง node
    def draw_connections(self):
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
    def run_pipeline(self):
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
                "output": output
            })

            current_data = output

    # ล้าง pipeline
    def clear_pipeline(self):
        print("Clearing pipeline...")
        for node in self.nodes:
            node['frame'].destroy()
        self.nodes.clear()
        self.node_count = 0
        self.line_canvas.delete("line")
        self.cleanup_pipeline_artifacts()
        # P0.4B
        self.original_file_path = None

    # สร้างไฟล์ temp จาก data
    def write_temp_file(self, data):
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.write(data)
        tmp.close()
        return tmp.name

    # เปิด popup ของแต่ละ step
    def open_step_window(self, node, previous_output, original_data, logs, is_last, step_index=1, total_steps=1):

        tool_name = node["name"]

        win = ctk.CTkToplevel(self)
        win.title(f"Step {step_index}/{total_steps} — {tool_name}")
        win.geometry("1000x660")
        win.attributes("-topmost", True)
        win.configure(fg_color=BG_COLOR)

        # ---------------- แถบ Progress (Step X / N) ----------------
        progress_header = ctk.CTkFrame(win, fg_color=PANEL_COLOR, corner_radius=8)
        progress_header.pack(fill="x", padx=10, pady=(10, 0))

        ctk.CTkLabel(
            progress_header,
            text=f"STEP {step_index} / {total_steps}  ·  {tool_name}",
            font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
            text_color=ACCENT_CYAN
        ).pack(side="left", padx=15, pady=10)

        progress_bar = ctk.CTkProgressBar(
            progress_header, width=220, progress_color=ACCENT_GREEN, fg_color=INPUT_BG
        )
        progress_bar.pack(side="right", padx=15, pady=10)
        progress_bar.set(step_index / total_steps if total_steps else 1)

        container = ctk.CTkFrame(win, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # ---------------- LEFT PANEL ----------------
        left = ctk.CTkFrame(container, width=520, fg_color=PANEL_COLOR, border_width=1, border_color=BORDER_COLOR)
        left.pack(side="left", fill="both", expand=True, padx=(0, 5))

        ctk.CTkLabel(
            left, text="PIPELINE OUTPUT HISTORY",
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"), text_color=ACCENT_CYAN
        ).pack(anchor="w", padx=10, pady=(10, 0))

        output_box = ctk.CTkTextbox(
            left, fg_color=INPUT_BG, border_width=1, border_color=BORDER_COLOR,
            text_color=ACCENT_GREEN, font=("Consolas", 12)
        )
        output_box.pack(fill="both", expand=True, padx=10, pady=10)

        def send_selected_to_input():
            try:
                selected = output_box.get("sel.first", "sel.last")
                input_entry.delete(0, "end")
                input_entry.insert(0, selected.strip())
            except:
                pass

        def get_selected_or_output_text():
            # ถ้าผู้ใช้ select ข้อความไว้ ใช้ส่วนที่ select
            # ถ้าไม่ได้ select อะไรเลย ใช้ output ล่าสุดของ step นี้แทน (สะดวกกว่าปล่อยว่าง)
            try:
                return output_box.get("sel.first", "sel.last").strip()
            except Exception:
                pass
            if result["output"] is not None:
                try:
                    return result["output"].decode(errors="ignore").strip()
                except Exception:
                    return str(result["output"]).strip()
            return ""

        def send_selected_to_gemini():
            text = get_selected_or_output_text()
            if text and hasattr(self.app_root, "send_to_gemini"):
                self.app_root.send_to_gemini(text)

        def send_selected_to_hashing():
            text = get_selected_or_output_text()
            if text and hasattr(self.app_root, "send_to_hashing"):
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

        def show_context_menu(event):
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()

        output_box.bind("<Button-3>", show_context_menu)

        result = {"output": None}

        output_box.insert("end", ">>> original input\n")

        if original_data:
            preview = original_data[:2000].decode(errors="ignore")
        else:
            preview = "[No file input]"

        output_box.insert("end", preview + "\n")

        for log in logs:
            tool = log["tool"]
            out = log["output"]

            if isinstance(out, bytes):
                out = out.decode(errors="ignore")

            output_box.insert("end", f"\n>>> {tool}\n")
            output_box.insert("end", out + "\n")

        def save_output():
            if result["output"] is None:
                return
            win.attributes("-topmost", False)
            path = filedialog.asksaveasfilename(parent=win, defaultextension=".txt")
            win.attributes("-topmost", True)

            if path:
                with open(path, "wb") as f:
                    f.write(result["output"])

        ctk.CTkButton(
            left, text="Save Output as File", command=save_output,
            fg_color="transparent", border_width=1, border_color=ACCENT_CYAN,
            text_color=ACCENT_CYAN, hover_color=CARD_COLOR
        ).pack(pady=5)

        # ---------------- RIGHT PANEL ----------------
        right = ctk.CTkFrame(container, width=380, fg_color=PANEL_COLOR, border_width=1, border_color=BORDER_COLOR)
        right.pack(side="left", fill="y", padx=(5, 0))

        ctk.CTkLabel(
            right, text=tool_name, font=ctk.CTkFont(family="Consolas", size=16, weight="bold"),
            text_color=ACCENT_CYAN
        ).pack(pady=10)

        # -------- Input --------
        ctk.CTkLabel(right, text="Input", text_color=TEXT_DIM).pack(anchor="w", padx=20)

        input_frame = ctk.CTkFrame(right, fg_color="transparent")
        input_frame.pack(fill="x", padx=20, pady=5)

        input_entry = ctk.CTkEntry(input_frame, fg_color=INPUT_BG, border_color=BORDER_COLOR, text_color="white")
        input_entry.pack(side="left", fill="x", expand=True)

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

        options_frame = ctk.CTkFrame(right, fg_color="transparent")
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

                output_box.insert(
                    "end",
                    "\n>>> INPUT SOURCE: PREVIOUS\n"
                    f"[+] {previous_file_path}\n"
                )

                update_preview()

            # ----------------------------------------------
            # ORIGINAL
            # ----------------------------------------------

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

                output_box.insert(
                    "end",
                    "\n>>> INPUT SOURCE: ORIGINAL\n"
                    f"[+] {original}\n"
                )

                update_preview()

            # ----------------------------------------------
            # SET ORIGINAL
            # ----------------------------------------------

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

        def update_preview(*args):
            params_list = []
            for flag, var, opt_type in option_vars:
                if opt_type == "checkbox":
                    if var.get():
                        params_list.append(flag)
                elif opt_type in ["text", "file"]:
                    val = var.get().strip()
                    if val:
                        params_list.append(f"{flag} {val}")

            params_before_fixed = " ".join(params_list)

            after_tool = preview_before_args() if switch_before_var.get() else ""
            after_input = preview_after_args() if switch_after_var.get() else ""

            inp = input_entry.get().strip()

            cmd = tool_name
            if after_tool:
                cmd += f" {after_tool}"
            if params_before_fixed:
                cmd += f" {params_before_fixed}"
            if inp:
                cmd += f" {inp}"
            if after_input:
                cmd += f" {after_input}"

            preview_label.configure(text=cmd)

        for opt in tool_options:
            flag = opt["flag"]
            desc = opt.get("description", "").strip()
            opt_type = opt["type"]

            # จัดรูปแบบใหม่: เอาวงเล็บออก และถ้าไม่มีคำอธิบายให้โชว์แค่ flag
            display_text = f"{flag}  {desc}" if desc else flag

            row = ctk.CTkFrame(options_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)

            if opt_type == "checkbox":
                var = tk.BooleanVar()
                chk = ctk.CTkCheckBox(
                    row, text=display_text, variable=var, command=update_preview,
                    text_color="white", fg_color=ACCENT_CYAN, hover_color="#00CCCC",
                    checkmark_color="black", border_color=BORDER_COLOR
                )
                chk.pack(anchor="w")
                option_vars.append((flag, var, "checkbox"))

            elif opt_type in ["text", "file"]:
                ctk.CTkLabel(row, text=f"{display_text}:", text_color=TEXT_DIM).pack(side="left", padx=(0, 5))
                var = tk.StringVar()
                var.trace_add("write", update_preview)
                ent = ctk.CTkEntry(row, textvariable=var, width=120, fg_color=INPUT_BG, border_color=BORDER_COLOR, text_color="white")
                ent.pack(side="left", fill="x", expand=True)
                option_vars.append((flag, var, "text"))

        # =================================================================
        # -------- Advanced Options (ยุบ/ขยาย) --------
        # เก็บ Manual Options (before/after) ไว้ในนี้เพื่อไม่ให้หน้าต่างรก
        # auto-ขยายให้เองถ้า tool ไม่มี default option เลย (เช่น openssl enc)
        # =================================================================
        advanced_frame = ctk.CTkFrame(right, fg_color="transparent")

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
        switch_before_var = ctk.BooleanVar(value=False)
        before_container = ctk.CTkFrame(advanced_frame, fg_color="transparent")
        before_rows = []

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
                            args.append(f"{f} {v}")
                        else:
                            args.append(f)
            return " ".join(args)

        def add_before_row(opt_type="checkbox"):
            row = ctk.CTkFrame(before_container, fg_color="transparent")
            row.pack(fill="x", pady=2)

            flag_var = tk.StringVar()
            flag_var.trace_add("write", update_preview)
            flag_entry = ctk.CTkEntry(row, width=70, placeholder_text="-n", fg_color=INPUT_BG, border_color=BORDER_COLOR, text_color="white")
            flag_entry.pack(side="left", padx=(0, 5))
            flag_entry.configure(textvariable=flag_var)

            val_var = tk.StringVar()
            if opt_type == "text":
                val_var.trace_add("write", update_preview)
                val_entry = ctk.CTkEntry(row, placeholder_text="value", fg_color=INPUT_BG, border_color=BORDER_COLOR, text_color="white")
                val_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
                val_entry.configure(textvariable=val_var)
            else:
                lbl = ctk.CTkLabel(row, text="No Param", fg_color="#3498db", text_color="white", corner_radius=4, height=26)
                lbl.pack(side="left", fill="x", expand=True, padx=(0, 5))

            row_data = {"frame": row, "type": opt_type, "flag": flag_var, "val": val_var}
            before_rows.append(row_data)

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
        switch_after_var = ctk.BooleanVar(value=False)
        after_container = ctk.CTkFrame(advanced_frame, fg_color="transparent")
        after_rows = []

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
                            args.append(f"{f} {v}")
                        else:
                            args.append(f)
            return " ".join(args)

        def add_after_row(opt_type="checkbox"):
            row = ctk.CTkFrame(after_container, fg_color="transparent")
            row.pack(fill="x", pady=2)

            flag_var = tk.StringVar()
            flag_var.trace_add("write", update_preview)
            flag_entry = ctk.CTkEntry(row, width=70, placeholder_text="-n", fg_color=INPUT_BG, border_color=BORDER_COLOR, text_color="white")
            flag_entry.pack(side="left", padx=(0, 5))
            flag_entry.configure(textvariable=flag_var)

            val_var = tk.StringVar()
            if opt_type == "text":
                val_var.trace_add("write", update_preview)
                val_entry = ctk.CTkEntry(row, placeholder_text="value", fg_color=INPUT_BG, border_color=BORDER_COLOR, text_color="white")
                val_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
                val_entry.configure(textvariable=val_var)
            else:
                lbl = ctk.CTkLabel(row, text="No Param", fg_color="#3498db", text_color="white", corner_radius=4, height=26)
                lbl.pack(side="left", fill="x", expand=True, padx=(0, 5))

            row_data = {"frame": row, "type": opt_type, "flag": flag_var, "val": val_var}
            after_rows.append(row_data)

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

        def toggle_after():
            if switch_after_var.get():
                after_container.pack(after=switch_after, fill="x", pady=(0, 5))
            else:
                after_container.pack_forget()
            update_preview()

        switch_after = ctk.CTkSwitch(advanced_frame, text="Add Additional Arguments (After Input)", variable=switch_after_var, command=toggle_after, progress_color=ACCENT_GREEN, text_color="white", button_color=TEXT_DIM)
        switch_after.pack(anchor="w", pady=(10, 0))

        if not tool_options:
            # tool นี้ไม่มี option สำเร็จรูปเลย (เช่น openssl enc) ต้องพึ่ง manual options
            # อย่างเดียว เลยเปิด Advanced ให้อัตโนมัติจะได้ไม่ต้องเดา
            toggle_advanced()

        # -------- Command Preview --------
        preview_header = ctk.CTkFrame(right, fg_color="transparent")
        preview_header.pack(fill="x", padx=20, pady=(15, 0))

        ctk.CTkLabel(preview_header, text="Command Preview", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT_DIM).pack(side="left")

        preview_label = ctk.CTkLabel(right, text=tool_name, text_color=ACCENT_GREEN, font=ctk.CTkFont(family="Consolas", size=13), wraplength=320)
        preview_label.pack(anchor="w", padx=20, pady=5)

        input_entry.bind("<KeyRelease>", update_preview)
        update_preview()

        # -------- Description --------
        desc = node.get("user_description", "")
        if desc:
            ctk.CTkLabel(right, text="Description", font=ctk.CTkFont(weight="bold"), text_color=TEXT_DIM).pack(anchor="w", padx=20, pady=(10, 0))
            ctk.CTkLabel(right, text=desc, text_color=TEXT_DIM, wraplength=300).pack(anchor="w", padx=20)

        # -------- Run Tool --------
        def run_tool():
            # รวม options → params
            # ตรวจว่าเป็น file tool หรือ text tool
            # เรียก PipelineEngine
            # แสดง output
            params_list = []
            for flag, var, opt_type in option_vars:
                if opt_type == "checkbox":
                    if var.get():
                        params_list.append(flag)
                elif opt_type in ["text", "file"]:
                    val = var.get().strip()
                    if val:
                        params_list.append(f"{flag} {val}")

            params_before_fixed = " ".join(params_list)
            after_tool = preview_before_args() if switch_before_var.get() else ""
            after_input = preview_after_args() if switch_after_var.get() else ""

            params = " ".join(filter(None, [after_tool, params_before_fixed, after_input]))
            update_preview()

            if tool_name in self.engine.file_tools:
                # =====================================================
                # FILE TOOL
                # input_entry จะถูกเติมโดย
                # PREVIOUS / ORIGINAL / BROWSE
                # =====================================================

                path = input_entry.get().strip()

                # ถ้าช่อง path ว่าง
                # ลอง route previous_output อัตโนมัติอีกครั้ง
                if not path and previous_output:

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

                res = self.engine.run_file_tool(
                    tool_name,
                    path,
                    params
                )

            else:
                # =====================================================
                # TEXT TOOL
                # behavior เดิม
                # =====================================================

                inp_data = input_entry.get().strip()

                if not inp_data and previous_output:
                    input_bytes = previous_output
                else:
                    input_bytes = inp_data.encode("utf-8")

                res = self.engine.run_text_tool(
                    tool_name,
                    input_bytes,
                    params
                )
            result["output"] = res
            output_box.insert("end", f"\n>>> output ({tool_name})\n")
            output_box.insert("end", res.decode(errors="ignore") + "\n")
            output_box.see("end")

        # buttons
        ctk.CTkButton(
            right, text="Run", fg_color=ACCENT_GREEN, text_color="black",
            hover_color="#00CC33", command=run_tool
        ).pack(pady=(15, 5))

        def next_step(): # ปิด window แล้วส่ง output กลับ pipeline
            if result["output"] is None:
                return
            win.destroy()

        ctk.CTkButton(
            right,
            text="Close" if is_last else "Next",
            fg_color=BORDER_COLOR if is_last else ACCENT_CYAN,
            text_color="white" if is_last else "black",
            hover_color=CARD_COLOR if is_last else "#00CCCC",
            command=next_step
        ).pack()

        self.wait_window(win)

        return result["output"]

    #โหลด template pipeline สำเร็จรูป
    def load_template(self, template):
        self.clear_pipeline()

        if template == "Basic Recon":
            tools = ["file", "strings", "unique"]
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
    def load_tools_from_json(self):
        tools_path = os.path.join(os.path.dirname(__file__), "..", "Pipeline", "custom_tools.json")
        tools_path = os.path.abspath(tools_path)
        main_data = {}
        if os.path.exists(tools_path):
            with open(tools_path, "r", encoding="utf-8") as f:
                main_data = json.load(f)

        saved_path = os.path.join(os.path.dirname(__file__), "..", "Pipeline", "saved_pipelines.json")
        saved_path = os.path.abspath(saved_path)
        saved_list = []
        if os.path.exists(saved_path):
            try:
                with open(saved_path, "r", encoding="utf-8") as f:
                    content = json.load(f)
                    saved_list = content.get("saved_pipelines", [])
            except Exception as e:
                print(f"Error loading saved pipelines: {e}")

        categories = {"Saved Pipelines": []}

        if saved_list:
            categories["Saved Pipelines"] = [p["pipeline_name"] for p in saved_list]

        for category in main_data:
            if category == "saved_pipelines":
                continue
            if isinstance(main_data[category], list):
                categories[category] = [tool["name"] for tool in main_data[category]]

        return categories

    #refresh panel tool 
    def refresh_tools_panel(self):
        for widget in self.tools_panel.winfo_children():
            widget.destroy()

        tool_categories = self.load_tools_from_json()

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

    #เช็ค pipeline ที่เคย save
    def check_pipeline_status(self):
        saved_data = self.load_saved_pipelines()
        self.show_startup_popup(saved_data)

    # popup หน้าเริ่มต้น (Pipeline Manager)
    def show_startup_popup(self, saved_data):
        popup = ctk.CTkToplevel(self)
        popup.title("Pipeline Manager")
        popup.geometry("400x420")
        popup.attributes("-topmost", True)
        popup.configure(fg_color=BG_COLOR)

        ctk.CTkLabel(
            popup, text=">_ UNIT PIPELINE", font=("Consolas", 20, "bold"), text_color=ACCENT_CYAN
        ).pack(pady=(20, 5))

        def create_new():
            popup.destroy()
            self.open_pipeline_wizard()

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
    def load_saved_pipelines(self):
        save_path = os.path.join(os.path.dirname(__file__), "..", "Pipeline", "saved_pipelines.json")
        save_path = os.path.abspath(save_path)

        if os.path.exists(save_path):
            try:
                with open(save_path, "r", encoding="utf-8") as f:
                    return json.load(f).get("saved_pipelines", [])
            except Exception:
                pass
        return []

    # แสดงจำนวน pipeline (debug)
    def show_saved_pipelines_list(self, saved_data):
        print(f"You have {len(saved_data)} saved pipelines available in the sidebar.")

    # Wizard สร้าง pipeline
    def open_pipeline_wizard(self, current_step=1, pipeline_data=None):
        if pipeline_data is None:
            pipeline_data = []

        wizard = ctk.CTkToplevel(self)
        wizard.title(f"Create Pipeline - Step {current_step}")
        wizard.geometry("520x650")
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
        def open_add_option_popup():
            popup = ctk.CTkToplevel(wizard)
            popup.title("Add Custom Option")
            popup.geometry("620x350")
            popup.attributes("-topmost", True)
            popup.configure(fg_color=BG_COLOR)

            ctk.CTkLabel(popup, text="Add Custom Option", font=("Consolas", 14, "bold"), text_color=ACCENT_CYAN).pack(pady=(10, 0))

            preview_label = ctk.CTkLabel(popup, text="Preview: ...", text_color=ACCENT_GREEN, font=ctk.CTkFont(family="Consolas", size=13))
            preview_label.pack(pady=(5, 10))

            options_container = ctk.CTkScrollableFrame(popup, fg_color="transparent", height=150)
            options_container.pack(fill="both", expand=True, padx=10)

            option_rows = []

            # อัปเดตพรีวิวแบบ Real-time ทันทีที่พิมพ์
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
    def finalize_wizard_pipeline(self, pipeline_data, pipeline_name):
        self.clear_pipeline()
        for tool_info in pipeline_data:
            self.add_tool_node(tool_info["name"], user_desc=tool_info.get("user_description", ""))
            if self.nodes:
                self.nodes[-1]["params"] = tool_info.get("params", "")
                self.nodes[-1]["options"] = tool_info.get("options", [])

        save_path = os.path.join(os.path.dirname(__file__), "..", "Pipeline", "saved_pipelines.json")
        save_path = os.path.abspath(save_path)

        try:
            data = {"saved_pipelines": []}
            if os.path.exists(save_path):
                with open(save_path, "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                        if "saved_pipelines" not in data:
                            data["saved_pipelines"] = []
                    except json.JSONDecodeError:
                        data = {"saved_pipelines": []}

            new_entry = {
                "pipeline_name": pipeline_name,
                "steps": pipeline_data
            }
            data["saved_pipelines"].append(new_entry)

            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            self.refresh_tools_panel()
            print(f"Saved pipeline '{pipeline_name}' successfully!")

        except Exception as e:
            print(f"Error saving pipeline: {e}")

    # โหลด pipeline มาแสดงบน canvas
    def load_saved_pipeline_to_canvas(self, pipeline_name):
        save_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "Pipeline",
            "saved_pipelines.json"
        )
        save_path = os.path.abspath(save_path)

        if not os.path.exists(save_path):
            return

        with open(save_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for p in data.get("saved_pipelines", []):
            if p["pipeline_name"] == pipeline_name:
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
                break

    # popup เพิ่ม tool ใหม่
    def open_add_tool_window(self):
        win = ctk.CTkToplevel(self)
        win.title("Add Tool")
        win.geometry("300x250")
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

        def save_tool():
            name = name_entry.get()
            cmd = cmd_entry.get()
            mode = mode_var.get()

            if not name or not cmd:
                return

            self.engine.add_tool(name, cmd, mode)
            win.destroy()

        ctk.CTkButton(
            win, text="Add Tool", command=save_tool,
            fg_color=ACCENT_GREEN, text_color="black", hover_color="#00CC33"
        ).pack(pady=10)