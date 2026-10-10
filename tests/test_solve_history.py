import os
import tempfile
import unittest
import sqlite3
import gc
import warnings
from unittest.mock import patch
from pathlib import Path

from Tools.solve_history import MAX_FILES, MAX_FILES_TOTAL, MAX_TEXT, SolveHistoryStore, export_html


class SolveHistoryStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_begin_finish_filter_order_and_persistence(self):
        db_path = self.root / "history.sqlite3"
        store = SolveHistoryStore(db_path)
        first = store.begin("File Inspection", "strings", "input", {"mode": "all"}, files=["evidence.bin"])
        second = store.begin("Data Hashing", "sha256", group_id="retry-group", parent_id=first)
        store.finish(first, "Failed", error="bad input")
        store.finish(second, "Success", output_data="ok")

        events = store.list_events()
        self.assertEqual([event["id"] for event in events], [first, second])
        self.assertEqual([event["seq"] for event in events], [1, 2])
        self.assertEqual(events[0]["status"], "Failed")
        self.assertEqual(events[1]["group_id"], "retry-group")
        self.assertEqual(events[1]["parent_id"], first)
        self.assertEqual(store.list_events("Data Hashing")[0]["id"], second)
        self.assertEqual(store.get_event(first)["files"], ["evidence.bin"])
        store.close()

        reopened = SolveHistoryStore(db_path)
        self.assertEqual(reopened.get_event(second)["output"], "ok")
        reopened.close()

    def test_clear_preserves_other_categories_and_does_not_touch_files(self):
        db_path = self.root / "history.sqlite3"
        evidence = self.root / "real-evidence.bin"
        evidence.write_bytes(b"keep me")
        store = SolveHistoryStore(db_path)
        removed = store.begin("Pipeline", "run", files=[str(evidence)])
        kept = store.begin("Data Hashing", "md5")
        self.assertEqual(store.clear("Pipeline"), 1)
        self.assertIsNone(store.get_event(removed))
        self.assertEqual(store.get_event(kept)["seq"], 2)
        self.assertEqual(evidence.read_bytes(), b"keep me")
        self.assertEqual(store.clear("Pipeline"), 0)
        next_id = store.begin('File Inspection', 'strings', parent_id=kept)
        self.assertEqual(store.get_event(next_id)['seq'], 3)
        self.assertEqual(store.get_event(next_id)['parent_id'], kept)
        store.close()

    def test_clear_all_restarts_numbering_after_reopen_without_reusing_ids(self):
        path = self.root / 'history.sqlite3'
        with SolveHistoryStore(path) as store:
            old_id = store.begin('Pipeline', 'first')
            store.begin('Data Hashing', 'second')
            self.assertEqual(store.clear(), 2)
        with SolveHistoryStore(path) as store:
            new_id = store.begin('File Inspection', 'new', parent_id=old_id)
            self.assertEqual(store.get_event(new_id)['seq'], 1)
            self.assertNotEqual(new_id, old_id)
            self.assertIsNone(store.get_event(old_id))

    def test_clearing_last_category_and_already_empty_history_resets_counter(self):
        with SolveHistoryStore(self.root / 'history.sqlite3') as store:
            store.begin('Pipeline', 'first')
            store.begin('Pipeline', 'second')
            self.assertEqual(store.clear('Pipeline'), 2)
            self.assertEqual(store.clear('All'), 0)
            event_id = store.begin('Pipeline', 'new')
            self.assertEqual(store.get_event(event_id)['seq'], 1)

    def test_clear_and_counter_reset_roll_back_together(self):
        with SolveHistoryStore(self.root / 'history.sqlite3') as store:
            first = store.begin('Pipeline', 'first')
            store._connection.execute("""CREATE TEMP TRIGGER fail_counter_reset
                BEFORE UPDATE ON solve_history_meta WHEN NEW.value = 1
                BEGIN SELECT RAISE(ABORT, 'test reset failure'); END""")
            with self.assertRaises(sqlite3.DatabaseError):
                store.clear()
            self.assertIsNotNone(store.get_event(first))
            second = store.begin('Pipeline', 'second')
            self.assertEqual(store.get_event(second)['seq'], 2)

    def test_redaction_binary_and_explicit_truncation(self):
        store = SolveHistoryStore(self.root / "history.sqlite3")
        event_id = store.begin(
            "Pipeline",
            "runner",
            input_data=b"password=byte-secret",
            options=["--password", "dont-save", "--token=also-secret", "key=value-secret"],
        )
        store.finish(event_id, "Success", output_data="x" * (MAX_TEXT + 500))
        event = store.get_event(event_id)
        self.assertEqual(event["input"], "password=[REDACTED]")
        self.assertNotIn("dont-save", event["options"])
        self.assertNotIn("also-secret", event["options"])
        self.assertNotIn("value-secret", event["options"])
        self.assertIn("[REDACTED]", event["options"])
        self.assertLessEqual(len(event["output"]), MAX_TEXT)
        self.assertIn("truncated", event["output"])
        text_id = store.begin("Pipeline", "bytes", input_data=b"text bytes")
        self.assertEqual(store.get_event(text_id)["input"], "text bytes")
        store.close()

    def test_files_and_tool_are_bounded(self):
        store = SolveHistoryStore(self.root / "history.sqlite3")
        event_id = store.begin("Pipeline", "t" * (MAX_TEXT + 100), files=["f" * 5000] * (MAX_FILES + 50))
        event = store.get_event(event_id)
        self.assertLessEqual(len(event["tool"]), MAX_TEXT)
        self.assertLessEqual(len(event["files"]), MAX_FILES)
        self.assertLessEqual(len(str(event["files"])), MAX_FILES_TOTAL + 100)
        self.assertIn("truncated", " ".join(event["files"]))
        store.close()

    def test_failed_finish_transaction_does_not_report_success(self):
        store = SolveHistoryStore(self.root / "history.sqlite3")
        event_id = store.begin("Data Hashing", "sha256")
        with self.assertRaises(KeyError):
            store.finish("not-an-event", "Success", output_data="should not persist")
        self.assertEqual(store.get_event(event_id)["status"], "Running")
        with self.assertRaises(ValueError):
            store.finish(event_id, "Unknown")
        self.assertEqual(store.get_event(event_id)["status"], "Running")
        store.close()

    def test_new_database_files_are_private_but_existing_mode_is_unchanged(self):
        db_path = self.root / "new.sqlite3"
        store = SolveHistoryStore(db_path)
        store.begin("Pipeline", "run")
        self.assertTrue(os.stat(db_path).st_mode & 0o077 == 0)
        for suffix in ("-wal", "-shm"):
            sidecar = Path(str(db_path) + suffix)
            if sidecar.exists():
                self.assertTrue(os.stat(sidecar).st_mode & 0o077 == 0)
        store.close()

        existing = self.root / "existing.sqlite3"
        existing.touch(mode=0o666)
        os.chmod(existing, 0o644)
        existing_store = SolveHistoryStore(existing)
        self.assertEqual(os.stat(existing).st_mode & 0o777, 0o644)
        existing_store.close()

    def test_export_html_escapes_values_and_does_not_overwrite_db(self):
        db_path = self.root / "history.sqlite3"
        store = SolveHistoryStore(db_path)
        event_id = store.begin("File Inspection", "<tool>", input_data="<script>alert(1)</script>")
        store.finish(event_id, "Success", output_data='</article><a href="evil">x</a>')
        report = self.root / "history.html"
        export_html(report, store.list_events())
        text = report.read_text(encoding="utf-8")
        self.assertNotIn("<script>", text)
        self.assertNotIn("<a ", text)
        self.assertIn("&lt;script&gt;", text)
        self.assertIn("&lt;a href=&quot;evil&quot;&gt;", text)

        original_db = db_path.read_bytes()
        with self.assertRaises(ValueError):
            export_html(db_path, store.list_events())
        self.assertEqual(db_path.read_bytes(), original_db)
        store.close()

    def test_failed_export_and_corrupt_database_preserve_existing_files(self):
        report = self.root / 'report.html'
        report.write_text('original', encoding='utf-8')
        with patch('Tools.solve_history.os.replace', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                export_html(report, [])
        self.assertEqual(report.read_text(), 'original')
        self.assertEqual(list(self.root.glob('.solve-history-*.tmp')), [])
        broken = self.root / 'broken.sqlite3'
        broken.write_bytes(b'not a database')
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always', ResourceWarning)
            with self.assertRaises(sqlite3.DatabaseError):
                SolveHistoryStore(broken)
            gc.collect()
        self.assertFalse([w for w in caught if 'unclosed database' in str(w.message)])
        self.assertEqual(broken.read_bytes(), b'not a database')


if __name__ == "__main__":
    unittest.main()
