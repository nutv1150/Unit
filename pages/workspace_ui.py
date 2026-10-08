"""Shared dark colors and CTk-only dialogs for personal workspace pages."""
import customtkinter as ctk

# ใช้โทนเข้มคงที่เหมือน Dashboard แม้ appearance mode ของแอปเป็น Light
THEME_COLORS = {
    'bg': '#0D0D12', 'panel': '#15151E',
    'card': '#1E1E2A', 'border': '#333344',
    'text': '#E6EAF3', 'muted': '#8892B0',
    'accent': '#378ADD', 'green': '#1D9E75',
    'amber': '#EF9F27', 'purple': '#7F77DD',
    'error': '#FF5378', 'hover': '#20304A',
}
COLORS = {name: THEME_COLORS[key] for name, key in
          [('blue', 'accent'), ('green', 'green'), ('amber', 'amber'), ('purple', 'purple')]}
FONT = ('Consolas', 12)
ENTRY_STYLE = dict(fg_color='#0A0A0F', border_color=THEME_COLORS['border'],
                   text_color=THEME_COLORS['text'], placeholder_text_color=THEME_COLORS['muted'])


def label(parent, text, **kwargs):
    return ctk.CTkLabel(parent, text=text, font=FONT, text_color=THEME_COLORS['text'], **kwargs)


def dialog(parent, title, geometry='400x520'):
    window = ctk.CTkToplevel(parent)
    window.title(title)
    window.geometry(geometry)
    window.configure(fg_color=THEME_COLORS['bg'])
    window.transient(parent.winfo_toplevel())
    window.after(100, lambda: window.grab_set() if window.winfo_exists() else None)
    return window


class CTkMessagebox(ctk.CTkToplevel):
    """Small CTk-only confirmation, with no additional third-party dependency."""
    def __init__(self, parent, message, on_confirm):
        super().__init__(parent)
        self.title('Confirm delete')
        self.geometry('400x180')
        self.configure(fg_color=THEME_COLORS['bg'])
        self.transient(parent.winfo_toplevel())
        previous_grab = parent.grab_current()
        def close():
            self.destroy()
            if previous_grab is not None and previous_grab.winfo_exists():
                previous_grab.grab_set()
        def confirm():
            close()
            on_confirm()
        label(self, message, wraplength=350).pack(padx=20, pady=24)
        buttons = ctk.CTkFrame(self, fg_color='transparent')
        buttons.pack(padx=20, fill='x')
        ctk.CTkButton(buttons, text='Cancel', command=close).pack(side='left')
        ctk.CTkButton(buttons, text='Delete', fg_color=THEME_COLORS['error'], command=confirm).pack(side='right')
        self.protocol('WM_DELETE_WINDOW', close)
        self.after(100, lambda: self.grab_set() if self.winfo_exists() else None)
