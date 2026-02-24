import customtkinter as ctk

class PipelinePage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.configure(fg_color="#E0E0E0") # พื้นหลังสีเทาอ่อนตามภาพ

        # --- Header ---
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(10, 5))
        ctk.CTkLabel(header, text="Pipeline", font=("Arial", 22, "bold"), text_color="#555").pack(side="left")

        # --- Top Controls ---
        ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        ctrl_frame.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkButton(ctrl_frame, text="Step-by-Step", width=100, fg_color="#6495ED").pack(side="left", padx=(0, 10))
        self.path_entry = ctk.CTkEntry(ctrl_frame, placeholder_text="File...........", height=35)
        self.path_entry.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(ctrl_frame, text="Browse", width=80, fg_color="#6495ED").pack(side="left", padx=(10, 0))

        # --- Main Workspace Area (Center) ---
        main_workspace = ctk.CTkFrame(self, fg_color="transparent")
        main_workspace.pack(fill="both", expand=True, padx=20, pady=10)

        # 1. Left Sidebar (Tool List)
        tool_sidebar = ctk.CTkFrame(main_workspace, width=150, fg_color="#D3D3D3", corner_radius=10)
        tool_sidebar.pack(side="left", fill="y", padx=(0, 10))
        tool_sidebar.pack_propagate(False)
        
        tools = ["zbarimg", "md5sum", "File", "steghide", "Base 64"]
        for tool in tools:
            ctk.CTkLabel(tool_sidebar, text=tool, font=("Arial", 13)).pack(pady=10)
        ctk.CTkButton(tool_sidebar, text="+ add..", width=60, height=25, fg_color="#333").pack(pady=10)

        # 2. Right Canvas (Node Pipeline)
        canvas_container = ctk.CTkFrame(main_workspace, fg_color="#8C8C94", corner_radius=10)
        canvas_container.pack(side="left", fill="both", expand=True)

        # Toolbar inside canvas
        canvas_tools = ctk.CTkFrame(canvas_container, fg_color="#333", height=40, corner_radius=0)
        canvas_tools.pack(fill="x")
        ctk.CTkLabel(canvas_tools, text="▶  Stop  ⬜", text_color="white").pack(side="left", padx=15)
        # Dropdown Templates ตามภาพ
        ctk.CTkOptionMenu(canvas_tools, values=["Templates"], width=120, height=25).pack(side="right", padx=10)

        # Visual Nodes Area
        # หมายเหตุ: ในขั้นสูงสามารถใช้ Canvas วาดเส้นได้ แต่ในที่นี้จะใช้ Frame จัดวางให้เหมือน
        nodes_area = ctk.CTkFrame(canvas_container, fg_color="transparent")
        nodes_area.pack(expand=True)

        # แถวบน: File -> zbarimg
        row1 = ctk.CTkFrame(nodes_area, fg_color="transparent")
        row1.pack(pady=10)
        self.create_node(row1, "File", status="done").pack(side="left")
        ctk.CTkLabel(row1, text=" ──▶ ", font=("Arial", 16)).pack(side="left")
        self.create_node(row1, "zbarimg", status="process").pack(side="left")
        ctk.CTkLabel(row1, text=" ──╮", font=("Arial", 16)).pack(side="left")

        # แถวกลาง: เลี้ยวลงมาหา steghide
        row2 = ctk.CTkFrame(nodes_area, fg_color="transparent")
        row2.pack(fill="x")
        ctk.CTkLabel(row2, text="╭─────────────────╯", font=("Arial", 16)).pack(side="right", padx=(0, 40))

        # แถวล่าง: steghide -> Base 64 -> Output
        row3 = ctk.CTkFrame(nodes_area, fg_color="transparent")
        row3.pack(pady=10)
        self.create_node(row3, "Output", status="wait").pack(side="left")
        ctk.CTkLabel(row3, text=" ◀── ", font=("Arial", 16)).pack(side="left")
        self.create_node(row3, "Base 64", status="wait").pack(side="left")
        ctk.CTkLabel(row3, text=" ◀── ", font=("Arial", 16)).pack(side="left")
        self.create_node(row3, "steghide", status="wait").pack(side="left")

        # --- Output Section ---
        output_container = ctk.CTkFrame(self, fg_color="#D3D3D3", corner_radius=10)
        output_container.pack(fill="x", padx=20, pady=(0, 20))
        
        output_header = ctk.CTkFrame(output_container, fg_color="transparent")
        output_header.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(output_header, text="Output", font=("Arial", 14, "bold")).pack(side="left")
        ctk.CTkButton(output_header, text="Clear", width=60, height=20, fg_color="#888").pack(side="right")

        self.output_box = ctk.CTkTextbox(output_container, height=120, fg_color="#1A1A1B", text_color="#00FF00")
        self.output_box.pack(fill="x", padx=10, pady=(0, 10))
        self.output_box.insert("0.0", "THCTT24{6b569a1f0566088c354bdc3d57c19063}")

    def create_node(self, master, name, status="wait"):
        """ฟังก์ชันช่วยสร้างกล่อง Node พร้อมไอคอนสถานะ"""
        node_frame = ctk.CTkFrame(master, fg_color="transparent")
        
        # แสดงไอคอนสถานะด้านบน (เขียว = succeed, เหลือง = process)
        status_color = "#2ECC71" if status == "done" else "#F1C40F" if status == "process" else "#BBB"
        status_icon = "✔" if status == "done" else "⏳" if status == "process" else ""
        
        ctk.CTkLabel(node_frame, text=status_icon, text_color=status_color, font=("Arial", 12, "bold")).pack()
        
        # กล่อง Tool
        box = ctk.CTkFrame(node_frame, width=100, height=35, corner_radius=8, fg_color="#D3D3D3")
        box.pack()
        box.pack_propagate(False)
        ctk.CTkLabel(box, text=name, text_color="black", font=("Arial", 12)).pack(expand=True)
        
        return node_frame

