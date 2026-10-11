import tempfile
import unittest
from pathlib import Path

from Tools.inspection_stream import ExtractionCancelled, extract_strings


class InspectionStreamTests(unittest.TestCase):
    def run_extract(self, data, cancelled=lambda: False):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, destination = root / "source.bin", root / "result.txt"
            source.write_bytes(data)
            extract_strings(source, destination, cancelled)
            return destination.read_bytes()

    def test_invalid_utf8_after_valid_prefix_is_not_duplicated(self):
        self.assertEqual(self.run_extract("prefix\n".encode() + b"\xffSECRET"), b"  prefix\n  SECRET\n")

    def test_ascii_run_crossing_chunk_boundary(self):
        run = b"A" * (64 * 1024 - 2) + b"CROSSING" + b"\0"
        self.assertEqual(self.run_extract(b"\xff" + run), b"  " + run[:-1] + b"\n")

    def test_one_megabyte_ascii_run_is_preserved(self):
        run = b"Z" * (1024 * 1024)
        self.assertEqual(self.run_extract(b"\xff" + run + b"\0"), b"  " + run + b"\n")

    def test_utf8_long_line_and_multibyte_boundary(self):
        text = "x" * (64 * 1024 - 1) + "€" + "y" * 100
        self.assertEqual(self.run_extract(text.encode()), text.encode())

    def test_cancellation(self):
        calls = [0]
        def cancelled():
            calls[0] += 1
            return calls[0] > 1
        with self.assertRaises(ExtractionCancelled):
            self.run_extract(b"A" * (128 * 1024), cancelled)


if __name__ == "__main__":
    unittest.main()
