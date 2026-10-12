"""Keep app-owned runtime messages English without changing user content."""
import ast
import os
from pathlib import Path
import re
import unittest
from unittest.mock import patch

from tests import test_history_gui as fixtures

ROOT = Path(__file__).resolve().parents[1]


class EnglishSourceTests(unittest.TestCase):
    def test_runtime_strings_have_no_thai(self):
        paths = [ROOT / 'app.py', ROOT / 'sidebar.py']
        for folder in ('pages', 'Tools', 'Pipeline', 'Decode', 'Encode', 'Hashing'):
            paths.extend((ROOT / folder).glob('*.py'))
        failures = []
        for path in paths:
            if path.name == 'package_smoke.py':
                continue  # Intentional Thai input/filename fixtures, not UI copy.
            tree = ast.parse(path.read_text(encoding='utf-8'))
            docstrings = set()
            for node in ast.walk(tree):
                if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.body and isinstance(node.body[0], ast.Expr):
                        docstrings.add(id(node.body[0].value))
            for node in ast.walk(tree):
                if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                        and id(node) not in docstrings and re.search('[\u0e00-\u0e7f]', node.value)):
                    failures.append(f'{path.relative_to(ROOT)}:{node.lineno}: {node.value}')
        self.assertEqual(failures, [])


@unittest.skipUnless(os.environ.get('DISPLAY'), 'Needs X display')
class EnglishGuiTests(unittest.TestCase):
    setUp = fixtures.HistoryGuiTests.setUp
    close_root = fixtures.HistoryGuiTests.close_root

    def test_icon_and_disconnected_gemini_warning(self):
        from Tools.app_icon import ICON_PATH
        self.assertTrue(ICON_PATH.is_file())
        self.assertEqual(len(self.root._unit_icons), 3)
        self.assertTrue(all(0 < icon.width() <= 140 for icon in self.root._unit_icons))
        self.root.switch_page('Gemini CLI')
        page = self.root.pages['Gemini CLI']
        page.cli_ready = False
        page.input_field.insert(0, 'test')
        with patch('pages.gemini.threading.Thread') as worker:
            page.send_message()
        worker.assert_not_called()
        text = page.chat_display.get('1.0', 'end')
        self.assertIn('Please connect to Gemini CLI first', text)
        self.assertNotRegex(text, '[\u0e00-\u0e7f]')
        self.assertFalse(self.errors)
