"""Compatibility examples from the supplied thesis; production has no challenge data."""
import base64
import hashlib
import runpy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from Decode.base_decoder import decode_data, decode_to_bytes, auto_detect_decode
from Encode.base_encoder import encode_data
from Hashing.hash_utils import hash_data
from Tools.extra_tools import bitwise_unmask


class DocumentFlowTests(unittest.TestCase):
    def test_many_files_and_metadata_base64(self):
        examples = {
            'TDRyZzNfbnVtYjNyXzBmX2ZpbDNzXzRuZF9kM3A3aA==': 'L4rg3_numb3r_0f_fil3s_4nd_d3p7h',
            'cGljb0NURnt0aGVfbTN0YWRhdGFfMXNfbW9kaWZpZWR9': 'picoCTF{the_m3tadata_1s_modified}',
        }
        for encoded, text in examples.items():
            self.assertEqual(decode_data(encoded, 'Base64'), text)

    def test_vault_reverse_bytes_xor(self):
        reversed_text = decode_data('=wnf4VHe99Xf85Xe', 'Reverse')
        raw = decode_to_bytes(reversed_text, 'Base64')
        self.assertEqual(raw.hex(), '797e7c7d7f7d7875787e7c')
        self.assertIn('52013149420', bitwise_unmask(raw.hex(), '0x4C'))

    def test_custom_hex_rot_and_interencdec(self):
        self.assertEqual(decode_to_bytes('FG EC EF', 'Hex', alphabet='AJIHGFEDCBjihgfe'), b'The')
        text = 'flag{wtctt-dcode-master-2025}'
        self.assertEqual(decode_data(encode_data(text, 'ROT:47:ascii'), 'ROT:47:ascii'), text)
        encoded = 'd3BqdkpBTXtqaGx6aHlfazNqeTl3YTNrX2kyMDRoa2o2fQ=='
        caesar = decode_data(encoded, 'Base64')
        self.assertEqual(auto_detect_decode(caesar.encode())[1], 'picoCTF{caesar_d3cr9pt3d_b204adc6}')

    def test_base45_space_is_a_digit_and_invalid_padding_errors(self):
        for value in ['A', 'Hello!!', 'ไทย', ' leading ']:
            self.assertEqual(decode_data(encode_data(value, 'Base45'), 'Base45'), value)
        self.assertEqual(decode_data('BB8', 'Base45'), 'AB')
        with self.assertRaises(ValueError):
            decode_to_bytes('SGVsbG8', 'Base64')
        for invalid in ['A', ':::']:
            with self.assertRaises(ValueError):
                decode_to_bytes(invalid, 'Base45')

    def test_exact_hash_and_onlyone_record_scan(self):
        value = ' leading \n'
        self.assertEqual(hash_data(value, 'sha256'), hashlib.sha256(value.encode()).hexdigest())
        source = Path(__file__).parents[1] / '0nLy0ne.txt'
        if not source.exists():
            self.skipTest('Optional original ONLYONE fixture unavailable')
        lines = source.read_text().splitlines()
        mismatches = []
        for line in lines[1:]:
            body, stored = decode_data(line, 'Base64').rsplit('|', 1)
            calculated = hash_data(body, 'sha256')[:8]
            if calculated != stored:
                mismatches.append((body, stored, calculated))
        self.assertEqual(len(mismatches), 1)
        self.assertTrue(mismatches[0][0].startswith('565382|'))

    def test_hidden_data_benchmark_with_synthetic_archive_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            raw = b"7z\xbc\xaf\x27\x1c" + bytes(1200)
            source = work / 'reversed.txt'
            source.write_text(base64.b64encode(raw).decode()[::-1])
            module = runpy.run_path(str(Path(__file__).with_name('test_hidden_data_real.py')))
            with patch.object(sys, 'argv', ['benchmark', str(source), str(work / 'artifacts')]):
                module['main']()
            self.assertEqual((work / 'artifacts/hidden_data_layer1.7z').read_bytes(), raw)
