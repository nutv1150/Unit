"""Run with xvfb-run -a .venv/bin/python -m unittest discover -s tests -p test_workspace_gui.py."""
import os
import tempfile
import unittest
from pathlib import Path
import customtkinter as ctk
from pages.my_tools import MyToolsPage
from pages.challenge import ChallengePage
from Tools.workspace_store import ChallengeStore


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


def button(widget, text):
    return next(w for w in descendants(widget) if isinstance(w, ctk.CTkButton) and w.cget('text') == text)


@unittest.skipUnless(os.environ.get('DISPLAY'), 'Needs X display (use xvfb-run)')
class WorkspaceGuiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = ctk.CTk()
        self.root.geometry('1200x800')
        def cleanup():
            # Cancel Tk/CTk scheduled callbacks before destroying the test interpreter.
            for callback in self.root.tk.call('after', 'info'):
                self.root.tk.call('after', 'cancel', callback)
            self.root.destroy()
        self.addCleanup(cleanup)
        self.errors = []
        self.root.report_callback_exception = lambda *args: self.errors.append(args)

    def test_group_dialog_chips_search_and_themes(self):
        calls = []
        page = MyToolsPage(self.root, lambda *args: calls.append(args), storage_path=Path(self.temp.name)/'groups.json')
        page.pack(fill='both', expand=True)
        self.root.update()
        win = page._open_dialog()
        self.root.update()
        button(win, 'Save').invoke()
        self.assertEqual(page.groups, [])
        entry = next(w for w in descendants(win) if isinstance(w, ctk.CTkEntry))
        entry.insert(0, 'Decode toolkit')
        checks = [w for w in descendants(win) if isinstance(w, ctk.CTkCheckBox)]
        checks[0].select(); checks[1].select(); checks[3].select()
        button(win, 'Save').invoke()
        self.root.update()
        self.assertEqual(len(page.groups), 1)
        for name in ('Base64 decode', 'ROT decode', 'XOR bitwise'):
            button(page, '● '+name).invoke()
        self.assertEqual(calls, [('Data Hashing', 'Base64'), ('Data Hashing', 'ROT'), ('Data Hashing', 'XOR')])
        edit = page._open_dialog(page.groups[0]); self.root.update()
        self.assertEqual(sum(w.get() for w in descendants(edit) if isinstance(w, ctk.CTkCheckBox)), 3)
        edit.destroy()
        page.search.set('missing'); self.root.update()
        self.assertTrue(any(isinstance(w, ctk.CTkLabel) and w.cget('text') == 'No groups found' for w in descendants(page)))
        page.search.set('')
        for mode in ('Dark', 'Light'):
            ctk.set_appearance_mode(mode); self.root.update()
        page._delete(page.groups[0]); self.root.update()
        confirmation = next(w for w in descendants(page) if isinstance(w, ctk.CTkToplevel))
        button(confirmation, 'Cancel').invoke()
        self.assertEqual(len(page.groups), 1)
        page._delete(page.groups[0]); self.root.update()
        confirmation = next(w for w in descendants(page) if isinstance(w, ctk.CTkToplevel))
        button(confirmation, 'Delete').invoke()
        self.assertEqual(page.groups, [])
        self.assertFalse(self.errors)

    def test_timer_edit_validation_close_and_reload(self):
        path = Path(self.temp.name)/'challenges.json'
        page = ChallengePage(self.root, storage_path=path); page.pack(fill='both', expand=True)
        self.root.update()
        page.name_entry.insert(0, 'TCTT2026'); page.total_entry.insert(0, '20'); page._create()
        rid = page.store.rows[0]['id']
        now = [1000.0]; page.store.clock = lambda: now[0]
        win = page._open_editor(rid); self.root.update()
        button(win, 'Start').invoke(); now[0] += 5
        score = next(w for w in descendants(win) if isinstance(w, ctk.CTkEntry))
        score.delete(0, 'end'); score.insert(0, '21'); button(win, 'Save').invoke()
        self.assertEqual(page.store.get(rid)['solved_items'], 0)
        score.delete(0, 'end'); score.insert(0, '8'); button(win, 'Save').invoke()
        page.save_before_close()
        saved = ChallengeStore(path).get(rid)
        self.assertEqual(saved['elapsed_seconds'], 5)
        self.assertEqual(saved['solved_items'], 8)
        self.assertFalse(saved['is_running'])
        self.root.update()
        self.assertFalse(self.errors)

    def test_navigation_routes_and_close_hook(self):
        from app import UNITApp
        from types import SimpleNamespace
        from unittest.mock import Mock
        hashing, inspection, portal, challenge = Mock(), Mock(), Mock(), Mock()
        app = SimpleNamespace(pages={'Data Hashing': hashing, 'File Inspection': inspection,
                                     'App Portal': portal, 'Challenge': challenge},
                              switch_page=Mock(), destroy=Mock())
        UNITApp.navigate_to(app, 'Data Hashing', 'XOR')
        hashing.set_mode.assert_called_with('Bitwise')
        hashing.select_quick_algo.assert_called_with('XOR Mask')
        UNITApp.navigate_to(app, 'Data Hashing', 'Base64')
        hashing.set_mode.assert_called_with('Decode')
        hashing.select_quick_algo.assert_called_with('Base64')
        UNITApp.navigate_to(app, 'File Inspection', 'zsteg Analysis')
        inspection.tool_menu.set.assert_called_with('zsteg Analysis')
        UNITApp.navigate_to(app, 'App Portal', 'Wireshark')
        portal.search_var.set.assert_called_with('Wireshark')
        portal.launch_app.assert_not_called()
        UNITApp.on_close(app)
        challenge.save_before_close.assert_called_once()
        app.destroy.assert_called_once()
        app.destroy.reset_mock()
        challenge.save_before_close.side_effect = OSError('disk full')
        UNITApp.on_close(app)
        app.destroy.assert_not_called()
