import hashlib
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from Tools.stream_capture import PREVIEW_BYTES, run_capture
from Tools.solve_history import SolveHistoryStore, export_html


class LargeStreamTests(unittest.TestCase):
    def test_output_budget_and_complete_command_report(self):
        with patch('Tools.stream_capture.MAX_CAPTURE_BYTES', 1024):
            capture = run_capture([sys.executable, '-c',
                "import sys; sys.stdout.write('A'*4096); sys.stderr.write('error tail')"])
        self.addCleanup(capture.close)
        self.assertIsNone(capture.returncode)
        self.assertIn(b'limit', capture.stderr)
        report = capture.report_path().read_bytes()
        self.assertIn(b'A'*4096, report)
        self.assertIn(b'error tail', report)

    def test_large_binary_stdout_and_stderr_preserved(self):
        capture = run_capture([sys.executable, '-c',
            "import sys; sys.stdout.buffer.write(b'\\x00\\xff'*(1024*1024)); sys.stderr.buffer.write(b'E'*(256*1024))"])
        self.addCleanup(capture.close)
        self.assertEqual(capture.returncode, 0)
        self.assertEqual(len(capture.stdout), PREVIEW_BYTES)
        self.assertEqual(capture.stdout_file.read_bytes(), b'\x00\xff'*(1024*1024))
        self.assertEqual(capture.stderr_file.stat().st_size, 256*1024)

    def test_stream_file_to_stdin_and_cancel(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/'source.bin'
            source.write_bytes(b'01234567'*(512*1024))
            capture = run_capture([sys.executable, '-c',
                'import sys,shutil; shutil.copyfileobj(sys.stdin.buffer,sys.stdout.buffer)'], input_data=source)
            try:
                self.assertEqual(hashlib.sha256(capture.stdout_file.read_bytes()).digest(), hashlib.sha256(source.read_bytes()).digest())
            finally:
                capture.close()
            stop = threading.Event()
            timer = threading.Timer(.1, stop.set)
            timer.start()
            capture = run_capture([sys.executable, '-c', 'import time; time.sleep(5)'], cancel_event=stop)
            try:
                self.assertIsNone(capture.returncode)
                self.assertIn(b'Cancelled', capture.stderr)
                self.assertTrue(source.exists())
            finally:
                capture.close()
                timer.join()

    def test_history_sql_pages_and_streamed_export(self):
        with tempfile.TemporaryDirectory() as directory, SolveHistoryStore(Path(directory)/'history.db') as store:
            for index in range(240):
                event = store.begin('Pipeline', str(index))
                store.finish(event, 'Success', output_data=b'A'*20000)
            page = store.list_events(limit=100, offset=200, summaries=True)
            self.assertEqual(len(page), 40)
            self.assertEqual(page[0]['seq'], 201)
            self.assertEqual(page[0]['output'], '')
            destination = Path(directory)/'report.html'
            export_html(destination, store.iter_events())
            self.assertIn('240 event(s)', destination.read_text())
            self.assertIn('<h2>#240 239</h2>', destination.read_text())

    def test_gemini_large_prompt_uses_stdin_not_argv(self):
        from pages.gemini import GeminiPage
        seen = {}
        def capture(command, **kwargs):
            seen.update(command=command, stdin=kwargs['input_data'])
            return SimpleNamespace(stdout=b'ok', stderr=b'', returncode=0, stdout_file=None, stderr_file=None)
        page = SimpleNamespace(gemini_cmd='not-run', model_name='test', cli_workdir=None,
                               _stop_requested=False, _build_env=lambda: {})
        with patch('pages.gemini.run_capture', side_effect=capture):
            self.assertEqual(GeminiPage.call_gemini_cli(page, 'A'*(256*1024)), 'ok')
        self.assertEqual(len(seen['stdin']), 256*1024)
        self.assertLess(sum(map(len, seen['command'])), 200)

    def test_gemini_rejects_oversize_and_binary_attachments_without_sending(self):
        from tests.test_integration_safety import GeminiSafetyTests
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/'input.txt'
            page = GeminiSafetyTests().page()
            page.call_gemini_cli = Mock()
            for data in (b'A'*(1024*1024+1), b'\x00\xff'):
                source.write_bytes(data)
                page.process_request(str(source))
                page.call_gemini_cli.assert_not_called()
                self.assertIn('Error', page.finish_response.call_args.args[0])

    def test_gemini_oversized_response_never_executes_partial_tags(self):
        from tests.test_integration_safety import GeminiSafetyTests
        from unittest.mock import Mock
        page = GeminiSafetyTests().page()
        def reply(_):
            page._full_response_path = Path('/unused-test-output')
            return '[EXEC]should-not-run[/EXEC]'
        page.call_gemini_cli = reply
        page.ask_action_confirm = Mock()
        with patch('pages.gemini.run_capture') as launch:
            page.process_request('analyze')
        launch.assert_not_called()
        page.ask_action_confirm.assert_not_called()


@unittest.skipUnless(os.environ.get('DISPLAY'), 'Needs X display')
class LargePipelineGuiTests(unittest.TestCase):
    from tests.test_pipeline_output_gui import PipelineOutputGuiTests
    setUp = PipelineOutputGuiTests.setUp
    step = PipelineOutputGuiTests.step

    def test_large_output_preview_save_and_forward_are_complete(self):
        import customtkinter as ctk
        from tests.test_pipeline_output_gui import button, run_and_wait, descendants
        payload_size = 2*1024*1024
        self.page.engine.text_tools['large'] = lambda p: [sys.executable, '-c',
            f"import sys; sys.stdout.buffer.write(b'A'*{payload_size})"]
        saved = self.work/'saved.bin'
        ticks=[]
        def act(win):
            self.root.after(10, lambda: ticks.append(True))
            run_and_wait(win)
            output = next(w for w in descendants(win) if isinstance(w, ctk.CTkTextbox))
            self.assertLess(len(output.get('1.0','end')), 300000)
            self.assertIn('Preview only', output.get('1.0','end'))
            with patch('pages.pipeline.filedialog.asksaveasfilename', return_value=str(saved)):
                button(win, 'Save Output as File').invoke()
            deadline=time.monotonic()+5
            while not saved.exists():
                self.root.update()
                self.assertLess(time.monotonic(), deadline)
                time.sleep(.01)
            button(win, 'Next').invoke()
        forwarded = self.step('large', act)
        self.assertIsInstance(forwarded, Path)
        self.assertEqual(forwarded.stat().st_size, payload_size)
        self.assertEqual(saved.read_bytes(), b'A'*payload_size)
        self.assertTrue(ticks)
        self.page.engine.text_tools['length'] = lambda p: [sys.executable, '-c',
            'import sys; print(len(sys.stdin.buffer.read()))']
        def next_act(win):
            run_and_wait(win)
            button(win, 'Next').invoke()
        self.assertEqual(self.step('length', next_act, previous=forwarded), str(payload_size).encode()+b'\n')


@unittest.skipUnless(os.environ.get('DISPLAY'), 'Needs X display')
class LargeInspectionGuiTests(unittest.TestCase):
    from tests.test_inspection_gui import InspectionGuiTests
    setUp = InspectionGuiTests.setUp
    wait_done = InspectionGuiTests.wait_done

    def test_over_64_mib_file_and_single_long_line(self):
        path = Path(self.temp.name)/'large.txt'
        with path.open('wb') as stream:
            for _ in range(65):
                stream.write(b'A'*(1024*1024))
        self.page.tool_menu.set('Strings')
        self.page.regex_var.set('')
        self.page.load_files([str(path)])
        ticks=[]
        self.root.after(10, lambda: ticks.append(True))
        self.wait_done()
        box=self.page.result_boxes[str(path)]
        self.assertLess(len(box.textbox.get('1.0','end')), 140000)
        self.assertEqual(Path(box.full_output_path).stat().st_size, path.stat().st_size)
        self.assertIn('Preview only', box.textbox.get('1.0','end'))
        self.assertTrue(ticks)


@unittest.skipUnless(os.environ.get('DISPLAY'), 'Needs X display')
class LargeCodecGuiTests(unittest.TestCase):
    from tests.test_codec_gui import CodecGuiRegressionTests
    setUpClass = CodecGuiRegressionTests.setUpClass.__func__
    setUpClass = classmethod(setUpClass)
    setUp = CodecGuiRegressionTests.setUp
    tearDown = CodecGuiRegressionTests.tearDown

    def test_file_load_and_mode_change_keep_full_input(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/'large.txt'
            content = 'abc\r\n' * 10000
            source.write_bytes(content.encode())
            with patch('pages.data_hash.filedialog.askopenfilename', return_value=str(source)):
                self.page.browse_file()
            self.page.set_mode('Hash')
            self.page.algo_menu.set('sha256')
            self.page.process_data()
            ticks = []
            self.root.after(10, lambda: ticks.append(True))
            deadline = time.monotonic()+5
            while not self.page.output_bytes:
                self.root.update()
                self.assertLess(time.monotonic(), deadline)
                time.sleep(.01)
            self.assertTrue(ticks)
            self.assertLess(len(self.page.input_box.get('1.0','end')), len(content))
            self.assertEqual(self.page.output_bytes, hashlib.sha256(content.encode()).hexdigest().encode())
            # Cursor movement must not replace full file contents with its preview.
            self.page._input_changed()
            self.assertEqual(self.page._snapshot_source(), content)

    def test_old_worker_cannot_overwrite_new_input(self):
        from pages.data_hash import DataHashPage
        self.page.set_mode('Hash')
        self.page.algo_menu.set('sha256')
        self.page.input_box.insert('1.0', 'old\n'*10000)
        release, started = threading.Event(), threading.Event()
        original = DataHashPage._compute_snapshot
        def compute(snapshot):
            if len(snapshot[0]) > 20000:
                started.set()
                release.wait(3)
            return original(snapshot)
        with patch.object(DataHashPage, '_compute_snapshot', side_effect=compute):
            try:
                self.page.process_data()
                self.assertTrue(started.wait(1))
                future = self.page._active_future
                self.page.input_box.delete('1.0','end')
                self.page.input_box.insert('1.0','new')
                self.page.process_data()
                release.set()
                future.result(timeout=3)
                deadline = time.monotonic()+.15
                while time.monotonic() < deadline:
                    self.root.update()
                    time.sleep(.01)
                self.assertEqual(self.page.output_bytes, hashlib.sha256(b'new').hexdigest().encode())
            finally:
                release.set()

    def test_background_heartbeat_and_no_stale_output(self):
        from pages.data_hash import DataHashPage
        self.page.set_mode('Hash')
        self.page.algo_menu.set('sha256')
        source='A'*(2*1024*1024)
        self.page.input_box.insert('1.0',source)
        original=DataHashPage._compute_snapshot
        def delayed(snapshot):
            time.sleep(.2)
            return original(snapshot)
        ticks=[]
        with patch.object(DataHashPage, '_compute_snapshot', side_effect=delayed):
            self.page.output_bytes = b'old result'
            self.page.process_data()
            self.assertEqual(self.page.output_bytes, b'')
            self.assertEqual(self.page.save_raw_button.cget('state'), 'disabled')
            self.root.after(10, lambda: ticks.append(True))
            deadline=time.monotonic()+5
            while not self.page.output_bytes:
                self.root.update()
                self.assertLess(time.monotonic(), deadline)
                time.sleep(.01)
        self.assertTrue(ticks)
        self.assertEqual(self.page.output_bytes, hashlib.sha256(source.encode()).hexdigest().encode())

    def test_paged_view_preserves_unicode_boundaries(self):
        from Tools.text_view import open_text_view, PAGE_CHARS
        from tests.test_pipeline_output_gui import button, descendants
        import customtkinter as ctk
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/'unicode.txt'
            content = 'ก'*(PAGE_CHARS-1) + '€end\n'
            source.write_text(content, encoding='utf-8')
            win = open_text_view(self.root, source)
            def wait_button(label):
                deadline = time.monotonic()+5
                while button(win, label).cget('state') == 'disabled':
                    self.root.update()
                    self.assertLess(time.monotonic(), deadline)
                    time.sleep(.01)
            try:
                wait_button('Next')
                box = next(w for w in descendants(win) if isinstance(w, ctk.CTkTextbox))
                first = box.get('1.0','end-1c')
                button(win, 'Next').invoke()
                wait_button('Previous')
                self.assertEqual(first + box.get('1.0','end-1c'), content)
            finally:
                win.destroy()
