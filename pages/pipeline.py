import customtkinter as ctk

class PipelinePage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)

        ctk.CTkLabel(self, text="⚙️ Pipeline", font=("Arial", 18, "bold")).pack(anchor="w", padx=20, pady=10)

        # Control butt
        ctrl = ctk.CTkFrame(self, fg_color="transparent")
        ctrl.pack(fill="x", padx=20)
        ctk.CTkButton(ctrl, text="Browse", width=80).pack(side="left")
        ctk.CTkEntry(ctrl, placeholder_text="File...........").pack(side="left", fill="x", expand=True, padx=10)
        
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkButton(btn_frame, text="Auto", width=100).pack(side="left")
        ctk.CTkButton(btn_frame, text="Step-by-Step", width=120, fg_color="#3498DB").pack(side="left", padx=10)

        # Interactive Status Area
        main_content = ctk.CTkFrame(self, fg_color="transparent")
        main_content.pack(fill="x", padx=20)

        # Left: Active Tool Control
        active_tool = ctk.CTkFrame(main_content, width=200, height=150)
        active_tool.pack(side="left", fill="y", padx=(0, 10))
        ctk.CTkLabel(active_tool, text="steghide").pack(pady=5)
        ctk.CTkEntry(active_tool, placeholder_text="Pass...", height=25).pack(padx=10, pady=5)
        btn_row = ctk.CTkFrame(active_tool, fg_color="transparent")
        btn_row.pack(pady=5)
        ctk.CTkButton(btn_row, text="extract", width=60, height=25).pack(side="left", padx=2)
        ctk.CTkButton(btn_row, text="info", width=60, height=25).pack(side="left", padx=2)

        # Right: Status Grid
        status_grid = ctk.CTkFrame(main_content)
        status_grid.pack(side="left", fill="both", expand=True)
        
        tools = [("zbarimg", "succeed"), ("md5sum", "succeed"), ("steghide", "Process"), ("cat", "wait..")]
        for i, (name, status) in enumerate(tools):
            card = ctk.CTkFrame(status_grid, width=150, height=40)
            card.grid(row=i//2, column=i%2, padx=5, pady=5, sticky="nsew")
            ctk.CTkLabel(card, text=name).pack(side="left", padx=10)
            color = "green" if status == "succeed" else "orange" if status == "Process" else "gray"
            ctk.CTkLabel(card, text=status, text_color=color).pack(side="right", padx=10)

        # Output
        self.output_box = ctk.CTkTextbox(self, height=150)
        self.output_box.pack(fill="both", expand=True, padx=20, pady=20)