"""Extract and exercise a locally built release in an isolated temporary folder."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile


def main():
    archive = Path(sys.argv[1]).resolve()
    with tempfile.TemporaryDirectory(prefix='unit-release-check-') as directory:
        work = Path(directory)
        with tarfile.open(archive) as tar:
            names = tar.getnames()
            assert not any(name.endswith(('.sqlite3', '.iso', '.docx', '.env')) for name in names)
            assert not any('/writeups/' in name or '/dashboard_state.json' in name for name in names)
            tar.extractall(work, filter='data')
        folder = next(path for path in work.iterdir() if path.is_dir())
        executable = folder/'UNIT'
        assert executable.is_file() and (folder/'_internal').is_dir()
        for name in ('install_dependencies.sh', 'install_dependencies.py', 'Install UNIT Dependencies.desktop'):
            assert (folder/name).is_file(), f'Missing installer: {name}'
        subprocess.run(['bash', '-n', str(folder/'install_dependencies.sh')], check=True)
        subprocess.run(['bash', str(folder/'install_dependencies.sh'), '--plan'], cwd=work,
                       check=True, capture_output=True, text=True, timeout=10)
        defaults = folder/'_internal/defaults'
        assert json.loads((defaults/'Pipeline/saved_pipelines.json').read_text()) == {'saved_pipelines':[]}
        assert json.loads((defaults/'custom_tools.json').read_text()) == []
        env = dict(os.environ, UNIT_DATA_HOME=str(work/'profile'), XDG_DATA_HOME=str(work/'xdg'),
                   PYTHONPATH='', PYTHONHOME='')
        # Launch outside the checkout without depending on its virtualenv.
        checked = subprocess.run([str(executable), '--check-tools'], cwd=work, env=env,
                                 capture_output=True, text=True, check=True, timeout=10)
        assert 'UNIT — SYSTEM CHECK' in checked.stdout
        assert not (work/'profile').exists(), 'Read-only tool check wrote a profile'
        subprocess.run([str(folder/'install-user.sh')], cwd=work, env=env, check=True, timeout=10)
        shortcut = work/'xdg/applications/unit-toolkit.desktop'
        assert shortcut.exists() and str(executable) in shortcut.read_text()
        result = subprocess.run(['xvfb-run','-a',str(executable),'--smoke-test'], cwd=work, env=env,
                                capture_output=True, text=True, timeout=45)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        assert '"result": "PASS"' in result.stdout
        assert not (work/'profile/data').exists(), 'Smoke test touched the caller profile'
        print('PASS: archive privacy, extraction, relocated executable, shortcut, isolated packaged GUI smoke')


if __name__ == '__main__':
    main()
