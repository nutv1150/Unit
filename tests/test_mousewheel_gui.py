"""Real wheel dispatch on Linux, including dynamically created popup controls."""
import os
import tkinter as tk
from tkinter import ttk
import unittest

import customtkinter as ctk
from tests import test_history_gui as fixtures
from tests.test_pipeline_output_gui import descendants


@unittest.skipUnless(os.environ.get('DISPLAY'), 'Needs X display')
class MouseWheelTests(unittest.TestCase):
    setUp = fixtures.HistoryGuiTests.setUp
    close_root = fixtures.HistoryGuiTests.close_root

    def wheel(self, widget, sequence='<Button-5>', **kwargs):
        widget.event_generate(sequence, **kwargs)
        self.root.update()
        self.assertFalse(self.errors)

    def test_dashboard_and_pipeline_hover_without_focus(self):
        self.root.geometry('1024x640')
        self.root.update()
        area = self.root.pages['Dashboard'].main_frame
        canvas = area._parent_canvas
        label = next(w for w in descendants(area) if isinstance(w, ctk.CTkLabel))
        before = canvas.yview()
        self.wheel(label)
        self.assertGreater(canvas.yview()[0], before[0])
        self.wheel(label, '<Button-4>')
        self.assertAlmostEqual(canvas.yview()[0], before[0], places=2)
        self.root.switch_page('Pipeline')
        self.root.update()
        panel = self.root.pages['Pipeline'].tools_panel
        # A short synthetic list avoids depending on the user's tool profiles.
        for n in range(40):
            ctk.CTkLabel(panel, text=f'Tool {n}').pack()
        self.root.update()
        before = panel._parent_canvas.yview()[0]
        self.wheel(panel, '<MouseWheel>', delta=-120)
        self.assertGreater(panel._parent_canvas.yview()[0], before)
        self.assertEqual(canvas.yview()[0], 0)

    def test_popup_nested_text_scrolls_only_once_and_keeps_parent_still(self):
        popup = ctk.CTkToplevel(self.root)
        self.addCleanup(popup.destroy)
        popup.geometry('460x330')
        area = ctk.CTkScrollableFrame(popup)
        area.pack(fill='both', expand=True)
        text = tk.Text(area, width=35, height=6)
        text.pack()
        text.insert('1.0', '\n'.join(f'Output {n}' for n in range(200)))
        text.configure(state='disabled')
        for n in range(25):
            ctk.CTkLabel(area, text=f'Option {n}').pack()
        self.root.update()
        text.yview_scroll(3, 'units')
        expected = text.yview()
        text.yview_moveto(0)
        before = area._parent_canvas.yview()
        self.wheel(text)
        self.assertEqual(text.yview(), expected)
        self.assertEqual(area._parent_canvas.yview(), before)
        text.yview_moveto(1)
        self.wheel(text)
        self.assertEqual(area._parent_canvas.yview(), before)
        self.wheel(area)
        self.assertGreater(area._parent_canvas.yview()[0], before[0])

    def test_history_tree_and_shift_horizontal(self):
        popup = ctk.CTkToplevel(self.root)
        self.addCleanup(popup.destroy)
        popup.geometry('460x330')
        tree = ttk.Treeview(popup, height=5)
        tree.pack()
        for n in range(80):
            tree.insert('', 'end', text=str(n))
        text = tk.Text(popup, width=30, height=3, wrap='none')
        text.pack()
        text.insert('1.0', 'long output ' * 100)
        self.root.update()
        self.wheel(tree)
        self.assertGreater(tree.yview()[0], 0)
        self.wheel(text, '<MouseWheel>', delta=-120, state=1)
        self.assertGreater(text.xview()[0], 0)
        self.assertEqual(text.yview()[0], 0)
