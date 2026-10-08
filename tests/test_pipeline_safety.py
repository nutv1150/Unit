import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from Pipeline.pipeline_engine import PipelineEngine
from Pipeline.config_store import saved_pipelines, write_json


class PipelineSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        previous = Path.cwd()
        os.chdir(self.work)
        self.addCleanup(os.chdir, previous)
        self.engine = PipelineEngine()

    def test_url_decode_is_data_not_a_program(self):
        for value, expected in [(b'hello%20world%FF', b'hello world\xff'),
                                (b'print(41 + 1)', b'print(41 + 1)')]:
            result = self.engine.run_text_tool('url_decode', value, detailed=True)
            self.assertTrue(result.succeeded, result.stderr)
            self.assertEqual(result.stdout, expected)

    def test_named_decoders_have_decode_defaults(self):
        for tool, value, expected in [('base64_decode', b'SGVsbG8=', b'Hello'),
                                     ('base32_decode', b'JBSWY3DP', b'Hello'),
                                     ('hex_decode', b'00ff41', b'\x00\xffA')]:
            result = self.engine.run_text_tool(tool, value, detailed=True)
            self.assertTrue(result.succeeded, result.stderr)
            self.assertEqual(result.stdout, expected)

    def test_archive_tools_extract_without_requiring_mode_checkbox(self):
        import tarfile
        import zipfile
        source = self.work / 'payload.txt'
        source.write_bytes(b'archive fixture')
        tar_path = self.work / 'source.tar'
        with tarfile.open(tar_path, 'w') as archive:
            archive.add(source, arcname='inside.txt')
        zip_path = self.work / 'source.zip'
        with zipfile.ZipFile(zip_path, 'w') as archive:
            archive.writestr('inside.txt', b'archive fixture')
        for tool, archive, options in [
            ('tar_extract', tar_path, lambda dest: ['-C', str(dest)]),
            ('7zip_extract', zip_path, lambda dest: ['-o' + str(dest)]),
        ]:
            with self.subTest(tool=tool):
                dest = self.work / tool
                dest.mkdir()
                result = self.engine.run_file_tool(tool, str(archive), options(dest), detailed=True)
                self.assertTrue(result.succeeded, result.stderr)
                self.assertEqual((dest / 'inside.txt').read_bytes(), b'archive fixture')
                self.assertIn(dest / 'inside.txt', result.files)

    def test_packet_tools_read_input_instead_of_starting_capture(self):
        for tool in ('tshark', 'tcpdump'):
            self.assertEqual(self.engine.build_command(tool, file_path='sample.pcap'),
                             [tool, '-r', 'sample.pcap'])

    def test_literal_argument_and_after_input_order(self):
        command = self.engine.build_command('strings', ['-n', '4'], '/tmp/with space.bin', ['tail'])
        self.assertEqual(command, ['strings', '-n', '4', '/tmp/with space.bin', 'tail'])
        result = self.engine.run_text_tool('grep', b'hello world\n', ['hello world'], detailed=True)
        self.assertEqual(result.stdout, b'hello world\n')

    def test_legacy_manual_openssl_input_is_not_duplicated(self):
        path = str(self.work / "b'input file.bin")
        command = self.engine.build_command('openssl enc', ['-d', '-in'], path, ['-out', 'out.bin'])
        self.assertEqual(command, ['openssl', 'enc', '-d', '-in', path, '-out', 'out.bin'])
        command = self.engine.build_command('openssl enc', ['-in', path], path)
        self.assertEqual(command.count('-in'), 1)
        with self.assertRaises(ValueError):
            self.engine.build_command('openssl enc', ['-in', 'different.bin'], path)

    def test_dd_input_value_and_space_path(self):
        source = self.work / "b'input file.bin"
        source.write_bytes(b'headerPAYLOAD')
        result = self.engine.run_file_tool('dd', str(source), ['bs=1', 'skip=6', 'of=output file.bin'], detailed=True)
        self.assertTrue(result.succeeded, result.stderr)
        self.assertEqual((self.work / 'output file.bin').read_bytes(), b'PAYLOAD')

    def test_cancellation_returns_failure_not_partial_success(self):
        cancel = threading.Event()
        timer = threading.Timer(.15, cancel.set)
        timer.start()
        self.addCleanup(timer.cancel)
        result = self.engine._run_command([sys.executable, '-c', 'import time;time.sleep(5)'],
                                           detailed=True, cancel_event=cancel)
        self.assertFalse(result.succeeded)
        self.assertIn(b'Cancelled', result.stderr)
        self.assertEqual(result.files, [])

    def test_invalid_config_does_not_overwrite_or_crash_engine(self):
        path = self.work / 'tools.json'
        path.write_text('{broken')
        with patch.object(PipelineEngine, 'CUSTOM_TOOL_FILE', str(path)):
            engine = PipelineEngine()
            self.assertTrue(engine.load_error)
            with self.assertRaises(ValueError):
                engine.save_custom_tool('new', 'strings', 'file', 'Custom')
        self.assertEqual(path.read_text(), '{broken')

    def test_saved_config_and_atomic_failure(self):
        path = self.work / 'saved.json'
        original = '{broken'
        path.write_text(original)
        with self.assertRaises(ValueError):
            saved_pipelines(path)
        self.assertEqual(path.read_text(), original)
        with patch('Pipeline.config_store.os.replace', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                write_json(path, {'saved_pipelines': []})
        self.assertEqual(path.read_text(), original)

    def test_document_aes_file_output_to_strings_and_xor(self):
        # Synthetic fixture exercises the documented method, not a hardcoded solver.
        if not shutil.which('openssl') or not shutil.which('strings'):
            self.skipTest('Needs OpenSSL and strings')
        from Tools.extra_tools import bitwise_unmask
        flag = b'flag{fixture_round_trip}'
        key = bytes(range(16))
        masked = ','.join(f'0x{x ^ 0x4a:02x}' for x in flag)
        payload = f'$key = 0x4A\n$data = @({masked})\n'.encode()
        payload += b'\x00' * (-len(payload) % 16)
        raw = self.work / 'original.bin'
        raw.write_bytes(payload)
        enc = self.work / 'encrypted sample.iso'
        encrypted = subprocess.run(['openssl', 'enc', '-aes-128-ecb', '-nopad', '-K', key.hex(),
                                    '-in', str(raw), '-out', str(enc)], capture_output=True)
        self.assertEqual(encrypted.returncode, 0, encrypted.stderr)
        result = self.engine.run_file_tool('openssl enc', str(enc),
                   ['-d', '-aes-128-ecb', '-nopad', '-K', key.hex(), '-out', 'result.iso'], detailed=True)
        self.assertTrue(result.succeeded, result.stderr)
        self.assertEqual(result.files, [self.work / 'result.iso'])
        self.assertEqual(result.files[0].read_bytes(), payload)
        text = self.engine.run_file_tool('strings', str(result.files[0]), detailed=True)
        self.assertTrue(text.succeeded)
        self.assertIn(flag.decode(), bitwise_unmask(text.stdout.decode(), '0x4A'))


if __name__ == '__main__':
    unittest.main()
