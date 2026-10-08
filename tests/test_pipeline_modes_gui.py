"""Mode switch and exploratory Step flow, using real Tk and temporary files."""
import os
import sys
import shlex
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

import customtkinter as ctk
from tests import test_pipeline_output_gui as gui


@unittest.skipUnless(os.environ.get('DISPLAY'), 'Needs X display')
class PipelineModesGuiTests(unittest.TestCase):
    setUp = gui.PipelineOutputGuiTests.setUp

    def step(self, name, action, previous=b''):
        failures = []
        def interact():
            win = next(w for w in self.page.winfo_children() if isinstance(w, ctk.CTkToplevel))
            try:
                action(win)
            except BaseException as error:
                failures.append(error)
            finally:
                if win.winfo_exists():
                    win.destroy()
        self.root.after(80, interact)
        result = self.page.open_step_window({'name': name}, previous, previous, [], False, step_mode=True)
        if failures:
            raise failures[0]
        self.assertFalse(self.errors)
        return result

    def choose_next(self, win, name):
        menu = next(w for w in gui.descendants(win) if isinstance(w, ctk.CTkComboBox))
        menu.set(name)

    def send_to_input(self, win, text):
        history = next(w for w in gui.descendants(win) if isinstance(w, ctk.CTkTextbox))
        history.delete('1.0', 'end')
        history.insert('1.0', text)
        history.tag_add('sel', '1.0', 'end-1c')
        for menu in gui.descendants(win):
            if not isinstance(menu, tk.Menu) or menu.index('end') is None:
                continue
            for index in range(menu.index('end') + 1):
                if menu.type(index) == 'command' and menu.entrycget(index, 'label') == 'Send to Input':
                    menu.invoke(index)
                    return
        self.fail('Send to Input menu not found')

    def test_send_to_input_refreshes_stdin_preview_and_preserves_data(self):
        source = self.work / 'previous.bin'
        source.write_bytes(b'previous bytes')
        self.page.engine.text_tools['echo_input'] = lambda p: [
            sys.executable, '-c', 'import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())',
        ]
        selected = 'SGVsbG8=; $(echo unsafe) "quoted" ข้อมูล'
        def interact(win):
            command = shlex.join(self.page.engine.build_command('echo_input', [], None, []))
            preview = next(w for w in gui.descendants(win)
                           if isinstance(w, ctk.CTkLabel) and w.cget('text') == command)
            entry = next(w for w in gui.descendants(win) if isinstance(w, ctk.CTkEntry))
            self.send_to_input(win, selected)
            self.assertEqual(entry.get(), selected)
            self.assertEqual(preview.cget('text'), command + ' ' + selected)
            entry.delete(0, 'end')
            self.assertEqual(preview.cget('text'), command)
            entry.insert(0, 'x' * 1000)
            self.assertEqual(preview.cget('text'), command + ' ' + 'x' * 1000)
            self.send_to_input(win, selected)
            gui.run_and_wait(win)
            gui.button(win, 'Finish').invoke()
        result = self.step('echo_input', interact, source)
        self.assertEqual(result['output'], selected.encode())

    def test_send_to_input_refreshes_file_command_without_keypress(self):
        source = self.work / 'selected file "quoted".bin'
        source.write_bytes(b'file contents')
        self.page.engine.file_tools['file_input'] = lambda f, p: [
            sys.executable, '-c', 'import pathlib, sys; sys.stdout.buffer.write(pathlib.Path(sys.argv[1]).read_bytes())', f,
        ]
        def interact(win):
            self.send_to_input(win, str(source))
            expected = shlex.join(self.page.engine.build_command('file_input', [], str(source), []))
            self.assertTrue(any(isinstance(w, ctk.CTkLabel) and w.cget('text') == expected
                                for w in gui.descendants(win)))
            gui.run_and_wait(win)
            gui.button(win, 'Finish').invoke()
        self.assertEqual(self.step('file_input', interact)['output'], b'file contents')

    def test_english_ui_preserves_tool_output(self):
        original = 'ผลลัพธ์จากเครื่องมือ'
        self.page.engine.text_tools['language_test'] = lambda p: [
            sys.executable, '-c', f'print({original!r})',
        ]
        def interact(win):
            gui.run_and_wait(win)
            history = next(w for w in gui.descendants(win) if isinstance(w, ctk.CTkTextbox))
            text = history.get('1.0', 'end')
            self.assertIn(original, text)
            self.assertIn('[Running]', text)
            self.assertIn('[Success]', text)
            self.assertNotIn('Exit code', text)
            menu = next(w for w in gui.descendants(win) if isinstance(w, ctk.CTkComboBox))
            self.assertEqual(menu.get(), 'Select the next tool')
            for widget in gui.descendants(win):
                if isinstance(widget, (ctk.CTkButton, ctk.CTkLabel, ctk.CTkRadioButton)):
                    # Command previews are user/tool data, not translated UI.
                    self.assertNotRegex(str(widget.cget('text')).replace(original, ''), r'[\u0e00-\u0e7f]')
            self.page.engine.text_tools['language_test'] = lambda p: [
                sys.executable, '-c', 'raise SystemExit(2)',
            ]
            gui.run_and_wait(win)
            self.assertIn('[Failed]', history.get('1.0', 'end'))
            self.assertNotIn('Exit code', history.get('1.0', 'end'))
            gui.button(win, 'Close Analysis').invoke()
        self.assertIsNone(self.step('language_test', interact))

    def test_toggle_is_before_run_and_preserves_both_workspaces(self):
        self.assertEqual(self.page.pipeline_mode, 'Auto')
        self.assertLess(self.page.mode_btn.winfo_x(), self.page.run_btn.winfo_x())
        self.page.add_tool_node('strings')
        self.page.nodes[0]['params'] = '-n 6'
        self.page.add_tool_node('grep')
        auto_nodes = list(self.page.nodes)
        original = self.work / 'original.bin'
        original.write_bytes(b'original')
        self.page.original_file_path = str(original)
        temporary = self.page.write_temp_file(b'binary')
        self.addCleanup(lambda: Path(temporary).unlink(missing_ok=True))
        self.page.register_temp_artifact(temporary)
        self.page.mode_btn.invoke()
        self.root.update()
        self.assertEqual(self.page.pipeline_mode, 'Step')
        self.assertEqual(self.page.nodes, [])
        self.assertIsNone(self.page.original_file_path)
        self.assertTrue(all(not n['frame'].winfo_ismapped() for n in auto_nodes))
        self.page.add_tool_node('file')
        self.page.add_tool_node('strings')
        self.assertEqual([n['name'] for n in self.page.nodes], ['strings'])
        self.page.mode_btn.invoke()
        self.root.update()
        self.assertEqual(self.page.nodes, auto_nodes)
        self.assertEqual(self.page.nodes[0]['params'], '-n 6')
        self.assertEqual(self.page.original_file_path, str(original))
        self.assertTrue(Path(temporary).exists())
        self.page.mode_btn.invoke()
        self.page.clear_pipeline()
        self.assertTrue(Path(temporary).exists(), 'Clearing Step must not delete Auto artifacts')
        self.page.mode_btn.invoke()
        self.assertEqual(len(self.page.nodes), 2)

    def test_auto_keeps_existing_run_order(self):
        self.page.add_tool_node('strings')
        self.page.add_tool_node('grep')
        with patch.object(self.page, 'open_step_window', side_effect=[b'first', b'second']) as step:
            self.page.run_pipeline()
        self.assertEqual(step.call_count, 2)
        self.assertEqual(step.call_args_list[1].args[1], b'first')
        self.assertTrue(step.call_args_list[1].args[4])
        self.assertNotIn('step_mode', step.call_args.kwargs)
        self.assertEqual(self.page.run_logs[-1]['output'], b'second')

    def test_dynamic_file_to_text_flow_then_finish(self):
        self.page.set_pipeline_mode('Step')
        raw = b'\x00\xff\x80hello'
        self.page.engine.text_tools['writer'] = lambda p: [
            sys.executable, '-c', "from pathlib import Path; Path('result.bin').write_bytes(" + repr(raw) + ")",
        ]
        self.page.engine.text_tools['reader'] = lambda p: [
            sys.executable, '-c', 'import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())',
        ]
        self.page.add_tool_node('writer')
        failures = []
        visits = []
        def interact():
            win = next(w for w in self.page.winfo_children() if isinstance(w, ctk.CTkToplevel))
            try:
                visits.append(win.title())
                self.assertEqual(self.page.mode_btn.cget('state'), 'disabled')
                gui.run_and_wait(win)
                self.root.update_idletasks()
                self.assertTrue(gui.button(win, 'Continue').winfo_ismapped())
                for label in ('Run', 'Cancel', 'Close Analysis', 'Finish'):
                    control = gui.button(win, label)
                    self.assertTrue(control.winfo_ismapped(), label)
                    self.assertLessEqual(control.winfo_rooty() + control.winfo_height(),
                                         win.winfo_rooty() + win.winfo_height(), label)
                if len(visits) == 1:
                    self.assertTrue(gui.button(win, 'Browse result file').winfo_ismapped())
                    history = next(w for w in gui.descendants(win) if isinstance(w, ctk.CTkTextbox))
                    self.assertGreaterEqual(history.winfo_height(), 120, 'Keep history readable beside file/continuation controls')
                    self.choose_next(win, 'reader')
                    gui.button(win, 'Continue').invoke()
                    self.assertTrue(win.winfo_exists(), 'Must explicitly choose result file')
                    choice = next(w for w in gui.descendants(win) if isinstance(w, ctk.CTkRadioButton))
                    choice.invoke()
                    self.root.after(80, interact)
                    gui.button(win, 'Continue').invoke()
                else:
                    gui.button(win, 'Finish').invoke()
            except BaseException as error:
                failures.append(error)
                win.destroy()
        self.root.after(80, interact)
        self.page.run_pipeline()
        if failures:
            raise failures[0]
        self.assertFalse(self.errors)
        self.assertEqual(len(visits), 2)
        self.assertEqual([n['name'] for n in self.page.nodes], ['writer', 'reader'])
        self.assertEqual(self.page.run_logs[0]['output'], self.work / 'result.bin')
        self.assertEqual(self.page.run_logs[1]['output'], raw)
        self.assertFalse(hasattr(self.page, 'mode_hint'))
        self.assertEqual(self.page.mode_btn.cget('state'), 'normal')
        self.assertTrue((self.work / 'result.bin').exists())

    def test_stdout_choice_unknown_tool_and_retry_failure(self):
        self.page.engine.text_tools['both'] = lambda p: [
            sys.executable, '-c', "from pathlib import Path; Path('out').touch(); print('text')",
        ]
        def interact(win):
            self.assertFalse(gui.button(win, 'Continue').winfo_ismapped())
            gui.run_and_wait(win)
            self.choose_next(win, 'unknown-tool')
            gui.button(win, 'Continue').invoke()
            self.assertTrue(win.winfo_exists())
            self.page.engine.text_tools['both'] = lambda p: [sys.executable, '-c', 'raise SystemExit(2)']
            gui.run_and_wait(win)
            self.root.update_idletasks()
            self.assertFalse(gui.button(win, 'Continue').winfo_ismapped())
            gui.button(win, 'Finish').invoke()
            self.assertTrue(win.winfo_exists())
            self.page.engine.text_tools['both'] = lambda p: [
                sys.executable, '-c', "from pathlib import Path; Path('out2').touch(); print('new')",
            ]
            gui.run_and_wait(win)
            self.choose_next(win, 'base64_decode')
            stdout = next(w for w in gui.descendants(win)
                          if isinstance(w, ctk.CTkRadioButton) and w.cget('text') == 'Forward stdout')
            stdout.invoke()
            gui.button(win, 'Continue').invoke()
        result = self.step('both', interact)
        self.assertEqual(result['output'], b'new\n')
        self.assertEqual(result['next_tool'], 'base64_decode')

    def test_finish_does_not_require_a_forwarding_choice(self):
        self.page.engine.text_tools['quiet'] = lambda p: [
            sys.executable, '-c', "from pathlib import Path; Path('out').touch()",
        ]
        def interact(win):
            gui.run_and_wait(win)
            gui.button(win, 'Finish').invoke()
        result = self.step('quiet', interact)
        self.assertIsNone(result['next_tool'])
        self.assertEqual(result['files'], [self.work / 'out'])

    def test_deleted_output_blocks_forwarding_and_close_is_abort(self):
        self.page.engine.text_tools['quiet'] = lambda p: [
            sys.executable, '-c', "from pathlib import Path; Path('out').touch()",
        ]
        def interact(win):
            gui.run_and_wait(win)
            self.choose_next(win, 'strings')
            next(w for w in gui.descendants(win) if isinstance(w, ctk.CTkRadioButton)).invoke()
            (self.work / 'out').unlink()
            gui.button(win, 'Continue').invoke()
            self.assertTrue(win.winfo_exists())
            gui.button(win, 'Close Analysis').invoke()
        self.assertIsNone(self.step('quiet', interact))

    def test_saved_and_template_load_into_auto_without_destroying_step(self):
        self.page.set_pipeline_mode('Step')
        self.page.add_tool_node('strings')
        self.page.load_template('Basic Recon')
        self.assertEqual(self.page.pipeline_mode, 'Auto')
        self.assertEqual([n['name'] for n in self.page.nodes], ['file', 'strings', 'uniq'])
        self.page.set_pipeline_mode('Step')
        self.assertEqual([n['name'] for n in self.page.nodes], ['strings'])
        data = {'saved_pipelines': [{'pipeline_name': 'test', 'steps': [{'name': 'file'}]}]}
        with patch('pages.pipeline.saved_pipelines', return_value=data):
            self.page.load_saved_pipeline_to_canvas('test')
        self.assertEqual(self.page.pipeline_mode, 'Auto')
        self.assertEqual([n['name'] for n in self.page.nodes], ['file'])
        self.page.set_pipeline_mode('Step')
        self.assertEqual([n['name'] for n in self.page.nodes], ['strings'])

    def test_mode_change_blocked_while_running(self):
        self.page._pipeline_running = True
        with patch('pages.pipeline.messagebox.showwarning') as warning:
            self.assertFalse(self.page.toggle_pipeline_mode())
        self.assertEqual(self.page.pipeline_mode, 'Auto')
        warning.assert_called_once()
        self.page._pipeline_running = False

    def test_empty_step_still_explains_required_tool_selection(self):
        self.page.set_pipeline_mode('Step')
        with patch('pages.pipeline.messagebox.showwarning') as warning:
            self.page.run_pipeline()
        warning.assert_called_once()
        self.assertIn('Select a tool', warning.call_args.args[1])
        self.assertEqual(self.page.run_btn.cget('state'), 'normal')

    def test_closing_page_during_step_does_not_update_destroyed_widgets(self):
        self.page.set_pipeline_mode('Step')
        self.page.add_tool_node('strings')
        # Model the modal returning after its owning page has been destroyed.
        with patch.object(self.page, 'open_step_window', side_effect=lambda *a, **kw: self.page.destroy()):
            self.page.run_pipeline()
        self.assertFalse(self.errors)
        self.assertFalse(self.page._pipeline_running)
