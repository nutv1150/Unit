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

            ctk.CTkLabel(
                self.tools_panel,
                text=cat,
                font=ctk.CTkFont(size=13, weight="bold")
            ).pack(padx=15, anchor="w", pady=(5,0))

            for tool in tools:

                lbl = ctk.CTkLabel(
                    self.tools_panel,
                    text=f"  • {tool}",
                    font=ctk.CTkFont(size=12),
                    cursor="hand2"
                )

                lbl.pack(padx=15, anchor="w")

                if cat == "Saved Pipelines":

                    lbl.bind(
                        "<Button-1>",
                        lambda e, name=tool: self.load_saved_pipeline_to_canvas(name)
                    )

                else:

                    lbl.bind(
                        "<Button-1>",
                        lambda e, t=tool: self.add_tool_node(t)
                    )

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

        self.bind("<Visibility>", self.on_show_page)

    def on_show_page(self, event):
        # ตรวจสอบว่ามีโหนดอยู่แล้วหรือไม่ เพื่อไม่ให้วิซาดเด้งซ้ำถ้าผู้ใช้สร้างไปแล้ว
        if not self.nodes:
            self.check_pipeline_status()
        
        # ยกเลิกการผูกเพื่อไม่ให้เด้งทุกครั้งที่สลับหน้าไปมา (ถ้าต้องการให้เด้งแค่ครั้งแรกที่เข้าหน้า)
        self.unbind("<Visibility>")
            
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
    def add_tool_node(self, tool_name, user_desc=""): 
        if self.node_count == 0:
            self.placeholder.place_forget()

        self.node_count += 1
        
        # ใช้ความสูงคงที่ (35) เพราะไม่ต้องแสดง Note แล้ว
        node = ctk.CTkFrame(self.line_canvas, fg_color="#333333", corner_radius=4, 
                            border_width=1, border_color="#6f63ff", width=110, height=35)
        
        x_pos = 50 + (len(self.nodes) * 160)
        y_pos = 50 + ((len(self.nodes) % 3) * 60)
        node.place(x=x_pos, y=y_pos)

        # ชื่อเครื่องมือ วางไว้ตรงกลาง Node
        lbl = ctk.CTkLabel(node, text=tool_name, font=ctk.CTkFont(size=11, weight="bold"), text_color="white")
        lbl.place(relx=0.5, rely=0.5, anchor="center")
        
        # วาดจุด Socket เชื่อมต่อเส้น
        ctk.CTkFrame(node, width=6, height=6, corner_radius=3, fg_color="#555").place(relx=0, rely=0.5, anchor="center")
        ctk.CTkFrame(node, width=6, height=6, corner_radius=3, fg_color="#6f63ff").place(relx=1, rely=0.5, anchor="center")

        node_data = {
            'frame': node,
            'name': tool_name,
            'params': "",
            'user_description': user_desc,
            'options': []
        }
        self.nodes.append(node_data)

        # ทำให้ Node ลากวางได้
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

        current_data = b""
        self.run_logs = []

        for i, node in enumerate(self.nodes):

            tool = node["name"]
            is_last = (i == len(self.nodes) - 1)

            output = self.open_step_window(
                node,
                current_data,
                current_data,
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
    
    def open_step_window(self, node, previous_output, original_data, logs, is_last):

        tool_name = node["name"]

        win = ctk.CTkToplevel(self)
        win.title(f"{tool_name} Step")
        win.geometry("1000x620")

        container = ctk.CTkFrame(win)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # ---------------- LEFT PANEL ----------------
        left = ctk.CTkFrame(container, width=520)
        left.pack(side="left", fill="both", expand=True, padx=(0,5))

        ctk.CTkLabel(left, text="Pipeline Output History",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10,0))

        output_box = ctk.CTkTextbox(left)
        output_box.pack(fill="both", expand=True, padx=10, pady=10)

        # --- Context Menu (Right Click) ---

        def send_selected_to_input():
            try:
                selected = output_box.get("sel.first", "sel.last")
                input_entry.delete(0, "end")
                input_entry.insert(0, selected.strip())
            except:
                pass

        context_menu = tk.Menu(output_box, tearoff=0)

        context_menu.add_command(
            label="Send to Input",
            command=send_selected_to_input
        )

        def show_context_menu(event):
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()

        output_box.bind("<Button-3>", show_context_menu)

        result = {"output": None}

        # original preview
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

        # save output
        def save_output():
            if result["output"] is None:
                return

            path = filedialog.asksaveasfilename(defaultextension=".txt")

            if path:
                with open(path,"wb") as f:
                    f.write(result["output"])

        ctk.CTkButton(left,text="Save Output as File",
            command=save_output).pack(pady=5)

        # ---------------- RIGHT PANEL ----------------
        right = ctk.CTkFrame(container, width=380)
        right.pack(side="left", fill="y", padx=(5,0))

        # tool title
        ctk.CTkLabel(
            right,
            text=tool_name,
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)

        # -------- Input --------
        ctk.CTkLabel(right,text="Input").pack(anchor="w", padx=20)

        input_frame = ctk.CTkFrame(right, fg_color="transparent")
        input_frame.pack(fill="x", padx=20, pady=5)

        input_entry = ctk.CTkEntry(input_frame)
        input_entry.pack(side="left", fill="x", expand=True)

        def browse_file():
            path = filedialog.askopenfilename()
            if path:
                input_entry.delete(0,"end")
                input_entry.insert(0,path)

        ctk.CTkButton(
            input_frame,
            text="Browse",
            width=80,
            command=browse_file
        ).pack(side="right", padx=5)

        # auto fill previous
        if isinstance(previous_output, bytes):
            try:
                preview = previous_output.decode(errors="ignore")[:500]
                input_entry.insert(0,preview)
            except:
                pass

        # -------- Options --------
        # -------- Options --------
        ctk.CTkLabel(right, text="Options").pack(anchor="w", padx=20)

        options_frame = ctk.CTkFrame(right, fg_color="transparent")
        options_frame.pack(fill="x", padx=20, pady=5)

        option_vars = []
        tool_options = node.get("options") or self.engine.tool_options.get(tool_name, [])

        def update_preview(*args): # ใส่ *args เผื่อเวลากล่อง text มีการพิมพ์
            params_list = []

            for flag, var, opt_type in option_vars:
                if opt_type == "checkbox":
                    if var.get():
                        params_list.append(flag)
                elif opt_type in ["text", "file"]:
                    val = var.get().strip()
                    if val:
                        params_list.append(f"{flag} {val}") # เอา flag กับค่าที่พิมพ์มาต่อกัน

            params_before = " ".join(params_list)
            inp = input_entry.get().strip()
            after_tool = after_tool_entry.get().strip()
            after_input = after_input_entry.get().strip()

            cmd = tool_name
            if after_tool:
                cmd += f" {after_tool}"
            if params_before:
                cmd += f" {params_before}"
            if inp:
                cmd += f" {inp}"
            if after_input:
                cmd += f" {after_input}"

            preview_label.configure(text=cmd)

        # วาด UI ตามประเภทของ Option (วาดได้ทั้ง checkbox และ text)
        for opt in tool_options:
            flag = opt["flag"]
            desc = opt.get("description", "")
            opt_type = opt["type"]

            row = ctk.CTkFrame(options_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)

            if opt_type == "checkbox":
                var = tk.BooleanVar()
                chk = ctk.CTkCheckBox(row, text=f"{flag} ({desc})", variable=var, command=update_preview)
                chk.pack(anchor="w")
                option_vars.append((flag, var, "checkbox"))
                
            elif opt_type in ["text", "file"]:
                # ถ้าเป็น text ให้โชว์ชื่อ Flag แล้วสร้างกล่อง Textbox ให้พิมพ์ค่า
                ctk.CTkLabel(row, text=f"{flag} ({desc}):").pack(side="left", padx=(0, 5))
                var = tk.StringVar()
                var.trace_add("write", update_preview) # ให้พรีวิวอัปเดตทันทีที่พิมพ์ข้อความ
                ent = ctk.CTkEntry(row, textvariable=var, width=120)
                ent.pack(side="left", fill="x", expand=True)
                option_vars.append((flag, var, "text"))

        # -------- Parameters After Tool (เปลี่ยนชื่อตามที่อาจารย์แนะนำ) --------
        # -------- สวิตช์เปิด/ปิด Manual Options (Before Input) --------
        switch_before_var = ctk.BooleanVar(value=False)
        
        def toggle_before():
            if switch_before_var.get():
                # ถ้าเปิดสวิตช์ ให้โชว์ช่องกรอกข้อความ
                after_tool_entry.pack(after=switch_before, fill="x", padx=20, pady=(0, 5))
            else:
                # ถ้าปิด ให้ซ่อน และลบข้อความทิ้ง
                after_tool_entry.pack_forget()
                after_tool_entry.delete(0, 'end') 
            update_preview()

        switch_before = ctk.CTkSwitch(right, text="Add Manual Options (Before Input)", 
                                      variable=switch_before_var, command=toggle_before, progress_color="#2eb85c")
        switch_before.pack(anchor="w", padx=20, pady=(15, 5))
        
        after_tool_entry = ctk.CTkEntry(right, placeholder_text="example: -a -t x")
        after_tool_entry.bind("<KeyRelease>", update_preview)


        # -------- สวิตช์เปิด/ปิด Additional Arguments (After Input) --------
        switch_after_var = ctk.BooleanVar(value=False)

        def toggle_after():
            if switch_after_var.get():
                # ถ้าเปิดสวิตช์ ให้โชว์ช่องกรอกข้อความ
                after_input_entry.pack(after=switch_after, fill="x", padx=20, pady=(0, 5))
            else:
                # ถ้าปิด ให้ซ่อน และลบข้อความทิ้ง
                after_input_entry.pack_forget()
                after_input_entry.delete(0, 'end')
            update_preview()

        switch_after = ctk.CTkSwitch(right, text="Add Additional Arguments (After Input)", 
                                     variable=switch_after_var, command=toggle_after, progress_color="#2eb85c")
        switch_after.pack(anchor="w", padx=20, pady=(10, 5))
        
        after_input_entry = ctk.CTkEntry(right, placeholder_text="example: -T fields -e data")
        after_input_entry.bind("<KeyRelease>", update_preview)

        # -------- Command Preview --------
        preview_header = ctk.CTkFrame(right, fg_color="transparent")
        preview_header.pack(fill="x", padx=20, pady=(15, 0))

        ctk.CTkLabel(
            preview_header, 
            text="Command Preview", 
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(side="left")

        # เพิ่มปุ่ม Show Command ตามที่คุณต้องการ
        ctk.CTkButton(
            preview_header,
            text="Show Command",
            width=100,
            height=24,
            fg_color="#f39c12",
            hover_color="#e67e22",
            command=update_preview
        ).pack(side="right")

        # เปลี่ยนสีตัวหนังสือ Preview ให้เป็นสีเขียว (สไตล์ Command Line)
        preview_label = ctk.CTkLabel(
            right, 
            text=tool_name, 
            text_color="#2eb85c", 
            font=("Courier", 13, "italic"),
            wraplength=320
        )
        preview_label.pack(anchor="w", padx=20, pady=5)
        
        # ผูกให้ช่อง Input (ถ้ามีการพิมพ์หรือลบ) อัปเดต Command ด้วย
        input_entry.bind("<KeyRelease>", update_preview)
        
        # รันพรีวิวครั้งแรก
        update_preview()

        # -------- Description --------
        desc = node.get("user_description","")
        if desc:
            ctk.CTkLabel(right, text="Description", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(10,0))
            ctk.CTkLabel(right, text=desc, text_color="gray", wraplength=300).pack(anchor="w", padx=20)

        # -------- Run Tool --------
        def run_tool():
            params_list = []
            
            # ต้องแก้การดึงค่าตอนรันด้วย ให้รองรับทั้ง checkbox และ text
            for flag, var, opt_type in option_vars:
                if opt_type == "checkbox":
                    if var.get():
                        params_list.append(flag)
                elif opt_type in ["text", "file"]:
                    val = var.get().strip()
                    if val:
                        params_list.append(f"{flag} {val}")

            params_before = " ".join(params_list)
            after_tool = after_tool_entry.get().strip()
            after_input = after_input_entry.get().strip()

            params = " ".join(filter(None,[after_tool, params_before, after_input]))
            update_preview()

        # buttons
        ctk.CTkButton(
            right,
            text="Run",
            fg_color="#4caf50",
            command=run_tool
        ).pack(pady=(15,5))

        def next_step():

            if result["output"] is None:
                return

            win.destroy()

        ctk.CTkButton(
            right,
            text="Close" if is_last else "Next",
            fg_color="#4f87ff" if not is_last else "#666",
            command=next_step
        ).pack()

        self.wait_window(win)

        return result["output"]

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
        # 1. โหลดเครื่องมือหลักจาก custom_tools.json
        tools_path = os.path.join(os.path.dirname(__file__), "..", "Pipeline", "custom_tools.json")
        tools_path = os.path.abspath(tools_path)
        main_data = {}
        if os.path.exists(tools_path):
            with open(tools_path, "r", encoding="utf-8") as f:
                main_data = json.load(f)

        # 2. โหลด Saved Pipelines จาก saved_pipelines.json
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

        # 3. รวมหมวดหมู่
        categories = {}
        
        # แทรก Saved Pipelines ไว้ด้านบนสุด
        if saved_list:
            categories["Saved Pipelines"] = [p["pipeline_name"] for p in saved_list]

        # ดึงหมวดหมู่เครื่องมืออื่นๆ (ป้องกันกรณีมีคีย์ saved_pipelines หลงอยู่ใน custom_tools)
        for category in main_data:
            if category == "saved_pipelines":
                continue
            if isinstance(main_data[category], list):
                categories[category] = [tool["name"] for tool in main_data[category]]

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

                # ในฟังก์ชัน refresh_tools_panel ตรงลูปที่สร้าง lbl ให้แก้เป็น:
                if cat == "Saved Pipelines":
                    lbl.bind("<Button-1>", lambda e, name=tool: self.load_saved_pipeline_to_canvas(name))
                else:
                    lbl.bind("<Button-1>", lambda e, t=tool: self.add_tool_node(t))
        
    def check_pipeline_status(self):
        # โหลดข้อมูลที่เคยเซฟไว้
        saved_data = self.load_saved_pipelines()
        
        # เปิดหน้าต่าง Pop-up ต้อนรับ
        self.show_startup_popup(saved_data)
    
    def show_startup_popup(self, saved_data):
        # สร้างหน้าต่าง Pop-up และเพิ่มความสูงเป็น 400x420
        popup = ctk.CTkToplevel(self)
        popup.title("Pipeline Manager")
        popup.geometry("400x420")
        popup.attributes("-topmost", True) # ให้อยู่หน้าสุดเสมอ

        ctk.CTkLabel(popup, text="UNIT Pipeline", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(20, 5))

        # ฟังก์ชันเมื่อกดสร้างใหม่
        def create_new():
            popup.destroy() # ปิด Pop-up นี้
            self.open_pipeline_wizard() # ไปเปิดหน้า Wizard Step 1

        # ฟังก์ชันเมื่อกดเปิดของเก่า
        def load_existing(p_name):
            popup.destroy() # ปิด Pop-up นี้
            self.load_saved_pipeline_to_canvas(p_name) # วาดโหนดลง Canvas

        # ---------------------------------------------------------
        # 1. สร้างปุ่ม "+ Create New Pipeline" ล็อคไว้ด้านล่างสุดเสมอ
        # ---------------------------------------------------------
        bottom_frame = ctk.CTkFrame(popup, fg_color="transparent")
        bottom_frame.pack(side="bottom", fill="x", pady=20)
        
        ctk.CTkButton(bottom_frame, text="+ Create New Pipeline", fg_color="#6f63ff", 
                      font=ctk.CTkFont(weight="bold"), height=40, command=create_new).pack()

        # ---------------------------------------------------------
        # 2. ส่วนแสดงรายชื่อ (ตรงกลาง)
        # ---------------------------------------------------------
        content_frame = ctk.CTkFrame(popup, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=30)

        if not saved_data:
            # กรณีไม่มี Pipeline เก่าเลย
            ctk.CTkLabel(content_frame, text="ยังไม่มี Pipeline ที่บันทึกไว้\nเริ่มต้นสร้างชุดคำสั่งแรกของคุณได้เลย", 
                         text_color="gray").pack(pady=40)
        else:
            # กรณีมี Pipeline เก่า โชว์รายชื่อ
            ctk.CTkLabel(content_frame, text="เลือกเปิด Pipeline หรือสร้างใหม่", text_color="gray").pack(pady=(0, 10))
            
            # กล่อง Scroll สำหรับใส่รายชื่อ (ให้ยืดหยุ่นตามพื้นที่ที่เหลือ)
            list_frame = ctk.CTkScrollableFrame(content_frame, fg_color="#e6e6e6", corner_radius=10)
            list_frame.pack(fill="both", expand=True)

            for p in saved_data:
                p_name = p.get("pipeline_name", "Untitled Pipeline")
                
                row = ctk.CTkFrame(list_frame, fg_color="transparent")
                row.pack(fill="x", pady=5)
                
                ctk.CTkLabel(row, text=f"📄 {p_name}", font=ctk.CTkFont(weight="bold"), text_color="#333").pack(side="left", padx=10)
                
                # ปุ่ม Open สำหรับดึงของเก่า
                btn = ctk.CTkButton(row, text="Open", width=60, fg_color="#2eb85c", hover_color="#279e4f",
                                    command=lambda name=p_name: load_existing(name))
                btn.pack(side="right", padx=10)

    def load_saved_pipelines(self):
        # จัดการ Path ให้ชี้ไปที่โฟลเดอร์ Pipeline เสมอ (ป้องกัน Error หาไฟล์ไม่เจอ)
        save_path = os.path.join(os.path.dirname(__file__), "..", "Pipeline", "saved_pipelines.json")
        save_path = os.path.abspath(save_path)
        
        if os.path.exists(save_path):
            try:
                with open(save_path, "r", encoding="utf-8") as f:
                    return json.load(f).get("saved_pipelines", [])
            except Exception:
                pass
        return []
    
    def show_saved_pipelines_list(self, saved_data):
        # ฟังก์ชันนี้จะทำงานเมื่อเข้าหน้า Pipeline แล้วตรวจเจอว่าเคยเซฟไว้แล้ว
        # ในที่นี้เราจะแค่ Print บอก หรือจะให้แสดง Popup เลือกก็ได้
        print(f"You have {len(saved_data)} saved pipelines available in the sidebar.")
    
    def open_pipeline_wizard(self, current_step=1, pipeline_data=None):
        if pipeline_data is None:
            pipeline_data = []

        wizard = ctk.CTkToplevel(self)
        wizard.title(f"Create Pipeline - Step {current_step}")
        wizard.geometry("520x650")
        wizard.attributes("-topmost", True)

        main_frame = ctk.CTkScrollableFrame(wizard)
        main_frame.pack(fill="both", expand=True)

        # 1. ส่วนตั้งชื่อ Pipeline
        name_entry = None
        if current_step == 1:
            ctk.CTkLabel(main_frame, text="Pipeline Name:", font=("Arial", 13, "bold")).pack(anchor="w", padx=40, pady=(15, 0))
            name_entry = ctk.CTkEntry(main_frame, placeholder_text="ตั้งชื่อ Pipeline ของคุณที่นี่...")
            name_entry.pack(fill="x", padx=40, pady=10)
            self.current_pipeline_name = "" 

        ctk.CTkLabel(main_frame, text=f"Step {current_step}: Command Builder", font=("Arial", 18, "bold")).pack(pady=20)

        # 2. Dropdown เลือกเครื่องมือ
        ctk.CTkLabel(main_frame, text="Choose Tool:").pack(anchor="w", padx=40)
        all_categories = self.load_tools_from_json()
        all_tools_list = []
        for cat in all_categories:
            if cat != "Saved Pipelines":
                all_tools_list.extend(all_categories[cat])
            
        all_tools_list.append("Custom")
            
        tool_var = ctk.StringVar(value=all_tools_list[0] if all_tools_list else "None")
        tool_menu = ctk.CTkOptionMenu(main_frame, values=all_tools_list, variable=tool_var)
        tool_menu.pack(fill="x", padx=40, pady=(5, 10))

        # 3. ช่องกรอก Custom Tool
        custom_tool_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        custom_tool_entry = ctk.CTkEntry(custom_tool_frame, placeholder_text="พิมพ์คำสั่ง Custom Tool ของคุณที่นี่...")
        custom_tool_entry.pack(fill="x")

        # 4. System Info Label
        desc_label = ctk.CTkLabel(main_frame, text="System Info: Select a tool", text_color="gray", wraplength=400)
        desc_label.pack(pady=10)

        # 5. Checkbox และปุ่ม Add Option
        has_option_var = ctk.BooleanVar(value=False)
        has_option_checkbox = ctk.CTkCheckBox(main_frame, text="มี option ต่อไหม?", variable=has_option_var)
        add_option_btn = ctk.CTkButton(main_frame, text="+ Add Option", fg_color="#4f87ff")

        # 6. Note / Description
        ctk.CTkLabel(main_frame, text="Note / Description").pack(anchor="w", padx=40, pady=(15, 0))
        user_desc_entry = ctk.CTkEntry(main_frame, placeholder_text="..........")
        user_desc_entry.pack(fill="x", padx=40, pady=(5, 10))

        # ==========================================
        # Popup Add Option (แบบเลือกประเภท Param ได้)
        # ==========================================
        self.temp_options_list = []

        def open_add_option_popup():
            popup = ctk.CTkToplevel(wizard)
            popup.title("Add Custom Option")
            popup.geometry("620x350") # ขยายขนาดให้พอดีกับปุ่มใหม่
            popup.attributes("-topmost", True)
            
            ctk.CTkLabel(popup, text="Add Custom Option", font=("Arial", 14, "bold")).pack(pady=(10, 0))
            
            preview_label = ctk.CTkLabel(popup, text="Preview: ...", text_color="#2eb85c", font=("Courier", 13, "italic"))
            preview_label.pack(pady=(5, 10))
            
            options_container = ctk.CTkScrollableFrame(popup, fg_color="transparent", height=150)
            options_container.pack(fill="both", expand=True, padx=10)
            
            option_rows = [] 

            def preview_command():
                base_tool = tool_var.get()
                if base_tool == "Custom":
                    base_tool = custom_tool_entry.get().strip() or "custom_tool"
                
                flags = []
                for flag_e, desc_e, opt_type in option_rows:
                    f = flag_e.get().strip()
                    if f:
                        if opt_type == "checkbox":
                            flags.append(f)
                        else:
                            flags.append(f"{f} <value>") # ถ้ามี Param ให้ใส่ <value> โชว์ใน Preview
                
                cmd = f"{base_tool} {' '.join(flags)}"
                preview_label.configure(text=f"Preview: {cmd}")

            # ฟังก์ชันรับค่าประเภท Option มาสร้างแถว
            def add_option_row(opt_type="checkbox"):
                row = ctk.CTkFrame(options_container, fg_color="transparent")
                row.pack(fill="x", pady=5)
                
                flag_entry = ctk.CTkEntry(row, width=80, placeholder_text="-n")
                flag_entry.pack(side="left", padx=5)

                desc_entry = ctk.CTkEntry(row, placeholder_text="description")
                desc_entry.pack(side="left", fill="x", expand=True, padx=5)

                # โชว์เป็น Label สีทึบแทน Dropdown เพื่อให้ User รู้ว่าอันนี้คือแบบไหน
                type_text = "ไม่มี Param" if opt_type == "checkbox" else "มี Param (text)"
                type_color = "#3498db" if opt_type == "checkbox" else "#9b59b6"
                type_label = ctk.CTkLabel(row, text=type_text, width=100, fg_color=type_color, text_color="white", corner_radius=4)
                type_label.pack(side="left", padx=5)

                row_data = (flag_entry, desc_entry, opt_type)
                option_rows.append(row_data)

                def delete_this_row():
                    if row_data in option_rows:
                        option_rows.remove(row_data)
                    row.destroy()
                    preview_command()

                del_btn = ctk.CTkButton(row, text="X", width=30, fg_color="#e74c3c", hover_color="#c0392b", command=delete_this_row)
                del_btn.pack(side="left", padx=5)

            def save_option_from_popup():
                for flag_e, desc_e, opt_type in option_rows:
                    flag = flag_e.get().strip()
                    desc = desc_e.get().strip()
                    if flag:
                        self.temp_options_list.append({"flag": flag, "type": opt_type, "description": desc})
                        print(f"Added Option: {flag} ({opt_type})")
                popup.destroy()

            btn_row = ctk.CTkFrame(popup, fg_color="transparent")
            btn_row.pack(fill="x", pady=15, padx=20)
            
            # ปุ่มเพิ่ม Option 2 แบบ
            ctk.CTkButton(btn_row, text="+ ไม่มี Param", command=lambda: add_option_row("checkbox"), width=100, fg_color="#3498db", hover_color="#2980b9").pack(side="left", padx=5)
            ctk.CTkButton(btn_row, text="+ มี Param", command=lambda: add_option_row("text"), width=100, fg_color="#9b59b6", hover_color="#8e44ad").pack(side="left", padx=5)
            
            ctk.CTkButton(btn_row, text="Preview", command=preview_command, fg_color="#f39c12", hover_color="#e67e22", width=80).pack(side="left", padx=5)
            ctk.CTkButton(btn_row, text="Save & Close", command=save_option_from_popup, fg_color="#2eb85c", hover_color="#27ae60", width=110).pack(side="right", padx=5)

        add_option_btn.configure(command=open_add_option_popup)
        # ==========================================


        # --- ฟังก์ชันอัปเดต UI เมื่อเลือก Tool ---
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

        def toggle_add_option_btn():
            if has_option_var.get():
                add_option_btn.pack(after=has_option_checkbox, pady=5, padx=40, anchor="w")
            else:
                add_option_btn.pack_forget()

        has_option_checkbox.configure(command=toggle_add_option_btn)
        tool_menu.configure(command=update_tool_selection)
        update_tool_selection(tool_var.get())

        # --- ปุ่มควบคุมด้านล่าง (Finish & Save) ---
        btn_frame = ctk.CTkFrame(wizard, fg_color="transparent")
        btn_frame.pack(side="bottom", pady=30, fill="x", padx=40)

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

        ctk.CTkButton(btn_frame, text="+ Add Another Tool", fg_color="#6f63ff", command=add_next_tool).pack(side="left", expand=True, padx=5)
        ctk.CTkButton(btn_frame, text="Finish & Save", fg_color="#2eb85c", command=finish_pipeline).pack(side="left", expand=True, padx=5)

    def finalize_wizard_pipeline(self, pipeline_data, pipeline_name):
        self.clear_pipeline()
        for tool_info in pipeline_data:
            self.add_tool_node(tool_info["name"], user_desc=tool_info.get("user_description", ""))
            if self.nodes:
                self.nodes[-1]["params"] = tool_info.get("params", "")
                self.nodes[-1]["options"] = tool_info.get("options", [])

        # Path ไปยัง saved_pipelines.json ในโฟลเดอร์ Pipeline
        save_path = os.path.join(os.path.dirname(__file__), "..", "Pipeline", "saved_pipelines.json")
        save_path = os.path.abspath(save_path)
        
        try:
            data = {"saved_pipelines": []}
            if os.path.exists(save_path):
                # ถ้าไฟล์มีอยู่แล้ว ให้อ่านข้อมูลเดิมขึ้นมาก่อน
                with open(save_path, "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                        if "saved_pipelines" not in data:
                            data["saved_pipelines"] = []
                    except json.JSONDecodeError:
                        data = {"saved_pipelines": []}
            
            # เพิ่มข้อมูล Pipeline ใหม่
            new_entry = {
                "pipeline_name": pipeline_name,
                "steps": pipeline_data
            }
            data["saved_pipelines"].append(new_entry)

            # บันทึกทับไฟล์ saved_pipelines.json
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            self.refresh_tools_panel()
            print(f"Saved pipeline '{pipeline_name}' successfully!")
            
        except Exception as e:
            print(f"Error saving pipeline: {e}")

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
                        fg_color="#333333",
                        corner_radius=4,
                        border_width=1,
                        border_color="#6f63ff",
                        width=110,
                        height=35
                    )

                    node.place(x=x, y=y)

                    lbl = ctk.CTkLabel(
                        node,
                        text=step["name"],
                        font=ctk.CTkFont(size=11, weight="bold"),
                        text_color="white"
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

    def open_add_tool_window(self):

        win = ctk.CTkToplevel(self)
        win.title("Add Tool")
        win.geometry("300x250")

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

        def save_tool():

            name = name_entry.get()
            cmd = cmd_entry.get()
            mode = mode_var.get()

            if not name or not cmd:
                return

            self.engine.add_tool(name, cmd, mode)

            win.destroy()

        ctk.CTkButton(
            win,
            text="Add Tool",
            command=save_tool
        ).pack(pady=10)