import customtkinter as ctk

class DataHashPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        
        # เก็บสถานะปัจจุบัน nutcccvvttbbutv
        self.mode = "Decode"  # ค่าเริ่มต้นคือ Decode
        self.tab_buttons = {} # เก็บ object ของปุ่ม Tab

        # Title
        ctk.CTkLabel(self, text="Data Hashing Encoding And Decoding", font=("Arial", 18, "bold")).pack(anchor="w", padx=20, pady=(20, 10))

        # Top Control Bar sdflhsodklf
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=20)
        
        # ปุ่มสลับโหมด Decode/Encode
        self.mode_btn = ctk.CTkButton(top_bar, text="Decode", width=100, command=self.toggle_mode)
        self.mode_btn.pack(side="left", padx=5)
        
        self.algo_menu = ctk.CTkOptionMenu(top_bar, values=["Auto Detect", "Base64", "Base32", "Hex"], width=200)
        self.algo_menu.pack(side="left", padx=5)

        # Tab Selection Buttons
        tab_frame = ctk.CTkFrame(self, fg_color="transparent")
        tab_frame.pack(fill="x", padx=20, pady=10)
        
        tabs = ["Auto Detect", "Base64", "Base32", "Hex"]
        for t in tabs:
            btn = ctk.CTkButton(
                tab_frame, 
                text=t, 
                width=80, 
                fg_color=None if t == "Auto Detect" else "gray", # ให้ Auto Detect เป็นสีหลักเริ่มต้น
                command=lambda name=t: self.select_tab(name)
            )
            btn.pack(side="left", padx=4)
            self.tab_buttons[t] = btn

        # INPUT Section
        input_header = ctk.CTkFrame(self, fg_color="transparent")
        input_header.pack(fill="x", padx=20)
        ctk.CTkLabel(input_header, text="INPUT", font=("Arial", 12, "bold")).pack(side="left")
        ctk.CTkButton(input_header, text="Browse", width=60, height=24).pack(side="left", padx=10)

        self.input_box = ctk.CTkTextbox(self, height=150)
        self.input_box.pack(fill="x", padx=20, pady=(5, 15))

        # OUTPUT Section 
        output_header = ctk.CTkFrame(self, fg_color="transparent")
        output_header.pack(fill="x", padx=20)
        ctk.CTkLabel(output_header, text="OUTPUT", font=("Arial", 12, "bold")).pack(side="left")
        
        # ปุ่มแสดงประเภท Output (อาจจะเปลี่ยนตาม Algorithm ที่เลือก)
        self.output_label_btn = ctk.CTkButton(output_header, text="Base64", width=60, height=24, fg_color="gray")
        self.output_label_btn.pack(side="left", padx=10)

        self.output_box = ctk.CTkTextbox(self, height=150)
        self.output_box.pack(fill="both", expand=True, padx=20, pady=(5, 20))

    def toggle_mode(self):
        """ สลับระหว่าง Decode และ Encode """
        if self.mode == "Decode":
            self.mode = "Encode"
            self.mode_btn.configure(text="Encode")
            # คุณสามารถเพิ่ม Logic การทำงานของ Encode ตรงนี้ได้
        else:
            self.mode = "Decode"
            self.mode_btn.configure(text="Decode")
            # คุณสามารถเพิ่ม Logic การทำงานของ Decode ตรงนี้ได้
        print(f"Current Mode: {self.mode}")

    def select_tab(self, selected_name):
        """ ไฮไลท์ปุ่ม Tab ที่ถูกเลือก และเปลี่ยนค่าใน OptionMenu ตาม """
        for name, btn in self.tab_buttons.items():
            if name == selected_name:
                btn.configure(fg_color=["#3a7ebf", "#1f538d"]) # สีน้ำเงิน (Default Theme)
            else:
                btn.configure(fg_color="gray")
        
        # อัปเดต OptionMenu ให้ตรงกับ Tab ที่กดด้วย
        self.algo_menu.set(selected_name)
        print(f"Selected Algorithm: {selected_name}")