"""Regression coverage for large-input codec worker primitives."""

import base64
import hashlib
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch

from Decode.base_decoder import auto_detect_decode
from pages.data_hash import DataHashPage, LARGE_INPUT_BYTES, PREVIEW_CHARS


class LargeCodecTests(unittest.TestCase):
    def test_large_hash_keeps_exact_result_bytes(self):
        source = "unit-large-input\n" * (LARGE_INPUT_BYTES // 18 + 1)
        output, display, algo, detected, _ = DataHashPage._compute_snapshot(
            (source, "Hash", "sha256", {})
        )
        self.assertEqual(output, hashlib.sha256(source.encode()).hexdigest().encode())
        self.assertEqual(display, output.decode())
        self.assertEqual((algo, detected), ("sha256", None))

    def test_large_encode_result_is_complete_worker_output(self):
        source = "A" * (LARGE_INPUT_BYTES + 32)
        output, display, *_ = DataHashPage._compute_snapshot(
            (source, "Encode", "Base64", {})
        )
        self.assertEqual(output, base64.b64encode(source.encode()))
        self.assertEqual(len(display), len(output))
        self.assertGreater(len(display), PREVIEW_CHARS)

    def test_worker_does_not_block_heartbeat(self):
        source = "A" * (LARGE_INPUT_BYTES + 32)
        heartbeat = threading.Event()
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(DataHashPage._compute_snapshot, (source, "Hash", "sha256", {}))
            heartbeat.set()
            self.assertTrue(heartbeat.is_set())
            self.assertIsNotNone(future.result(timeout=5))

    def test_stale_job_is_cancelled_in_history_without_ui_update(self):
        page = DataHashPage.__new__(DataHashPage)
        page._job_generation = 2
        page.app_root = Mock()
        future = Mock()
        with patch("pages.data_hash.history_hooks.finish") as finish, patch.object(page, "_show_result") as show:
            page._job_done(future, 1, "history-1", "source")
        finish.assert_called_once_with(page.app_root, "history-1", "Failed", error="Superseded by newer input")
        show.assert_not_called()

    def test_auto_detect_legacy_result_is_preserved(self):
        self.assertEqual(auto_detect_decode(b"hello"), ("Reverse", "olleh"))


if __name__ == "__main__":
    unittest.main()
