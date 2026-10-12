"""Read-only optional tool discovery. Never run or install a discovered tool."""
import json
import shlex
import shutil
from pathlib import Path
from Tools.app_paths import RESOURCE_ROOT, writable_path


def report():
    path = writable_path('Pipeline/custom_tools.json')
    if not path.exists():
        path = RESOURCE_ROOT / 'defaults/Pipeline/custom_tools.json'
    if not path.exists():
        path = RESOURCE_ROOT / 'packaging/defaults/Pipeline/custom_tools.json'
    required = {'file', 'exiftool', 'zsteg', 'gemini', 'node', 'x-terminal-emulator',
                'bash', 'wireshark', 'ghidra', 'nmap', 'hashcat', 'burpsuite', 'msfconsole'}
    problems = []
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        from Pipeline.pipeline_engine import PipelineEngine
        PipelineEngine.validate_tools(data)
        for rows in data.values():
            for tool in rows:
                required.add(shlex.split(tool['command'])[0])
    except (OSError, ValueError, TypeError, KeyError, IndexError) as error:
        problems.append(f'Cannot inspect Pipeline configuration: {error}')
    lines = ['UNIT — SYSTEM CHECK', '',
             'Local codec/hash tools are included. External tools below are optional.',
             'FOUND means executable is on PATH, not that all features/version/auth work.',
             'Missing tools affect only the operations that use them. Nothing is installed.', '']
    for command in sorted(required):
        location = shutil.which(command)
        lines.append(f'{"FOUND  " if location else "MISSING"}  {command}' + (f'  {location}' if location else ''))
    lines.extend(['', f'User data: {writable_path(".")}', *problems])
    return '\n'.join(lines)


def main():
    print(report())
    return 0


def open_window(parent):
    import customtkinter as ctk
    from Tools.text_view import background
    from Tools.window_layout import fit_window
    win = ctk.CTkToplevel(parent)
    win.title('UNIT — System Check')
    fit_window(win, '1000x700')
    box = ctk.CTkTextbox(win, wrap='none')
    box.pack(fill='both', expand=True, padx=15, pady=15)
    def refresh():
        button.configure(state='disabled')
        def done(value, error):
            box.configure(state='normal')
            box.delete('1.0', 'end')
            box.insert('1.0', str(error) if error else value)
            box.configure(state='disabled')
            button.configure(state='normal')
        background(win, report, done)
    button = ctk.CTkButton(win, text='Refresh', command=refresh)
    button.pack(pady=(0, 15))
    refresh()
    return win
