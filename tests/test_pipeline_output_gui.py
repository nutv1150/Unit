"""Run with xvfb-run -a .venv/bin/python -m unittest discover -s tests -p test_pipeline_output_gui.py."""
import os
import sys
import tempfile
import unittest
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
            button(win, 'Run').invoke()
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
            button(win, 'Run').invoke()
            button(win, 'Close').invoke()
        self.assertEqual(self.step('file_reader', read_file, selected, True), b'\x00\xffhello\n')

        self.page.engine.text_tools['text_reader'] = lambda p: [
            sys.executable, '-c', 'import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())',
        ]
        def read_text(win):
            button(win, 'Run').invoke()
            button(win, 'Close').invoke()
        self.assertEqual(self.step('text_reader', read_text, selected, True), b'\x00\xffhello\n')
        self.page.cleanup_pipeline_artifacts()
        self.assertTrue(result_path.exists())

    def test_retry_failure_clears_selection_and_blocks_next(self):
        self.page.engine.text_tools['writer'] = lambda p: [
            sys.executable, '-c', "from pathlib import Path; Path('file').touch()",
        ]
        def interact(win):
            button(win, 'Run').invoke()
            choice = next(w for w in descendants(win) if isinstance(w, ctk.CTkRadioButton))
            choice.invoke()
            self.page.engine.text_tools['writer'] = lambda p: [sys.executable, '-c', 'raise SystemExit(2)']
            button(win, 'Run').invoke()
            self.assertFalse(any(isinstance(w, ctk.CTkRadioButton) for w in descendants(win)))
            button(win, 'Next').invoke()
            self.assertTrue(win.winfo_exists())
        self.assertIsNone(self.step('writer', interact))

    def test_manual_result_choice_and_deleted_file_validation(self):
        result_path = self.work / 'manual.bin'
        result_path.write_bytes(b'manual')
        self.page.engine.text_tools['quiet'] = lambda p: [sys.executable, '-c', 'pass']
        def interact(win):
            button(win, 'Run').invoke()
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
            button(win, 'Run').invoke()
            button(win, 'Next').invoke()
            self.assertTrue(win.winfo_exists())
            stdout = next(w for w in descendants(win)
                          if isinstance(w, ctk.CTkRadioButton) and w.cget('text') == 'ส่งต่อ stdout')
            stdout.invoke()
            button(win, 'Next').invoke()
        self.assertEqual(self.step('both', interact), b'log message\n')


if __name__ == '__main__':
    unittest.main()
