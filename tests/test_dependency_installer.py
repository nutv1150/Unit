import importlib.util
import json
from pathlib import Path
import shlex
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('unit_installer', ROOT/'packaging/install_dependencies.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class DependencyInstallerTests(unittest.TestCase):
    def test_default_pipeline_commands_covered(self):
        data = json.loads((ROOT/'packaging/defaults/Pipeline/custom_tools.json').read_text())
        commands = {shlex.split(t['command'])[0] for group in data.values() for t in group}
        provided = {c for group in installer.CORE.values() for c in group} | {'zsteg'}
        self.assertFalse(commands - provided)

    def test_plan_does_not_execute_or_prompt(self):
        with patch.object(installer, 'run') as run, patch('builtins.input') as prompt:
            self.assertEqual(installer.main(['--plan']), 0)
            run.assert_not_called(); prompt.assert_not_called()

    def test_check_reports_missing_without_installing(self):
        with patch.object(installer.shutil, 'which', return_value=None), patch.object(installer, 'run') as run:
            self.assertEqual(installer.main(['--check']), 1)
            run.assert_not_called()

    def test_check_success(self):
        with patch.object(installer.shutil, 'which', return_value='/usr/bin/tool'):
            self.assertEqual(installer.main(['--check']), 0)

    def test_root_rejected_before_apt(self):
        with patch.object(installer.os, 'geteuid', return_value=0), patch.object(installer.shutil, 'which', return_value='/usr/bin/apt-get'), patch.object(installer, 'run') as run:
            self.assertEqual(installer.main([]), 2)
            run.assert_not_called()

    def test_desktop_command_handles_spaces_and_uri(self):
        line = next(s for s in (ROOT/'Install UNIT Dependencies.desktop').read_text().splitlines() if s.startswith('Exec='))
        argv = shlex.split(line[5:])
        for path in ['/tmp/UNIT test/Install UNIT Dependencies.desktop', 'file:///tmp/UNIT%20test/Install%20UNIT%20Dependencies.desktop']:
            with patch('sys.argv', ['-c', path]), patch('os.execv') as call:
                exec(compile(argv[2], '<desktop>', 'exec'), {})
                call.assert_called_once_with('/bin/bash', ['bash','/tmp/UNIT test/install_dependencies.sh'])


if __name__ == '__main__':
    unittest.main()
