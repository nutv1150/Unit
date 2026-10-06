"""Real Tk event-loop checks with temporary evidence files only."""
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import customtkinter as ctk
from tkinterdnd2 import TkinterDnD
from pages.file_inspection import FileInspectionPage


@unittest.skipUnless(os.environ.get('DISPLAY'), 'Needs X display')
class InspectionGuiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = ctk.CTk()
        TkinterDnD._require(self.root)
        self.root.geometry('1200x800')
        def cleanup():
            for callback in self.root.tk.call('after', 'info'):
                self.root.tk.call('after', 'cancel', callback)
            self.root.destroy()
        self.addCleanup(cleanup)
        self.errors = []
        self.root.report_callback_exception = lambda *args: self.errors.append(args)
        self.page = FileInspectionPage(self.root)
        self.page.pack(fill='both', expand=True)
        self.page._record_activity = Mock()
        self.root.update()

    def wait_done(self):
        deadline = time.monotonic() + 5
        while self.page.btn_analyze.cget('state') == 'disabled':
            self.root.update()
            if time.monotonic() > deadline:
                self.fail('Analysis did not finish')
            time.sleep(.01)
        self.assertFalse(self.errors)

    def test_batch_does_not_skip_second_file_after_display_limit(self):
        paths = [Path(self.temp.name) / name for name in ('one.txt', 'two.txt')]
        paths[0].write_text('first\nextra\n', encoding='utf-8')
        paths[1].write_text('second\n', encoding='utf-8')
        self.page.tool_menu.set('Strings')
        self.page.max_display_entry.delete(0, 'end')
        self.page.max_display_entry.insert(0, '1')
        self.page.load_files([str(p) for p in paths])
        self.wait_done()
        self.assertIn('second', self.page.result_boxes[str(paths[1])].textbox.get('1.0', 'end'))
        self.assertEqual(self.page._record_activity.call_count, 2)

    def test_header_fallback_and_tool_failure_are_reported_correctly(self):
        path = Path(self.temp.name) / 'sample.bin'
        path.write_bytes(b'GIF89a' + b'\0' * 20)
        self.page.tool_menu.set('Header Check')
        with patch('pages.file_inspection.puremagic.from_file', return_value='.gif'):
            self.page.load_files([str(path)])
            self.wait_done()
        text = self.page.result_boxes[str(path)].textbox.get('1.0', 'end')
        self.assertIn('.gif', text)
        self.assertNotIn('Plain Text', text)
        self.page.tool_menu.set('Exiftool')
        failure = subprocess.CompletedProcess([], 2, '', 'invalid data')
        with patch('pages.file_inspection.subprocess.run', return_value=failure):
            self.page.start_analysis_thread()
            self.wait_done()
        self.assertIn('ERRORS', self.page.warning_label.cget('text'))
        self.assertEqual(self.page._record_activity.call_args.kwargs['status'], 'failed')

    def test_stale_callbacks_are_discarded_and_regex_is_validated(self):
        stale, current = Mock(), Mock()
        self.page._ui_queue.put(('analysis', -1, stale))
        self.page._ui_queue.put(('metadata', -1, stale))
        self.page._ui_queue.put(('analysis', self.page._analysis_generation, current))
        self.page._drain_ui()
        stale.assert_not_called()
        current.assert_called_once()
        path = Path(self.temp.name) / 'input.txt'
        path.write_text('data', encoding='utf-8')
        self.page.selected_files = [str(path)]
        self.page.regex_var.set('[')
        with patch('pages.file_inspection.threading.Thread') as worker:
            self.page.start_analysis_thread()
        worker.assert_not_called()
        self.assertIn('ERROR', self.page.warning_label.cget('text'))

    def test_regex_matching_and_timeout_recover_gui(self):
        path = Path(self.temp.name) / 'regex.txt'
        path.write_text('flag{ok}', encoding='utf-8')
        self.page.tool_menu.set('Strings')
        self.page.regex_var.set(r'flag\{[^}]+\}')
        self.page.load_files([str(path)])
        self.wait_done()
        self.assertIn('FOUND 1 MATCHES', self.page.warning_label.cget('text'))
        path.write_text('a' * 32 + '!', encoding='utf-8')
        self.page.regex_var.set('(a+)+$')
        ticks = []
        self.root.after(50, lambda: ticks.append(True))
        self.page.start_analysis_thread()
        self.wait_done()
        self.assertTrue(ticks)
        self.assertIn('ERRORS', self.page.warning_label.cget('text'))
        self.assertIn('Regex exceeded', self.page.result_boxes[str(path)].textbox.get('1.0', 'end'))
