"""Start the real application, isolated from persistent user data."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


@unittest.skipUnless(os.environ.get('DISPLAY'), 'Needs X display')
class ApplicationSmokeTests(unittest.TestCase):
    def test_all_pages_and_clean_close(self):
        from app import UNITApp
        from Tools.dashboard_store import DashboardStore
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            with patch('app.DashboardStore', side_effect=lambda: DashboardStore(work / 'dashboard.json')), \
                 patch('Tools.workspace_store.CONFIG_DIR', work), \
                 patch('pages.my_tools.CONFIG_DIR', work):
                root = UNITApp()
                errors = []
                root.report_callback_exception = lambda *args: errors.append(args)
                try:
                    self.assertEqual(len(root.pages), 8)
                    for name, page in root.pages.items():
                        root.switch_page(name)
                        root.update()
                        self.assertIs(root.current_page, page)
                        self.assertTrue(page.winfo_ismapped())
                    from tests.test_pipeline_output_gui import descendants
                    import customtkinter as ctk
                    labels = [str(w.cget('text')) for w in descendants(root)
                              if isinstance(w, ctk.CTkLabel)]
                    for caption in ('Universal codec console', 'ศูนย์ควบคุมเครื่องมือ',
                                    'SYSTEM_STATUS: WRAPPER ACTIVE', 'Auto ·', 'Step ·'):
                        self.assertFalse(any(caption in label for label in labels), caption)
                    self.assertFalse(errors)
                finally:
                    for callback in root.tk.call('after', 'info'):
                        root.tk.call('after', 'cancel', callback)
                    root.on_close()
