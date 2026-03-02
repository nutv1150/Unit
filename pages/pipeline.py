import customtkinter as ctk
import tkinter as tk

class PipelinePage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        
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
        self.tools_panel = ctk.CTkFrame(self.content_row, fg_color="#f7f7f7", width=230, corner_radius=10)
        self.tools_panel.pack(side="left", fill="y", padx=(0, 15))
        self.tools_panel.pack_propagate(False)

        ctk.CTkLabel(self.tools_panel, text="All Tools", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(15, 10), padx=15, anchor="w")

        tool_categories = {
            "Steganography": ["steghide", "zsteg", "zbarimg"],
            "File Analysis": ["binwalk", "strings", "file"],
            "Cryptography": ["Base 64", "md5sum", "unique", "grep"]
        }

        for cat, tools in tool_categories.items():
            ctk.CTkLabel(self.tools_panel, text=cat, font=ctk.CTkFont(size=13, weight="bold")).pack(padx=15, anchor="w", pady=(5,0))
            for tool in tools:
                lbl = ctk.CTkLabel(self.tools_panel, text=f"  • {tool}", font=ctk.CTkFont(size=12), cursor="hand2")
                lbl.pack(padx=15, anchor="w")
                lbl.bind("<Button-1>", lambda e, t=tool: self.add_tool_node(t))

        self.add_btn = ctk.CTkButton(self.tools_panel, text="+ Add Tools", fg_color="transparent", border_width=1, border_color="#ccc", text_color="black", hover_color="#eee")
        self.add_btn.pack(fill="x", padx=15, pady=20)

        # --- Work Area (ตรงกลาง) ---
        self.work_area = ctk.CTkFrame(self.content_row, fg_color="white", corner_radius=10)
        self.work_area.pack(side="left", fill="both", expand=True)

        # --- Top Controls (ใส่ปุ่มให้ครบตามรูป) ---
        self.controls = ctk.CTkFrame(self.work_area, fg_color="transparent")
        self.controls.pack(fill="x", padx=15, pady=15)

        self.step_btn = ctk.CTkButton(self.controls, text="Step-by-Step", fg_color="#4f87ff", width=100,command=self.toggle_mode)
        self.step_btn.pack(side="left", padx=2)

        self.file_input = ctk.CTkEntry(self.controls, placeholder_text="File..........")
        self.file_input.pack(side="left", fill="x", expand=True, padx=5)

        # ปุ่ม Browse, Run All, Stop, Clear (ครบถ้วน)
        for btn_text in ["Browse", "Run All", "Stop", "Clear"]:
            ctk.CTkButton(self.controls, text=btn_text, fg_color="#dcdcdc", text_color="black", width=80, hover_color="#ccc").pack(side="left", padx=2)
        
        self.template_opt = ctk.CTkOptionMenu(self.controls, values=["Templates"], fg_color="#dcdcdc", text_color="black", button_color="#ccc", width=100)
        self.template_opt.pack(side="left", padx=2)

        # --- Canvas Area (จุดที่ต้องแก้ Error line_canvas) ---
        self.canvas_container = ctk.CTkFrame(self.work_area, fg_color="#1a1a1a", corner_radius=8)
        self.canvas_container.pack(fill="both", expand=True, padx=15)

        # สร้าง Canvas สำหรับวาดเส้นเชื่อม
        self.line_canvas = tk.Canvas(self.canvas_container, bg="#1a1a1a", highlightthickness=0)
        self.line_canvas.pack(fill="both", expand=True)

        self.placeholder = ctk.CTkLabel(self.line_canvas, text="Pipeline Flow Canvas Area", text_color="#555")
        self.placeholder.place(relx=0.5, rely=0.5, anchor="center")

        # --- Bottom Panels (Configuration & Result) ---
        self.bottom_row = ctk.CTkFrame(self.work_area, fg_color="transparent")
        self.bottom_row.pack(fill="x", padx=15, pady=15)

        # Config Panel
        # --- Config Panel ---
        self.panel_config = ctk.CTkFrame(self.bottom_row, fg_color="#f3f3f3", corner_radius=8)
        self.panel_config.pack(side="left", fill="both", expand=True, padx=(0, 7))
        
        self.config_title = ctk.CTkLabel(self.panel_config, text="Node: [None] Configuration", font=ctk.CTkFont(size=13, weight="bold"))
        self.config_title.pack(anchor="w", padx=10, pady=5)
        
        self.param_input = ctk.CTkEntry(self.panel_config, placeholder_text="-sf <file> -p <password>", height=30)
        self.param_input.pack(fill="x", padx=10, pady=5)
        
        # เปลี่ยนจาก Ask AI เป็น ยืนยัน Option
        self.confirm_btn = ctk.CTkButton(self.panel_config, 
                                         text="Confirm Options", 
                                         fg_color="#2eb85c", # เปลี่ยนเป็นสีเขียวให้ดูเป็นการยืนยัน
                                         hover_color="#1e7e34",
                                         command=self.save_node_config) # เพิ่มฟังก์ชันรองรับการบันทึก
        self.confirm_btn.pack(fill="x", padx=10, pady=5)

        

        # Result Panel
        self.panel_result = ctk.CTkFrame(self.bottom_row, fg_color="#f3f3f3", corner_radius=8)
        self.panel_result.pack(side="left", fill="both", expand=True, padx=(7, 0))

        ctk.CTkLabel(self.panel_result, text="Intermediate Output (Step Result)", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=10, pady=5)
        self.result_text = ctk.CTkTextbox(self.panel_result, height=80, font=("monospace", 12))
        self.result_text.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(self.panel_result, text="Send Highlighted To Next Node", fg_color="#6f63ff").pack(fill="x", padx=10, pady=5)

    def save_node_config(self):
        # ดึงชื่อ Node ปัจจุบันจาก Title (หรือสร้างตัวแปรเก็บ current_node ไว้)
            current_text = self.config_title.cget("text")
            if "[None]" in current_text:
                print("No node selected!")
                return
                
            new_params = self.param_input.get()
            # Logic สำหรับบันทึกค่าลงใน List ของ Nodes หรือ Object ที่เกี่ยวข้อง
            print(f"Saved options for {current_text}: {new_params}")
            
            # แสดง Feedback เล็กน้อยว่าบันทึกแล้ว
            self.confirm_btn.configure(text="Saved!", fg_color="#155724")
            self.after(1000, lambda: self.confirm_btn.configure(text="Confirm Options", fg_color="#2eb85c"))
            
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

        node_data = {'frame': node, 'name': tool_name}
        self.nodes.append(node_data)

        # ทำให้ลากได้
        for item in [node, lbl]:
            item.bind("<Button-1>", lambda e, n=node_data: self.on_node_press(e, n))
            item.bind("<B1-Motion>", lambda e, n=node_data: self.on_node_drag(e, n))

        self.draw_connections()

    def on_node_press(self, event, node_data):
        self.config_title.configure(text=f"Node: {node_data['name']} [Configuration]")
        node_data['drag_data'] = {'x': event.x, 'y': event.y}
        node_data['frame'].lift()

    def on_node_drag(self, event, node_data):
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