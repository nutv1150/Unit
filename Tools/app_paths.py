"""Read-only bundle resources and writable per-user packaged-app data.

Source checkouts retain their existing paths unless UNIT_DATA_HOME is supplied.
No automatic migration of personal evidence or credentials is performed.
"""
import os
from pathlib import Path
import sys
import tempfile

RESOURCE_ROOT = Path(__file__).resolve().parents[1]


def uses_user_data():
    return bool(getattr(sys, 'frozen', False) or os.environ.get('UNIT_DATA_HOME'))


def data_root():
    override = os.environ.get('UNIT_DATA_HOME')
    if override:
        path = Path(override).expanduser()
        if not path.is_absolute():
            raise ValueError('UNIT_DATA_HOME must be an absolute path')
        return path
    if getattr(sys, 'frozen', False):
        base = Path(os.environ.get('XDG_DATA_HOME', '')).expanduser()
        if not base.is_absolute():
            base = Path.home() / '.local' / 'share'
        return base / 'unit'
    return RESOURCE_ROOT


def writable_path(relative):
    return data_root() / relative


def initialize_user_data():
    """Publish clean defaults once, never overwrite an existing user file."""
    if not uses_user_data():
        return
    root = data_root()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    defaults = RESOURCE_ROOT / ('defaults' if getattr(sys, 'frozen', False) else 'packaging/defaults')
    for relative in ('Pipeline/custom_tools.json', 'Pipeline/saved_pipelines.json', 'custom_tools.json'):
        target = root / relative
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        contents = (defaults / relative).read_bytes()
        # Hard-link publication is atomic and fails if another instance won.
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.unit-default-', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(contents)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            try:
                os.link(temporary, target)
            except FileExistsError:
                pass
        finally:
            temporary.unlink()


def external_environment(env=None):
    """Do not inject bundled Linux libraries into system CLI tools."""
    result = dict(os.environ if env is None else env)
    if getattr(sys, 'frozen', False) and sys.platform.startswith('linux'):
        original = result.get('LD_LIBRARY_PATH_ORIG')
        if original is None:
            result.pop('LD_LIBRARY_PATH', None)
        else:
            result['LD_LIBRARY_PATH'] = original
    return result
