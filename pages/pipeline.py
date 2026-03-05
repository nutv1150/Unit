import json

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
from Pipeline.pipeline_engine import PipelineEngine
import tempfile
import os


class PipelinePage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.run_logs = []
        self.engine = PipelineEngine()

        self.configure(fg_color="#ececec")
        self.nodes = []      # เก็บข้อมูล Node ทั้งหมด
        self.node_count = 0
        self.is_auto = False

        # --- Header ---
        self.title_label = ctk.CTkLabel(self, text="Pipeline", font=ctk.CTkFont(size=22, weight="bold"), text_color="black")
        self.title_label.pack(anchor="w", padx=20, pady=(10, 5))
        
        self.content_row = ctk.CTkFrame(self, fg_color="transparent")
        self.content_row.pack(fill="both", expand=True, padx=20, pady=20)

        # --- Tools Panel (ด้านซ้าย) ---
        self.tools_panel = ctk.CTkScrollableFrame(
            self.content_row,
            fg_color="#f7f7f7",
            width=230,
            corner_radius=10
        )

        self.tools_panel.pack(side="left", fill="y", padx=(0, 15))
        self.tools_panel.configure(height=600)

        ctk.CTkLabel(self.tools_panel, text="All Tools", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(15, 10), padx=15, anchor="w")

        tool_categories = self.load_tools_from_json()

        for cat, tools in tool_categories.items():
            ctk.CTkLabel(self.tools_panel, text=cat, font=ctk.CTkFont(size=13, weight="bold")).pack(padx=15, anchor="w", pady=(5,0))
            for tool in tools:
                lbl = ctk.CTkLabel(self.tools_panel, text=f"  • {tool}", font=ctk.CTkFont(size=12), cursor="hand2")
                lbl.pack(padx=15, anchor="w")
                lbl.bind("<Button-1>", lambda e, t=tool: self.add_tool_node(t))

        self.add_btn = ctk.CTkButton(self.tools_panel,text="+ Add Tools",command=self.open_add_tool_window, fg_color="transparent", border_width=1, border_color="#ccc", text_color="black", hover_color="#eee")
        self.add_btn.pack(fill="x", padx=15, pady=20)

        # --- Work Area (ตรงกลาง) ---
        self.work_area = ctk.CTkFrame(self.content_row, fg_color="white", corner_radius=10)
        self.work_area.pack(side="left", fill="both", expand=True)

        # --- Top Controls (ใส่ปุ่มให้ครบตามรูป) ---
        self.controls = ctk.CTkFrame(self.work_area, fg_color="transparent")
        self.controls.pack(fill="x", padx=15, pady=15)

        self.step_btn = ctk.CTkButton(self.controls, text="Step-by-Step", fg_color="#4f87ff", width=100,command=self.toggle_mode)
        self.step_btn.pack(side="left", padx=2)


        # Run
        self.run_btn = ctk.CTkButton(
            self.controls,
            text="Run All",
            fg_color="#dcdcdc",
            text_color="black",
            width=80,
            hover_color="#ccc",
            command=self.run_pipeline
        )
        self.run_btn.pack(side="left", padx=2)

        

        # Clear
        self.clear_btn = ctk.CTkButton(
            self.controls,
            text="Clear",
            fg_color="#dcdcdc",
            text_color="black",
            width=80,
            hover_color="#ccc",
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
            command=self.load_template
        )

        self.template_opt.pack(side="left", padx=2)

        # --- Canvas Area (จุดที่ต้องแก้ Error line_canvas) ---
        self.canvas_container = ctk.CTkFrame(self.work_area, fg_color="#1a1a1a", corner_radius=8)
        self.canvas_container.pack(fill="both", expand=True, padx=15)

        # สร้าง Canvas สำหรับวาดเส้นเชื่อม
        self.line_canvas = tk.Canvas(self.canvas_container, bg="#1a1a1a", highlightthickness=0)
        self.line_canvas.pack(fill="both", expand=True)

        self.placeholder = ctk.CTkLabel(self.line_canvas, text="Pipeline Flow Canvas Area", text_color="#555")
        self.placeholder.place(relx=0.5, rely=0.5, anchor="center")

            
    # --- ฟังก์ชันสลับโหมด ---
    def toggle_mode(self):
        self.is_auto = not self.is_auto # สลับสถานะ True/False
        
        if self.is_auto:
            # เปลี่ยนเป็นโหมด Auto
            self.step_btn.configure(text="Auto Mode", fg_color="#2eb85c") # เปลี่ยนเป็นสีเขียว
            print("Switched to Auto Mode")
            # คุณสามารถเพิ่ม Logic การรันแบบอัตโนมัติที่นี่ได้
        else:
            # เปลี่ยนกลับเป็น Step-by-Step
            self.step_btn.configure(text="Step-by-Step", fg_color="#4f87ff") # กลับเป็นสีฟ้า
            print("Switched to Step-by-Step Mode")
    # --- ฟังก์ชันจัดการ Node ---
    def add_tool_node(self, tool_name):
        if self.node_count == 0:
            self.placeholder.place_forget()

        self.node_count += 1
        
        # สร้าง Frame สำหรับ Node แบบลอยตัว
        node = ctk.CTkFrame(self.line_canvas, fg_color="#333333", corner_radius=4, border_width=1, border_color="#6f63ff", width=110, height=35)
        
        # วางตำแหน่งแบบสุ่มเล็กน้อยตามลำดับ
        x_pos = 50 + (len(self.nodes) * 160)
        y_pos = 50 + ((len(self.nodes) % 3) * 60)
        node.place(x=x_pos, y=y_pos)

        lbl = ctk.CTkLabel(node, text=tool_name, font=ctk.CTkFont(size=11, weight="bold"), text_color="white")
        lbl.place(relx=0.5, rely=0.5, anchor="center")
        
        # วาดจุด Socket (วงกลมเล็กๆ ซ้ายขวา)
        ctk.CTkFrame(node, width=6, height=6, corner_radius=3, fg_color="#555").place(relx=0, rely=0.5, anchor="center")
        ctk.CTkFrame(node, width=6, height=6, corner_radius=3, fg_color="#6f63ff").place(relx=1, rely=0.5, anchor="center")

        node_data = {
            'frame': node, 
            'name': tool_name,
            'params': "",
        }
        self.nodes.append(node_data)

        # ทำให้ลากได้
        for item in [node, lbl]:
            item.bind("<Button-1>", lambda e, n=node_data: self.on_node_press(e, n))
            item.bind("<B1-Motion>", lambda e, n=node_data: self.on_node_drag(e, n))

        self.draw_connections()

    def on_node_press(self, event, node_data):

        self.current_node = node_data

        node_data['drag_data'] = {
            'x': event.x,
            'y': event.y
        }

        node_data['frame'].lift()

    def on_node_drag(self, event, node_data):

        if 'drag_data' not in node_data:
            return

        deltax = event.x - node_data['drag_data']['x']
        deltay = event.y - node_data['drag_data']['y']

        new_x = node_data['frame'].winfo_x() + deltax
        new_y = node_data['frame'].winfo_y() + deltay

        node_data['frame'].place(x=new_x, y=new_y)

        self.draw_connections()

    def draw_connections(self):
        self.line_canvas.delete("line")
        # วาดเส้นเฉพาะเมื่อมี Node ตั้งแต่ 2 อันขึ้นไปเท่านั้น (ป้องกันเส้นดีด)
        if len(self.nodes) < 2: return

        for i in range(len(self.nodes) - 1):
            n1 = self.nodes[i]['frame']
            n2 = self.nodes[i+1]['frame']
            
            # จุดปล่อย (ขวา) และ จุดรับ (ซ้าย)
            x1 = n1.winfo_x() + n1.winfo_width()
            y1 = n1.winfo_y() + (n1.winfo_height() / 2)
            x2 = n2.winfo_x()
            y2 = n2.winfo_y() + (n2.winfo_height() / 2)
            
            # ใช้พิกัดสัมพัทธ์เพื่อให้เส้นไม่เอ๋อตอนกำลังลาก
            if x1 < 10 or x2 < 10: continue # ข้ามถ้าพิกัดยังไม่อัปเดต

            # วาดเส้นโค้ง Bezier (เพิ่มจุดดัดกลาง)
            dist = abs(x2 - x1) / 2
            self.line_canvas.create_line(
                x1, y1, x1 + dist, y1, x2 - dist, y2, x2, y2,
                fill="#6f63ff", width=2, smooth=True, tags="line", arrow=tk.LAST
            )
    def run_pipeline(self):

        if not self.nodes:
            return

        file_path = filedialog.askopenfilename(
            title="Select CTF File"
        )

        if not file_path:
            return

        # อ่านไฟล์เป็น data ตั้งแต่ต้น
        with open(file_path, "rb") as f:
            original_data = f.read()
        current_data = original_data

        self.run_logs = []

        for i, node in enumerate(self.nodes):

            tool = node["name"]

            is_last = (i == len(self.nodes) - 1)

            engine = self.engine

            # ถ้าเป็น file tool → run ทันที
            if tool in engine.file_tools:

                if isinstance(current_data, bytes):
                    temp_file = self.write_temp_file(current_data)
                    output = engine.run_file_tool(tool, temp_file)
                    os.remove(temp_file)
                else:
                    output = engine.run_file_tool(tool, file_path)

            # ถ้าเป็น text tool → เปิด step window
            else:

                output = self.open_step_window(
                    tool,
                    current_data,
                    original_data,
                    self.run_logs,
                    is_last
                )

            if output is None:
                return

            self.run_logs.append({
                "tool": tool,
                "output": output
            })

            current_data = output
    # วางนอก __init__ นะ
   

    def clear_pipeline(self):
        print("Clearing pipeline...")

        for node in self.nodes:
            node['frame'].destroy()

        self.nodes.clear()
        self.node_count = 0
        self.line_canvas.delete("line")

    def write_temp_file(self, data):
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.write(data)
        tmp.close()
        return tmp.name
    
    def open_step_window(self, tool_name, previous_output, original_data, logs, is_last):

        win = ctk.CTkToplevel(self)
        win.title(f"{tool_name} Step")
        win.geometry("900x450")

        container = ctk.CTkFrame(win)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # LEFT PANEL (previous output)
        left = ctk.CTkFrame(container)
        left.pack(side="left", fill="both", expand=True, padx=(0,5))

        ctk.CTkLabel(left, text="Pipeline Output History").pack(anchor="w", padx=10)

        output_box = ctk.CTkTextbox(left)
        output_box.pack(fill="both", expand=True, padx=10, pady=10)

        output_box.insert("end", ">>> original input\n")

        try:
            orig_preview = original_data[:2000].decode(errors="ignore")
        except:
            orig_preview = str(original_data)

        output_box.insert("end", orig_preview + "\n")

        # แสดง log ทุก step
        for log in logs:

            tool = log["tool"]
            out = log["output"]

            if isinstance(out, bytes):
                try:
                    out = out.decode()
                except:
                    out = out.decode(errors="ignore")

            output_box.insert("end", f"\n>>> {tool}\n")
            output_box.insert("end", out + "\n")


        # Go to Input button
        def send_to_input():
            try:
                selected = output_box.get("sel.first", "sel.last")
                input_entry.delete(0, "end")
                input_entry.insert(0, selected.strip())
            except:
                pass

        ctk.CTkButton(
            left,
            text="Go to Input",
            command=send_to_input
        ).pack(pady=5)

        # RIGHT PANEL (tool run)
        right = ctk.CTkFrame(container)
        right.pack(side="left", fill="both", expand=True, padx=(5,0))

        ctk.CTkLabel(right, text=tool_name, font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)

        ctk.CTkLabel(right, text="Input").pack(anchor="w", padx=20)
        input_entry = ctk.CTkEntry(right)
        input_entry.pack(fill="x", padx=20, pady=5)
        # auto fill previous output
        if isinstance(previous_output, bytes):
            try:
                preview = previous_output.decode(errors="ignore")[:500]
                input_entry.insert(0, preview)
            except:
                pass

        ctk.CTkLabel(right, text="Parameter").pack(anchor="w", padx=20)
        param_entry = ctk.CTkEntry(right)
        param_entry.pack(fill="x", padx=20, pady=5)

        result = {"output": None}

        def run_tool():

            params = param_entry.get()

            input_data = previous_output

            if isinstance(input_data, str):
                input_data = input_data.encode()

            engine = self.engine

            if tool_name in engine.text_tools:

                output = engine.run_text_tool(
                    tool_name,
                    input_data,
                    params
                )

            elif tool_name in engine.file_tools:

                if isinstance(previous_output, bytes):
                    temp_file = self.write_temp_file(previous_output)
                    output = engine.run_file_tool(tool_name, temp_file, params)
                    os.remove(temp_file)
                else:
                    output = engine.run_file_tool(tool_name, previous_output, params)

            else:
                output = b"Unknown tool"

            result["output"] = output

            # แปลง output เป็น text
            try:
                out_text = output.decode()
            except:
                out_text = output.decode(errors="ignore")

            # ถ้าเป็น step สุดท้าย → แสดง Final Output
            if is_last:
                output_box.insert("end", f"\n>>> {tool_name} (final output)\n")
                output_box.insert("end", out_text + "\n")
                output_box.see("end")
            else:
                win.destroy()
        ctk.CTkButton(
            right,
            text="Run",
            fg_color="#4caf50",
            command=run_tool
        ).pack(pady=20)

        ctk.CTkButton(
            right,
            text="Close",
            fg_color="#666",
            command=win.destroy
        ).pack(pady=5)

        self.wait_window(win)

        return result["output"]
    
    def open_add_tool_window(self):

        win = ctk.CTkToplevel(self)
        win.title("Add Tool")
        win.geometry("300x300")

        ctk.CTkLabel(win, text="Tool Name").pack(pady=5)
        name_entry = ctk.CTkEntry(win)
        name_entry.pack(pady=5)

        ctk.CTkLabel(win, text="Linux Command").pack(pady=5)
        cmd_entry = ctk.CTkEntry(win)
        cmd_entry.pack(pady=5)

        mode_var = ctk.StringVar(value="text")
        ctk.CTkOptionMenu(
            win,
            values=["text", "file"],
            variable=mode_var
        ).pack(pady=5)

        categories = list(self.load_tools_from_json().keys())

        category_var = ctk.StringVar(value=categories[0])

        ctk.CTkOptionMenu(
            win,
            values=categories,
            variable=category_var
        ).pack(pady=5)

        def save_tool():

            name = name_entry.get()
            cmd = cmd_entry.get()
            mode = mode_var.get()
            category = category_var.get()

            self.engine.add_tool(name, cmd, mode)

            self.engine.save_custom_tool(
                name,
                cmd,
                mode,
                category
            )

            lbl = ctk.CTkLabel(
                self.tools_panel,
                text=f"  • {name}",
                cursor="hand2"
            )

            lbl.pack(anchor="w", padx=15)

            lbl.bind("<Button-1>", lambda e, t=name: self.add_tool_node(t))
            self.refresh_tools_panel()

            win.destroy()

        ctk.CTkButton(win, text="Add Tool", command=save_tool).pack(pady=10)

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

    def load_tools_from_json(self):

        json_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "Pipeline",
            "custom_tools.json"
        )

        json_path = os.path.abspath(json_path)

        if not os.path.exists(json_path):
            return {}

        with open(json_path, "r") as f:
            data = json.load(f)

        categories = {}

        for category in data:
            categories[category] = [tool["name"] for tool in data[category]]

        return categories
    

    def refresh_tools_panel(self):

        for widget in self.tools_panel.winfo_children():
            widget.destroy()

        tool_categories = self.load_tools_from_json()

        for cat, tools in tool_categories.items():

            ctk.CTkLabel(
                self.tools_panel,
                text=cat,
                font=ctk.CTkFont(size=13, weight="bold")
            ).pack(anchor="w", padx=15)

            for tool in tools:

                lbl = ctk.CTkLabel(
                    self.tools_panel,
                    text=f"  • {tool}",
                    cursor="hand2"
                )

                lbl.pack(anchor="w", padx=15)

                lbl.bind("<Button-1>", lambda e, t=tool: self.add_tool_node(t))