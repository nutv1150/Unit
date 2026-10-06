"""Run with xvfb-run -a .venv/bin/python -m unittest discover -s tests -p test_pipeline_output_gui.py."""
import os
import shutil
import sys
import tempfile
import unittest
import time
from pathlib import Path
from unittest.mock import patch

import customtkinter as ctk
from pages.pipeline import PipelinePage


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


def button(widget, label):
    return next(w for w in descendants(widget)
                if isinstance(w, ctk.CTkButton) and w.cget('text') == label)


def run_and_wait(widget):
    run = button(widget, 'Run')
    run.invoke()
    deadline = time.monotonic() + 10
    while run.cget('state') == 'disabled':
        widget.update()
        if time.monotonic() >= deadline:
            raise AssertionError('Tool did not finish')
        time.sleep(0.01)


@unittest.skipUnless(os.environ.get('DISPLAY'), 'Needs X display')
class PipelineOutputGuiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        cwd = Path.cwd()
        os.chdir(self.work)
        self.addCleanup(os.chdir, cwd)
        self.root = ctk.CTk()
        self.root.geometry('1200x850')
        def cleanup():
            for callback in self.root.tk.call('after', 'info'):
                self.root.tk.call('after', 'cancel', callback)
            self.root.destroy()
        self.addCleanup(cleanup)
        self.errors = []
        self.root.report_callback_exception = lambda *args: self.errors.append(args)
        frame = ctk.CTkFrame(self.root)
        frame.pack(fill='both', expand=True)
        self.page = PipelinePage(frame)
        self.page.pack(fill='both', expand=True)
        self.root.update()

    def step(self, name, action, previous=b'', last=False):
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
        output = self.page.open_step_window({'name': name}, previous, previous, [], last)
        if failures:
            raise failures[0]
        self.assertFalse(self.errors)
        return output

    def test_silent_file_requires_selection_then_routes_to_file_and_text_tools(self):
        result_path = self.work / 'ผล ลัพธ์.bin'
        self.page.engine.text_tools['writer'] = lambda p: [
            sys.executable, '-c', "from pathlib import Path; Path('ผล ลัพธ์.bin').write_bytes(b'\\x00\\xffhello\\n'); Path('other.txt').touch()",
        ]
        def choose(win):
            run_and_wait(win)
            self.root.update_idletasks()
            button(win, 'Next').invoke()
            self.assertTrue(win.winfo_exists(), 'Next must wait for file selection')
            choices = [w for w in descendants(win) if isinstance(w, ctk.CTkRadioButton)]
            self.assertEqual(len(choices), 2)
            choice = next(w for w in choices if 'ผล ลัพธ์.bin' in w.cget('text'))
            self.assertIn('ผล ลัพธ์.bin', choice.cget('text'))
            self.assertTrue(choice.winfo_ismapped())
            choice.invoke()
            button(win, 'Next').invoke()
        selected = self.step('writer', choose)
        self.assertEqual(selected, result_path)
        self.assertNotIn(str(result_path), self.page.temp_artifacts)

        self.page.engine.file_tools['file_reader'] = lambda f, p: [
            sys.executable, '-c', 'from pathlib import Path; import sys; sys.stdout.buffer.write(Path(sys.argv[1]).read_bytes())', f,
        ]
        def read_file(win):
            entry = next(w for w in descendants(win) if isinstance(w, ctk.CTkEntry))
            self.assertEqual(entry.get(), str(result_path))
            run_and_wait(win)
            button(win, 'Close').invoke()
        self.assertEqual(self.step('file_reader', read_file, selected, True), b'\x00\xffhello\n')

        self.page.engine.text_tools['text_reader'] = lambda p: [
            sys.executable, '-c', 'import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())',
        ]
        def read_text(win):
            run_and_wait(win)
            button(win, 'Close').invoke()
        self.assertEqual(self.step('text_reader', read_text, selected, True), b'\x00\xffhello\n')
        self.page.cleanup_pipeline_artifacts()
        self.assertTrue(result_path.exists())

    def test_cancel_keeps_event_loop_live_and_blocks_canvas_mutation(self):
        self.page.add_tool_node('strings')
        self.page.engine.text_tools['slow'] = lambda p: [sys.executable, '-c', 'import time; time.sleep(20)']
        def interact(win):
            ticks = []
            button(win, 'Run').invoke()
            self.root.after(20, lambda: ticks.append(True))
            with patch('pages.pipeline.messagebox.showwarning') as warning:
                self.page.clear_pipeline()
                self.assertEqual(len(self.page.nodes), 1)
                warning.assert_called_once()
            deadline = time.monotonic() + 5
            while not ticks and time.monotonic() < deadline:
                self.root.update()
                time.sleep(.01)
            self.assertTrue(ticks)
            button(win, 'Cancel').invoke()
            while button(win, 'Run').cget('state') == 'disabled' and time.monotonic() < deadline:
                self.root.update()
                time.sleep(.01)
            self.assertEqual(button(win, 'Run').cget('state'), 'normal')
            self.assertFalse(self.page.active_runs)
            button(win, 'Next').invoke()
            self.assertTrue(win.winfo_exists())
        self.assertIsNone(self.step('slow', interact))

    def test_saved_pipeline_hides_placeholder_and_retains_options(self):
        data = {'saved_pipelines': [{'pipeline_name': 'test', 'steps': [
            {'name': 'strings', 'params': '-n 6', 'options': [], 'user_description': 'saved'}]}]}
        with patch('pages.pipeline.saved_pipelines', return_value=data):
            self.page.load_saved_pipeline_to_canvas('test')
        self.root.update()
        self.assertFalse(self.page.placeholder.winfo_ismapped())
        self.assertEqual(self.page.nodes[0]['params'], '-n 6')
        self.page.clear_pipeline()
        self.root.update()
        self.assertTrue(self.page.placeholder.winfo_ismapped())

    def test_failed_saved_pipeline_write_preserves_canvas(self):
        self.page.add_tool_node('strings')
        before = list(self.page.nodes)
        with patch('pages.pipeline.saved_pipelines', return_value={'saved_pipelines': []}), \
             patch('pages.pipeline.write_json', side_effect=OSError('disk full')), \
             patch('pages.pipeline.messagebox.showerror') as error:
            self.page.finalize_wizard_pipeline([{'name': 'file'}], 'test')
        error.assert_called_once()
        self.assertEqual(self.page.nodes, before)

    def test_retry_failure_clears_selection_and_blocks_next(self):
        self.page.engine.text_tools['writer'] = lambda p: [
            sys.executable, '-c', "from pathlib import Path; Path('file').touch()",
        ]
        def interact(win):
            run_and_wait(win)
            choice = next(w for w in descendants(win) if isinstance(w, ctk.CTkRadioButton))
            choice.invoke()
            self.page.engine.text_tools['writer'] = lambda p: [sys.executable, '-c', 'raise SystemExit(2)']
            run_and_wait(win)
            self.assertFalse(any(isinstance(w, ctk.CTkRadioButton) for w in descendants(win)))
            button(win, 'Next').invoke()
            self.assertTrue(win.winfo_exists())
        self.assertIsNone(self.step('writer', interact))

    def test_manual_result_choice_and_deleted_file_validation(self):
        result_path = self.work / 'manual.bin'
        result_path.write_bytes(b'manual')
        self.page.engine.text_tools['quiet'] = lambda p: [sys.executable, '-c', 'pass']
        def interact(win):
            run_and_wait(win)
            with patch('pages.pipeline.filedialog.askopenfilename', return_value=str(result_path)):
                button(win, 'Browse result file').invoke()
            result_path.unlink()
            button(win, 'Next').invoke()
            self.assertTrue(win.winfo_exists())
            result_path.write_bytes(b'restored')
            button(win, 'Next').invoke()
        self.assertEqual(self.step('quiet', interact), result_path)

    def test_file_plus_stdout_requires_explicit_choice(self):
        self.page.engine.text_tools['both'] = lambda p: [
            sys.executable, '-c', "from pathlib import Path; Path('file').touch(); print('log message')",
        ]
        def interact(win):
            run_and_wait(win)
            button(win, 'Next').invoke()
            self.assertTrue(win.winfo_exists())
            stdout = next(w for w in descendants(win)
                          if isinstance(w, ctk.CTkRadioButton) and w.cget('text') == 'ส่งต่อ stdout')
            stdout.invoke()
            button(win, 'Next').invoke()
        self.assertEqual(self.step('both', interact), b'log message\n')

    @unittest.skipUnless(shutil.which('strings'), 'Needs strings')
    def test_strings_without_files_hides_file_picker_even_after_previous_run(self):
        source = self.work / 'sample.iso'
        source.write_bytes(b'\x00UNIT pipeline text\x00')
        self.page.engine.file_tools['strings_test'] = lambda f, p: [
            sys.executable, '-c', "from pathlib import Path; Path('output.txt').touch()",
        ]
        def interact(win):
            run_and_wait(win)
            self.root.update_idletasks()
            choice = next(w for w in descendants(win) if isinstance(w, ctk.CTkRadioButton))
            self.assertTrue(choice.winfo_ismapped())
            choice.invoke()
            self.page.engine.file_tools['strings_test'] = lambda f, p: ['strings', f]
            run_and_wait(win)
            self.root.update_idletasks()
            self.assertFalse(button(win, 'Browse result file').winfo_ismapped())
            self.assertFalse(any(isinstance(w, ctk.CTkRadioButton) for w in descendants(win)))
            lists = [w for w in descendants(win) if isinstance(w, ctk.CTkScrollableFrame)]
            self.assertTrue(lists)
            self.assertTrue(all(not w.winfo_ismapped() for w in lists))
            button(win, 'Next').invoke()
        self.assertEqual(self.step('strings_test', interact, source), b'UNIT pipeline text\n')


if __name__ == '__main__':
    unittest.main()
