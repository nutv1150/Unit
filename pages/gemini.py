import customtkinter as ctk

class GeminiPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)

        # Styled Title (Simulating the Pixel Art Logo)
        ctk.CTkLabel(self, text="GEMINI", font=("Impact", 80), text_color="#A9CCE3").pack(expand=True)
        
        # Version Tag
        ctk.CTkLabel(self, text="geminia 2.5 Pro", font=("Arial", 12, "italic"), text_color="#5DADE2").place(relx=0.95, rely=0.8, anchor="e")

        # Bottom Input Area
        input_container = ctk.CTkFrame(self, fg_color="transparent")
        input_container.pack(side="bottom", fill="x", padx=100, pady=50)
        
        self.input_field = ctk.CTkEntry(input_container, placeholder_text="Text or path file...", height=40)
        self.input_field.pack(side="left", fill="x", expand=True)
        
        ctk.CTkButton(input_container, text="Enter", width=80, height=40).pack(side="left", padx=10)