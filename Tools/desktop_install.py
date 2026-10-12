"""Opt-in user-menu shortcut for the current extracted bundle; never use sudo."""
import os
from pathlib import Path
import sys
from Tools.app_paths import data_root
from Tools.app_icon import ICON_PATH


def value(text):
    text = str(text)
    if any(c in text for c in '\r\n\x00'):
        raise ValueError('Unsupported control character in shortcut path')
    return text.replace('\\', '\\\\').replace('\t', '\\t')


def executable_value(path):
    text = str(path)
    if '=' in text:
        raise ValueError('Desktop executable paths cannot contain an equals sign')
    # Exec quoting, followed by desktop-entry string escaping (two layers).
    quoted = ''.join('\\'+c if c in '\\"`$' else c for c in text)
    return '"' + value(quoted.replace('%', '%%')) + '"'


def install(executable, icon, applications, working_directory):
    executable, icon = Path(executable).resolve(), Path(icon).resolve()
    if not executable.is_file() or not icon.is_file():
        raise ValueError('Extract the entire UNIT folder before installing the shortcut')
    content = ('[Desktop Entry]\nType=Application\nVersion=1.0\nName=UNIT\n'
               'Comment=Unified security and CTF toolkit\n'
               f'Exec={executable_value(executable)}\nIcon={value(icon)}\n'
               f'Path={value(working_directory)}\nTerminal=false\nCategories=Utility;Development;\n')
    target = Path(applications) / 'unit-toolkit.desktop'
    if target.exists() or target.is_symlink():
        if not target.is_symlink() and target.read_text(encoding='utf-8') == content:
            return target
        raise FileExistsError(f'Shortcut already exists: {target}. Keep it, or remove it explicitly before installing a different build.')
    Path(working_directory).mkdir(parents=True, exist_ok=True, mode=0o700)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('x', encoding='utf-8') as stream:
        stream.write(content)
    return target


def main():
    if not getattr(sys, 'frozen', False):
        raise RuntimeError('Use --install-shortcut from the built UNIT executable')
    base = Path(os.environ.get('XDG_DATA_HOME', '')).expanduser()
    if not base.is_absolute():
        base = Path.home() / '.local/share'
    path = install(sys.executable, ICON_PATH, base/'applications', data_root()/'workspace')
    print(f'Shortcut created: {path}\nKeep the extracted UNIT folder in this location.')
    return 0
