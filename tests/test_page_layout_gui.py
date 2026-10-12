"""Check the two crowded pages against real Tk geometry, without live services."""
import os
import subprocess
import unittest
import customtkinter as ctk
from tests import test_history_gui as fixtures
from tests.test_pipeline_output_gui import button, descendants


@unittest.skipUnless(os.environ.get('DISPLAY'), 'Needs X display')
class PageLayoutTests(unittest.TestCase):
    setUp = fixtures.HistoryGuiTests.setUp
    close_root = fixtures.HistoryGuiTests.close_root

    def inside(self, widget, parent):
        self.assertTrue(widget.winfo_ismapped())
        self.assertGreaterEqual(widget.winfo_rootx(), parent.winfo_rootx())
        self.assertGreaterEqual(widget.winfo_rooty(), parent.winfo_rooty())
        self.assertLessEqual(widget.winfo_rootx()+widget.winfo_width(), parent.winfo_rootx()+parent.winfo_width())
        self.assertLessEqual(widget.winfo_rooty()+widget.winfo_height(), parent.winfo_rooty()+parent.winfo_height())

    def test_headers_controls_and_footer_at_multiple_sizes(self):
        self.addCleanup(ctk.set_widget_scaling, 1)
        for scale, geometry in [(1, '1024x640'), (1.25, '1200x720'), (1, '1200x720'), (1, '1360x820')]:
            with self.subTest(scale=scale, geometry=geometry):
                ctk.set_widget_scaling(scale)
                self.root.geometry(geometry)
                self.root.switch_page('Dashboard')
                self.root.update()
                dashboard = self.root.pages['Dashboard']
                title = next(w for w in descendants(dashboard) if isinstance(w, ctk.CTkLabel)
                             and w.cget('text') == '>_ UNIT COMMAND DASHBOARD')
                history = button(dashboard, 'History')
                system = button(dashboard, 'System Check')
                for w in (title, history, system):
                    self.inside(w, self.root)
                self.assertLessEqual(title.winfo_rooty()+title.winfo_height(), history.winfo_rooty())
                self.assertFalse(hasattr(dashboard, 'competition_menu'))
                self.assertFalse(any(isinstance(w, ctk.CTkLabel) and w.cget('text') == 'ACTIVE CTF'
                                     for w in descendants(dashboard)))
                if os.environ.get('UNIT_LAYOUT_SCREENSHOTS') and scale == 1 and geometry == '1200x720':
                    subprocess.run(['import', '-window', str(self.root.winfo_id()), '/tmp/unit-dashboard-layout.png'], check=True)
                self.root.switch_page('Gemini CLI')
                self.root.update()
                page = self.root.pages['Gemini CLI']
                for w in (page.chat_display, page.full_response_button, page.command_output_button,
                          page.input_field, page.send_btn, page.stop_btn, page.api_entry):
                    self.inside(w, page)
                self.assertEqual(page.full_response_button.winfo_rooty(), page.command_output_button.winfo_rooty())
                self.assertLessEqual(page.full_response_button.winfo_rootx()+page.full_response_button.winfo_width(),
                                     page.command_output_button.winfo_rootx())
                self.assertLessEqual(page.chat_display.winfo_rooty()+page.chat_display.winfo_height(),
                                     page.full_response_button.winfo_rooty())
                self.assertGreater(page.chat_display.winfo_height(), 100)
                self.assertGreater(page.input_field.winfo_width(), 150)
                if os.environ.get('UNIT_LAYOUT_SCREENSHOTS') and scale == 1 and geometry == '1200x720':
                    subprocess.run(['import', '-window', str(self.root.winfo_id()), '/tmp/unit-gemini-layout.png'], check=True)
        self.assertFalse(self.errors)
