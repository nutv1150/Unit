import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

try:
    from pages.app_portal import AppPortalPage
except ModuleNotFoundError as import_error:
    AppPortalPage = None


@unittest.skipIf(AppPortalPage is None, "CustomTkinter is not installed")
class PortalSafetyTests(unittest.TestCase):
    def test_launcher_failure_is_not_reported_as_success(self):
        page = AppPortalPage.__new__(AppPortalPage)
        page.status_label = Mock()
        page._record_activity = Mock()
        for code in (None, 0, 2):
            page._record_activity.reset_mock()
            page._finish_launch_check(Mock(poll=Mock(return_value=code)), 'Tool')
            if code == 2:
                self.assertEqual(page._record_activity.call_args.args[1], 'failed')
            else:
                page._record_activity.assert_not_called()
                self.assertIn('NOT VERIFIED', page.status_label.configure.call_args.kwargs['text'])

    def test_failed_atomic_replace_preserves_original(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'custom_tools.json'
            original = '[]'
            path.write_text(original, encoding='utf-8')
            page = AppPortalPage.__new__(AppPortalPage)
            page.custom_tools_file = str(path)
            page.custom_tools_read_only = False
            with patch('pages.app_portal.os.replace', side_effect=OSError('disk full')):
                with self.assertRaises(OSError):
                    page._persist_tools([{'name': 'new'}])
            self.assertEqual(path.read_text(encoding='utf-8'), original)
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_tool_schema_rejects_non_string_display_fields(self):
        self.assertFalse(AppPortalPage._valid_tool({"name": "x", "check": "x", "cmd": "x", "desc": [], "icon": "x"}))
        self.assertTrue(AppPortalPage._valid_tool({"name": "x", "check": "x", "cmd": "x", "desc": "", "icon": "x"}))

    def test_invalid_source_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "custom_tools.json"
            original = json.dumps({"not": "a list"})
            path.write_text(original, encoding="utf-8")
            page = AppPortalPage.__new__(AppPortalPage)
            page.custom_tools_file = str(path)
            page.custom_tools_read_only = False
            page.custom_tools_error = None
            self.assertEqual(page.load_custom_tools(), [])
            self.assertTrue(page.custom_tools_read_only)
            self.assertEqual(path.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
