import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from Tools.workspace_store import ChallengeStore, elapsed, format_elapsed, make_group, load_records, save_records


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'state.json'
        self.now = 1000.0
        self.store = ChallengeStore(self.path, clock=lambda: self.now)

    def test_timer_pause_resume_restart_and_close(self):
        rid = self.store.create('TCTT2026', '20')
        self.store.update(rid, '3', True)
        self.now += 10.5
        self.assertEqual(elapsed(self.store.get(rid), self.now), 10.5)
        self.store.update(rid, 4, False)
        self.now += 100
        self.assertEqual(elapsed(self.store.get(rid), self.now), 10.5)
        self.store.update(rid, 4, True)
        self.now += 5
        self.store.pause_all()
        reopened = ChallengeStore(self.path)
        self.assertEqual(reopened.get(rid)['elapsed_seconds'], 15.5)
        self.assertFalse(reopened.get(rid)['is_running'])
        self.assertEqual(format_elapsed(90061), '25:01:01')

    def test_invalid_scores_and_totals(self):
        for name, total in [('', '2'), ('x', '0'), ('x', '-1'), ('x', '2.5')]:
            with self.assertRaises(ValueError):
                self.store.create(name, total)
        rid = self.store.create('x', 2)
        for score in ('3', '-1', 'a', '1.5'):
            with self.assertRaises(ValueError):
                self.store.update(rid, score, False)
        self.assertEqual(self.store.get(rid)['solved_items'], 0)

    def test_save_failure_preserves_memory_and_disk(self):
        rid = self.store.create('x', 2)
        before = self.path.read_bytes()
        with patch('Tools.workspace_store.os.replace', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                self.store.update(rid, 1, True)
        self.assertFalse(self.store.get(rid)['is_running'])
        self.assertEqual(self.path.read_bytes(), before)

    def test_group_roundtrip_and_delete(self):
        tools = [{'name': 'ROT', 'page': 'Data Hashing', 'sub': 'ROT', 'color': 'blue'}]
        group = make_group(' Decode ', tools)
        save_records(self.path, [group])
        self.assertEqual(load_records(self.path)[0]['name'], 'Decode')
        self.assertEqual(load_records(self.path)[0]['tools'], tools)
        with self.assertRaises(ValueError):
            make_group('name', [])
        rid = self.store.create('x', 3)
        self.store.delete(rid)
        self.assertEqual(ChallengeStore(self.path).rows, [])

    def test_bad_json_is_not_replaced(self):
        self.path.write_text('{broken')
        with self.assertRaises(ValueError):
            ChallengeStore(self.path)
        self.assertEqual(self.path.read_text(), '{broken')


if __name__ == '__main__':
    unittest.main()
