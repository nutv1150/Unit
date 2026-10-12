"""Shared application icon for source runs, bundles and desktop shortcuts."""
import tkinter as tk
from Tools.app_paths import RESOURCE_ROOT


ICON_PATH = RESOURCE_ROOT / 'packaging' / 'unit.png'


def set_app_icon(root):
    image = tk.PhotoImage(master=root, file=str(ICON_PATH))
    # Keep the original asset unchanged; provide small in-memory window icons.
    root._unit_icons = [image.subsample(max(1, image.width() // size))
                        for size in (32, 64, 128)]
    root.iconphoto(True, *root._unit_icons)
