"""Route wheel events to the nearest scroll area, including Linux button events."""
import sys
import tkinter as tk
from tkinter import ttk


class MouseWheelRouter:
    def __init__(self, root):
        self.root = root
        self.tag = 'UNITMouseWheel'
        for sequence in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
            root.bind_class(self.tag, sequence, self._scroll)
        # Map also covers controls/popups created after startup. A first bindtag
        # prevents native Text and CTk's global bindings from scrolling twice.
        root.bind_all('<Map>', self._mapped, add='+')
        self._attach_tree(root)

    def _attach_tree(self, widget):
        self._attach(widget)
        for child in widget.winfo_children():
            self._attach_tree(child)

    def _attach(self, widget):
        tags = widget.bindtags()
        if self.tag not in tags:
            widget.bindtags((self.tag,) + tags)

    def _mapped(self, event):
        if isinstance(event.widget, tk.Misc):
            self._attach(event.widget)

    @staticmethod
    def _target(widget):
        while isinstance(widget, tk.Misc):
            if isinstance(widget, (tk.Text, tk.Listbox, ttk.Treeview)):
                return widget
            if isinstance(widget, tk.Canvas) and widget.cget('scrollregion'):
                return widget
            # Scrollbar/border siblings of a CTk scroll canvas should work too.
            for child in widget.winfo_children():
                if isinstance(child, tk.Canvas) and child.cget('scrollregion'):
                    return child
            if isinstance(widget, (tk.Tk, tk.Toplevel)):
                break
            widget = widget.master
        return None

    def _scroll(self, event):
        target = self._target(event.widget)
        if target is None:
            return None
        if event.num in (4, 5):
            units = -3 if event.num == 4 else 3
        elif not event.delta:
            return 'break'
        elif sys.platform == 'darwin':
            units = -int(event.delta)
        else:
            units = (-1 if event.delta > 0 else 1) * max(1, int(abs(event.delta) / 120)) * 3
        axis = 'x' if event.state & 0x0001 else 'y'
        # CTk uses pixel-sized canvas increments on Windows/macOS.
        if isinstance(target, tk.Canvas) and float(target.cget(axis + 'scrollincrement')) > 0:
            units *= 10
        try:
            view = getattr(target, axis + 'view')()
            if view and view != (0.0, 1.0):
                getattr(target, axis + 'view_scroll')(units, 'units')
        except tk.TclError:
            pass  # A popup may have closed during event dispatch.
        return 'break'
