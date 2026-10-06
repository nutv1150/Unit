import os
import gzip
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from Pipeline.output_files import output_locations, snapshot_files
from Pipeline.pipeline_engine import PipelineEngine
from Tools.artifact_bridge import resolve_file_input


class OutputFilesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        cwd = Path.cwd()
        os.chdir(self.work)
        self.addCleanup(os.chdir, cwd)
        self.engine = PipelineEngine()

    def run_script(self, script):
        self.engine.text_tools['writer'] = lambda p: [sys.executable, '-c', script]
        return self.engine.run_text_tool('writer', b'', detailed=True)

    def test_silent_success_discovers_nested_empty_and_changed_files(self):
        (self.work / 'unchanged.txt').write_text('old')
        changed = self.work / 'changed.txt'
        changed.write_text('old')
        result = self.run_script(
            "from pathlib import Path; Path('nested').mkdir(); "
            "Path('nested/ผล ลัพธ์.bin').write_bytes(b'\\x00\\xff'); "
            "Path('empty.txt').touch(); Path('changed.txt').write_text('new value')"
        )
        self.assertTrue(result.succeeded)
        self.assertEqual(result.stdout, b'')
        self.assertEqual(set(result.files), {
            changed, self.work / 'empty.txt', self.work / 'nested/ผล ลัพธ์.bin',
        })
        resolved = resolve_file_input(str(result.files[0]).encode())
        self.assertEqual(resolved['mode'], 'existing_path')

    def test_failed_run_and_retry_never_publish_partial_or_stale_files(self):
        good = self.run_script("from pathlib import Path; Path('ok').touch()")
        self.assertEqual(good.files, [self.work / 'ok'])
        failed = self.run_script(
            "from pathlib import Path; import sys; Path('partial').touch(); "
            "sys.stderr.write('bad input'); sys.exit(2)"
        )
        self.assertFalse(failed.succeeded)
        self.assertEqual(failed.files, [])
        self.assertEqual(failed.stderr, b'bad input')
        self.assertEqual(self.run_script('pass').files, [])

    def test_stdout_and_stderr_stay_separate_and_legacy_api_still_returns_bytes(self):
        result = self.run_script("import sys; sys.stdout.buffer.write(b'\\x00\\xff'); sys.stderr.write('warning')")
        self.assertTrue(result.succeeded)
        self.assertEqual(result.stdout, b'\x00\xff')
        self.assertEqual(result.stderr, b'warning')
        self.assertEqual(self.engine.run_text_tool('writer', b''), b'\x00\xffwarning')

    def test_explicit_destination_outside_cwd_and_input_are_handled(self):
        with tempfile.TemporaryDirectory() as other:
            output = Path(other) / 'new folder' / 'output.bin'
            source = self.work / 'source.bin'
            source.write_bytes(b'data')
            self.engine.file_tools['test_openssl'] = lambda f, p: ['openssl', 'enc', '-out', str(output), '-in', f]
            def execute(*args, **kwargs):
                output.parent.mkdir()
                output.write_bytes(b'\x00\xff')
                source.write_bytes(b'changed input')
                return subprocess.CompletedProcess(args[0], 0, b'', b'')
            with patch('Pipeline.pipeline_engine.subprocess.run', side_effect=execute):
                result = self.engine.run_file_tool('test_openssl', str(source), detailed=True)
            self.assertEqual(result.files, [output])

    def test_known_output_flags_not_confused_with_grep_or_cut(self):
        path = self.work / 'outside'
        for cmd in [['openssl', '-out', str(path)], ['7z', 'x', '-o' + str(path)],
                    ['unzip', 'a.zip', '-d', str(path)], ['dd', 'of=' + str(path)]]:
            self.assertIn(path, output_locations(cmd))
        self.assertEqual(output_locations(['grep', '-o', 'pattern']), [self.work])
        self.assertEqual(output_locations(['cut', '-d', ':']), [self.work])

    def test_symlinks_ignored_and_scan_limit_is_explicit(self):
        (self.work / 'file').touch()
        (self.work / 'link').symlink_to(self.work, target_is_directory=True)
        files, complete = snapshot_files([self.work])
        self.assertTrue(complete)
        self.assertEqual(list(files), [self.work / 'file'])
        self.assertFalse(snapshot_files([self.work], limit=1)[1])

    def test_command_errors_do_not_publish_files(self):
        for error in [FileNotFoundError(), subprocess.TimeoutExpired('tool', 30), PermissionError('denied')]:
            with patch('Pipeline.pipeline_engine.subprocess.run', side_effect=error):
                result = self.engine.run_text_tool('base64_decode', b'', detailed=True)
            self.assertFalse(result.succeeded)
            self.assertEqual(result.files, [])
            self.assertTrue(result.stderr)

    @unittest.skipUnless(shutil.which('gzip'), 'Needs gzip')
    def test_real_gzip_success_without_stdout(self):
        source = self.work / 'example.bin.gz'
        payload = b'\x00\xffUNIT\n'
        source.write_bytes(gzip.compress(payload))
        result = self.engine.run_file_tool('gzip_decompress', str(source), '-d', detailed=True)
        self.assertTrue(result.succeeded, result.stderr)
        self.assertEqual(result.stdout, b'')
        self.assertEqual(result.files, [self.work / 'example.bin'])
        self.assertEqual(result.files[0].read_bytes(), payload)


if __name__ == '__main__':
    unittest.main()
