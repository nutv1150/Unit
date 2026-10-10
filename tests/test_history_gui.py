"""Shared history across real pages, using isolated stores and subprocesses."""
import os
import sys
import tempfile
import time
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

import customtkinter as ctk
from Tools.solve_history import SolveHistoryStore
from Tools.dashboard_store import DashboardStore
from Tools import history_hooks
from tests.test_pipeline_output_gui import descendants, button, run_and_wait


@unittest.skipUnless(os.environ.get('DISPLAY'), 'Needs X display')
class HistoryGuiTests(unittest.TestCase):
    def setUp(self):
        from app import UNITApp
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.addCleanup(os.chdir, Path.cwd())
        os.chdir(self.work)
        for target, kwargs in [
            ('app.DashboardStore', {'side_effect': lambda: DashboardStore(self.work / 'dashboard.json')}),
            ('app.SolveHistoryStore', {'side_effect': lambda: SolveHistoryStore(self.work / 'history.sqlite3')}),
            ('Tools.workspace_store.CONFIG_DIR', {'new': self.work}),
            ('pages.my_tools.CONFIG_DIR', {'new': self.work}),
        ]:
            mock = patch(target, **kwargs)
            mock.start()
            self.addCleanup(mock.stop)
        self.root = UNITApp()
        self.addCleanup(self.close_root)
        self.errors = []
        self.root.report_callback_exception = lambda *args: self.errors.append(args)
        self.root.update()
        self.store = self.root.history_store

    def close_root(self):
        for callback in self.root.tk.call('after', 'info'):
            self.root.tk.call('after', 'cancel', callback)
        self.root.on_close()

    def wait_inspection(self, page):
        deadline = time.monotonic() + 8
        while page.btn_analyze.cget('state') == 'disabled':
            self.root.update()
            if time.monotonic() > deadline:
                self.fail('Inspection did not finish')
            time.sleep(.01)

    def test_inspection_to_hashing_and_pipeline_retries_are_ordered(self):
        source = self.work / 'sample.txt'
        source.write_text('SGVsbG8=', encoding='utf-8')
        inspection = self.root.pages['File Inspection']
        hashing = self.root.pages['Data Hashing']
        hashing.select_quick_algo('Base64')
        inspection.tool_menu.set('Strings')
        inspection.load_files([str(source)])
        self.wait_inspection(inspection)
        box = inspection.result_boxes[str(source)]
        box.textbox.tag_add('sel', '1.0', 'end-1c')
        box.send_selection()
        self.assertEqual(hashing.output_bytes, b'Hello')
        records = self.store.list_events()
        self.assertEqual([r['category'] for r in records], ['File Inspection', 'Data Hashing'])
        self.assertEqual(records[1]['parent_id'], records[0]['id'])
        self.assertEqual(records[1]['input'], 'SGVsbG8=')
        raw_file = self.work / 'decoded.bin'
        with patch('pages.data_hash.filedialog.asksaveasfilename', return_value=str(raw_file)):
            hashing.save_raw_output()
        self.assertEqual(raw_file.read_bytes(), b'Hello')
        self.assertIn(str(raw_file), self.store.get_event(records[1]['id'])['files'])
        page = self.root.pages['Pipeline']
        page.set_pipeline_mode('Step')
        page.engine.text_tools['echo_history'] = lambda p: [sys.executable, '-c',
            'import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())']
        page.add_tool_node('echo_history')
        failures = []
        def interact():
            win = next(w for w in page.winfo_children() if isinstance(w, ctk.CTkToplevel))
            try:
                entry = next(w for w in descendants(win) if isinstance(w, ctk.CTkEntry))
                entry.insert(0, 'Hello')
                run_and_wait(win)
                page.engine.text_tools['echo_history'] = lambda p: [sys.executable, '-c', 'raise SystemExit(2)']
                run_and_wait(win)
                button(win, 'Close Analysis').invoke()
            except BaseException as error:
                failures.append(error)
                win.destroy()
        self.root.after(80, interact)
        page.run_pipeline()
        if failures:
            raise failures[0]
        records = self.store.list_events()
        self.assertEqual(len(records), 4)
        self.assertEqual([r['status'] for r in records], ['Success', 'Success', 'Success', 'Failed'])
        self.assertEqual(records[2]['group_id'], records[3]['group_id'])
        self.assertIsNone(records[2]['parent_id'], 'Manual input must not guess provenance')
        self.assertEqual(records[2]['output'], 'Hello')
        self.assertFalse(self.errors)

    def test_history_filters_selected_export_and_scoped_clear(self):
        ids = []
        evidence = self.work / 'evidence.html'
        evidence.write_text('do not overwrite', encoding='utf-8')
        for category in ('Data Hashing', 'Pipeline', 'File Inspection'):
            event_id = self.store.begin(category, 'tool', input_data='<script>bad()</script>', files=[str(evidence)])
            self.store.finish(event_id, 'Success', output_data=category)
            ids.append(event_id)
        button(self.root.pages['Dashboard'], 'History').invoke()
        window = self.root._history_window
        self.root.update()
        self.assertEqual(len(window.table.get_children()), 3)
        window.table.selection_set((ids[0], ids[2]))
        report = self.work / 'selected.html'
        with patch('pages.solve_history.filedialog.asksaveasfilename', return_value=str(report)):
            window.export_selected()
        html = report.read_text(encoding='utf-8')
        self.assertIn('2 event(s)', html)
        self.assertNotIn('<script>', html)
        self.assertNotIn('Pipeline</code>', html)
        button(self.root.pages['Pipeline'], 'History').invoke()
        self.assertIs(self.root._history_window, window)
        self.assertEqual(window.filter.get(), 'Pipeline')
        self.assertEqual(list(window.table.get_children()), [ids[1]])
        with patch('pages.solve_history.messagebox.askyesno', return_value=False):
            window.clear_history()
        self.assertEqual(len(self.store.list_events()), 3)
        with patch('pages.solve_history.messagebox.askyesno', return_value=True):
            window.clear_history()
        self.assertEqual(len(self.store.list_events()), 2)
        self.assertEqual(evidence.read_text(), 'do not overwrite')
        window.set_category('All')
        with patch('pages.solve_history.filedialog.asksaveasfilename', return_value=str(evidence)), \
             patch('pages.solve_history.messagebox.showerror') as error:
            window.export_all()
        error.assert_called_once()
        self.assertEqual(evidence.read_text(), 'do not overwrite')
        with patch('pages.solve_history.messagebox.askyesno', return_value=True):
            window.clear_history()
        self.assertEqual(self.store.list_events(), [])
        new_id = self.store.begin('Data Hashing', 'new run')
        self.store.finish(new_id, 'Success')
        window.refresh()
        self.assertEqual(str(window.table.item(new_id, 'values')[0]), '1')
        with patch('pages.solve_history.filedialog.asksaveasfilename', return_value=str(report)):
            window.export_all()
        self.assertIn('<h2>#1 new run</h2>', report.read_text())
        self.assertFalse(self.errors)

    def test_history_failure_does_not_change_codec_result(self):
        page = self.root.pages['Data Hashing']
        page.select_quick_algo('Base64')
        page.input_box.insert('1.0', 'SGVsbG8=')
        with patch.object(self.store, 'begin', side_effect=OSError('disk full')), \
             patch('Tools.history_hooks.messagebox.showwarning') as warning:
            page.process_data()
        warning.assert_called_once()
        self.assertEqual(page.output_bytes, b'Hello')
        self.assertIn('disk full', self.root.history_error)
        self.assertFalse(self.errors)

    def test_pipeline_send_to_hashing_links_selected_output(self):
        hashing = self.root.pages['Data Hashing']
        hashing.select_quick_algo('Base64')
        page = self.root.pages['Pipeline']
        page.engine.text_tools['emit_base64'] = lambda p: [sys.executable, '-c', "print('SGVsbG8=')"]
        failures = []
        def interact():
            win = next(w for w in page.winfo_children() if isinstance(w, ctk.CTkToplevel))
            try:
                run_and_wait(win)
                output = next(w for w in descendants(win) if isinstance(w, ctk.CTkTextbox))
                start = output.search('SGVsbG8=', '1.0', stopindex='end')
                self.assertTrue(start)
                output.tag_add('sel', start, f'{start}+8c')
                invoked = False
                for menu in descendants(win):
                    if not isinstance(menu, tk.Menu) or menu.index('end') is None:
                        continue
                    for index in range(menu.index('end') + 1):
                        if menu.type(index) == 'command' and menu.entrycget(index, 'label') == 'Send to Data Hashing':
                            menu.invoke(index)
                            invoked = True
                self.assertTrue(invoked)
                button(win, 'Finish').invoke()
            except BaseException as error:
                failures.append(error)
                win.destroy()
        self.root.after(80, interact)
        page.open_step_window({'name': 'emit_base64'}, b'', b'', [], False, step_mode=True)
        if failures:
            raise failures[0]
        records = self.store.list_events()
        self.assertEqual(len(records), 2)
        self.assertEqual(records[1]['parent_id'], records[0]['id'])
        self.assertEqual(records[1]['input'], 'SGVsbG8=')
        self.assertEqual(records[1]['output'], 'Hello')
        self.assertFalse(self.errors)

    def test_selection_survives_filters_and_pages(self):
        ids = []
        for category in ['Pipeline', 'Data Hashing', 'File Inspection']:
            event_id = self.store.begin(category, category)
            self.store.finish(event_id, 'Success')
            ids.append(event_id)
        window = history_hooks.open_history(self.root, 'Pipeline')
        window.table.selection_set(ids[0])
        window.set_category('Data Hashing')
        window.table.selection_set(ids[1])
        report = self.work / 'mixed.html'
        with patch('pages.solve_history.filedialog.asksaveasfilename', return_value=str(report)):
            window.export_selected()
        self.assertIn('2 event(s)', report.read_text())
        window.PAGE_SIZE = 1
        window.set_category('All')
        window.turn_page(2)
        window.table.selection_set(ids[2])
        with patch('pages.solve_history.filedialog.asksaveasfilename', return_value=str(report)):
            window.export_selected()
        self.assertIn('3 event(s)', report.read_text())
        self.assertFalse(self.errors)

    def test_pipeline_steps_share_group_and_link_forwarded_input(self):
        page = self.root.pages['Pipeline']
        page.set_pipeline_mode('Step')
        page.engine.text_tools['first_history'] = lambda p: [sys.executable, '-c', "print('payload', end='')"]
        page.engine.text_tools['second_history'] = lambda p: [sys.executable, '-c',
            'import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())']
        page.add_tool_node('first_history')
        failures, visits = [], []
        def interact():
            win = next(w for w in page.winfo_children() if isinstance(w, ctk.CTkToplevel))
            try:
                visits.append(win.title())
                run_and_wait(win)
                if len(visits) == 1:
                    next(w for w in descendants(win) if isinstance(w, ctk.CTkComboBox)).set('second_history')
                    self.root.after(80, interact)
                    button(win, 'Continue').invoke()
                else:
                    button(win, 'Finish').invoke()
            except BaseException as error:
                failures.append(error)
                win.destroy()
        self.root.after(80, interact)
        page.run_pipeline()
        if failures:
            raise failures[0]
        records = self.store.list_events('Pipeline')
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]['group_id'], records[1]['group_id'])
        self.assertEqual(records[1]['parent_id'], records[0]['id'])
        self.assertEqual(records[1]['input'], records[0]['output'])
        self.assertEqual(records[1]['output'], 'payload')
        self.assertFalse(self.errors)

    def test_clear_is_blocked_while_operation_running(self):
        event_id = history_hooks.begin(self.root, category='Pipeline', tool='test')
        window = history_hooks.open_history(self.root)
        with patch('pages.solve_history.messagebox.showinfo') as info, \
             patch('pages.solve_history.messagebox.askyesno') as confirm:
            window.clear_history()
        info.assert_called_once()
        confirm.assert_not_called()
        self.assertIsNotNone(self.store.get_event(event_id))
