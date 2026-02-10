# ui/app.py 1522352
import customtkinter as ctk
from sidebar import Sidebar
from pages.data_hash import DataHashPage
from pages.file_inspection import FileInspectionPage
from pages.pipeline import PipelinePage
from pages.gemini import GeminiPage

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")


class UNITApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Unified Toolkit")
        self.geometry("1200x720")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = Sidebar(self, self.switch_page)
        self.sidebar.grid(row=0, column=0, sticky="ns")

        self.container = ctk.CTkFrame(self, fg_color="#f5f6f8")
        self.container.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.pages = {
            "Data Hashing": DataHashPage(self.container),
            "File Inspection": FileInspectionPage(self.container),
            "Pipeline": PipelinePage(self.container),
            "Gemini CLI": GeminiPage(self.container),
        }

        self.current_page = None
        self.switch_page("Data Hashing")

    def switch_page(self, name):
        if self.current_page:
            self.current_page.grid_forget()
        self.current_page = self.pages[name]
        self.current_page.grid(row=0, column=0, sticky="nsew")


if __name__ == "__main__":
    app = UNITApp()
    app.mainloop()
