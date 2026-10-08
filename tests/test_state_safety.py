import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from Tools.dashboard_store import DashboardStore


class DashboardStateSafetyTests(unittest.TestCase):
    def test_missing_favorite_target_is_not_success(self):
        from pages.dashboard import DashboardPage
        page = DashboardPage.__new__(DashboardPage)
        page.app_root = Mock()
        page.app_root.pages = {'Pipeline': Mock()}
        pipeline = page.app_root.pages['Pipeline']
        pipeline.engine.file_tools = {}
        pipeline.engine.text_tools = {}
        pipeline.load_saved_pipeline_to_canvas.return_value = False
        page.persistence_notice = Mock()
        for target in ('page:Missing', 'pipeline_tool:Missing', 'pipeline_saved:Missing', 'portal:Missing'):
            with self.subTest(target=target):
                page.launch_favorite({'name': 'Missing', 'target': target})
                self.assertEqual(page.app_root.record_activity.call_args.kwargs['status'], 'failed')
        pipeline.add_tool_node.assert_not_called()

    def test_nested_invalid_data_is_not_silently_normalized(self):
        for data in ({"favorites": [{"name": " ", "target": "page:Pipeline"}]},
                     {"categories": [{}]}, {"events": [{"flags": [{}]}]},
                     {"events": [{"timestamp": []}]}, {"schema_version": 999}):
            with self.subTest(data=data), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "state.json"
                original = json.dumps(data)
                path.write_text(original, encoding="utf-8")
                store = DashboardStore(path)
                self.assertTrue(store.read_only)
                with self.assertRaises(OSError):
                    store.add_competition("Test")
                self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_invalid_schema_is_read_only_and_not_rewritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            original = json.dumps({"events": [{"tool": []}]})
            path.write_text(original, encoding="utf-8")
            store = DashboardStore(path)
            self.assertTrue(store.read_only)
            self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_failed_save_rolls_back_memory(self):
        with tempfile.TemporaryDirectory() as directory:
            store = DashboardStore(Path(directory) / "state.json")
            before = store.list_favorites()
            with patch.object(store, "_save", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    store.remove_favorite("page:Data Hashing")
            self.assertEqual(store.list_favorites(), before)


if __name__ == "__main__":
    unittest.main()
