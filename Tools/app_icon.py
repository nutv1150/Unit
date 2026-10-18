"""Shared application icon for source runs, bundles and desktop shortcuts."""
import tkinter as tk
from Tools.app_paths import RESOURCE_ROOT


ICON_PATH = RESOURCE_ROOT / 'packaging' / 'unit.png'


# หน้าที่: โหลดรูปไอคอนและกำหนดหลายขนาดให้หน้าต่าง Tk พร้อมรักษา reference ของรูป
# ที่มา: app.py::UNITApp.__init__ (เรียกตรง)
# Input: root (tkinter.Misc (widget ของ Tk/CustomTkinter)) — หน้าต่างหรือ widget ที่ผู้เรียกสร้างไว้
def set_app_icon(root):
    image = tk.PhotoImage(master=root, file=str(ICON_PATH))
    # Keep the original asset unchanged; provide small in-memory window icons.
    root._unit_icons = [image.subsample(max(1, image.width() // size))
                        for size in (32, 64, 128)]
    root.iconphoto(True, *root._unit_icons)
