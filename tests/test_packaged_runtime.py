import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from Tools import app_paths


class PackagedRuntimeTests(unittest.TestCase):
    def test_source_paths_unchanged(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(sys, 'frozen', False, create=True):
            self.assertEqual(app_paths.data_root(), app_paths.RESOURCE_ROOT)

    def test_frozen_profile_and_relative_override_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {'XDG_DATA_HOME':directory}, clear=True), patch.object(sys, 'frozen', True, create=True):
                self.assertEqual(app_paths.data_root(), Path(directory)/'unit')
            with patch.dict(os.environ, {'UNIT_DATA_HOME':'relative'}, clear=True):
                with self.assertRaises(ValueError):
                    app_paths.data_root()

    def test_seed_is_clean_and_does_not_replace_user_file(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'UNIT_DATA_HOME':directory}):
            app_paths.initialize_user_data()
            saved = Path(directory)/'Pipeline/saved_pipelines.json'
            self.assertEqual(json.loads(saved.read_text()), {'saved_pipelines':[]})
            saved.write_text('keep invalid user file')
            app_paths.initialize_user_data()
            self.assertEqual(saved.read_text(), 'keep invalid user file')
            self.assertFalse((Path(directory)/'data/solve_history.sqlite3').exists())

    def test_external_environment_does_not_mutate_parent(self):
        env = {'LD_LIBRARY_PATH':'/bundled', 'LD_LIBRARY_PATH_ORIG':'/system', 'TOKEN':'not-printed'}
        with patch.object(sys, 'frozen', True, create=True), patch.object(sys, 'platform', 'linux'):
            self.assertEqual(app_paths.external_environment(env)['LD_LIBRARY_PATH'], '/system')
            self.assertNotIn('LD_LIBRARY_PATH', app_paths.external_environment({'LD_LIBRARY_PATH':'/bundled'}))
        self.assertEqual(env['LD_LIBRARY_PATH'], '/bundled')

    def test_frozen_regex_dispatch_no_gui(self):
        from Tools.regex_runner import find_match_spans
        with patch.object(sys, 'frozen', True, create=True), patch('Tools.regex_runner.subprocess.run',
            return_value=subprocess.CompletedProcess([], 0, b'[[0, 1]]', b'')) as launch:
            self.assertEqual(find_match_spans('a','a'), [[0,1]])
            self.assertEqual(launch.call_args.args[0], [sys.executable, '--unit-regex-worker'])

    def test_system_check_does_not_launch_tools(self):
        from Tools.system_check import report
        with patch('Tools.system_check.shutil.which', return_value=None), patch('subprocess.Popen') as launch:
            self.assertIn('MISSING', report())
        launch.assert_not_called()

    def test_shortcut_is_explicit_and_never_overwrites(self):
        from Tools.desktop_install import install
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            exe = root / 'UNIT with spaces'
            icon = root / 'unit.svg'
            exe.touch()
            icon.touch()
            shortcut = install(exe, icon, root/'apps', root/'work')
            text = shortcut.read_text()
            self.assertIn(f'Exec="{exe}"', text)
            self.assertIn('Terminal=false', text)
            self.assertEqual(install(exe, icon, root/'apps', root/'work'), shortcut)
            shortcut.write_text('user shortcut')
            with self.assertRaises(FileExistsError):
                install(exe, icon, root/'apps', root/'work')
            self.assertEqual(shortcut.read_text(), 'user shortcut')
