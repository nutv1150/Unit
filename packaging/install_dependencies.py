"""Interactive Kali dependency installer. --check/--plan never install anything.

Only fixed package names are installed; custom tool commands are never executed.
Python dependencies are needed for source checkout only, not the frozen bundle.
"""
import argparse
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

CORE = {
    'coreutils': ['base32', 'base64', 'cut', 'dd', 'md5sum', 'sort', 'tr', 'uniq'],
    'binutils': ['strings', 'objdump'], 'bsdextrautils': ['hexdump'],
    'util-linux': ['rev'], 'gawk': ['awk'], 'grep': ['grep'], 'bash': ['bash'],
    'xxd': ['xxd'], '7zip': ['7z'], 'unzip': ['unzip'], 'tar': ['tar'],
    'gzip': ['gzip'], 'openssl': ['openssl'], 'python3': ['python3'],
    'file': ['file'], 'libimage-exiftool-perl': ['exiftool'],
    'binwalk': ['binwalk'], 'steghide': ['steghide'], 'foremost': ['foremost'],
    'zbar-tools': ['zbarimg'], 'checksec': ['checksec'], 'apktool': ['apktool'],
    'jadx': ['jadx'], 'tcpdump': ['tcpdump'], 'tshark': ['tshark'],
    'xterm': ['x-terminal-emulator'],
}
PORTAL = {'wireshark': ['wireshark'], 'burpsuite': ['burpsuite'],
          'ghidra': ['ghidra'], 'nmap': ['nmap'], 'hashcat': ['hashcat'],
          'metasploit-framework': ['msfconsole'], 'firefox-esr': ['firefox']}

def run(args, capture=False):
    print('+ ' + shlex.join(map(str, args)), flush=True)
    return subprocess.run(list(map(str, args)), text=True, check=False,
                          stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.PIPE if capture else None)

def ask(message):
    return input(message + ' [y/N] ').strip().lower() in ('y', 'yes')

def report(commands):
    missing = []
    for cmd in sorted(set(commands)):
        found = shutil.which(cmd)
        print(f'{"FOUND" if found else "MISSING":7} {cmd}' + (f'  {found}' if found else ''))
        if not found: missing.append(cmd)
    return missing

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Read-only executable discovery')
    parser.add_argument('--plan', action='store_true', help='Show packages only; no network or writes')
    parser.add_argument('--core-only', action='store_true', help='Exclude large App Portal applications')
    args = parser.parse_args(argv)
    packages = dict(CORE)
    if not args.core_only: packages.update(PORTAL)
    commands = [c for group in packages.values() for c in group] + ['zsteg', 'node', 'gemini']
    if args.check:
        return 1 if report(commands) else 0
    print('UNIT dependency installer — Kali Linux')
    print('APT tools: ' + ', '.join(packages))
    print('Optional: zsteg (RubyGems), Gemini CLI (npm, Node.js >=20).')
    print('Source checkout only: Python packages from Requirements.txt in .venv.')
    print('App Portal tools can require several GB. Use --core-only to exclude them.')
    print('No custom tools, personal data, credentials, or system Python are modified.')
    if args.plan: return 0
    if sys.platform != 'linux' or not shutil.which('apt-get'):
        print('Unsupported system: this installer requires Kali Linux and apt-get.'); return 2
    if os.geteuid() == 0:
        print('Run as your normal desktop user, NOT with sudo. Only APT uses sudo.'); return 2
    if not sys.stdin.isatty():
        print('Open in a terminal; interactive confirmation is required.'); return 2
    if not shutil.which('sudo'):
        print('sudo is unavailable; ask your administrator to install system packages.'); return 2
    if 'ID=kali' not in Path('/etc/os-release').read_text():
        print('This distribution is not Kali; package names may not be available.')
        if not ask('Continue on this APT-based distribution?'): return 2
    if not ask('Install missing tools from the listed APT packages?'): return 0
    failures = []
    if run(['sudo', 'apt-get', 'update']).returncode:
        print('Package index update failed. Check connectivity/repositories and retry.'); return 1
    for pkg, cmds in packages.items():
        if all(shutil.which(c) for c in cmds): continue
        # Keep APT confirmation: do not auto-accept removals, upgrades or capture privileges.
        if run(['sudo', 'apt-get', 'install', pkg]).returncode: failures.append(pkg)

    local = Path.home()/'.local'
    if not shutil.which('zsteg') and ask('Install zsteg from RubyGems for this user?'):
        if run(['sudo', 'apt-get', 'install', 'ruby', 'ruby-dev', 'build-essential', 'zlib1g-dev']).returncode:
            failures.append('zsteg prerequisites')
        elif run(['gem', 'install', '--user-install', '--no-document', 'zsteg']).returncode:
            failures.append('zsteg')
        else:
            result = run(['ruby', '-e', "require 'rubygems'; puts Gem.user_dir"], capture=True)
            if result.returncode == 0:
                bindir = Path(result.stdout.strip())/'bin'
                link = local/'bin/zsteg';link.parent.mkdir(parents=True, exist_ok=True)
                if not os.path.lexists(link) and (bindir/'zsteg').exists():link.symlink_to(bindir/'zsteg')
                os.environ['PATH'] = str(local/'bin')+os.pathsep+os.environ.get('PATH','')
            else: failures.append('zsteg PATH setup')
    if not shutil.which('gemini') and ask('Install Gemini CLI from npm for this user?'):
        if run(['sudo', 'apt-get', 'install', 'nodejs', 'npm']).returncode:
            failures.append('Gemini prerequisites')
        else:
            check = run(['node', '-e', 'process.exit(Number(process.versions.node.split(".")[0])>=20?0:1)'])
            if check.returncode:
                failures.append('Gemini needs Node.js >=20; update Node using your administrator')
            elif run(['npm', 'install', '--global', '--prefix', local, '@google/gemini-cli']).returncode:
                failures.append('Gemini CLI')
            else:os.environ['PATH']=str(local/'bin')+os.pathsep+os.environ.get('PATH','')
    here = Path(__file__).resolve().parent
    root = here.parent if here.name == 'packaging' else here
    if (root/'app.py').is_file() and ask('Install source Python requirements into .venv?'):
        venv = root/'.venv'
        if run(['sudo', 'apt-get', 'install', 'python3-venv', 'python3-tk']).returncode:
            failures.append('Python prerequisites')
        elif venv.exists() and not (venv/'pyvenv.cfg').is_file():
            failures.append('Refusing to modify .venv: not a recognized virtual environment')
        else:
            created = True
            if not venv.exists():created = run(['python3', '-m', 'venv', venv]).returncode == 0
            if not created or run([venv/'bin/python', '-m', 'pip', 'install', '-r', root/'Requirements.txt']).returncode:
                failures.append('Python requirements')
            elif run([venv/'bin/python','-c','import tkinter,customtkinter,tkinterdnd2,puremagic']).returncode:
                failures.append('Python import check')
    print('\nFinal executable check (not a functional/version/authentication test):')
    missing = report(commands)
    print('Failed operations: ' + (', '.join(failures) or 'none'))
    print('Missing or skipped: ' + (', '.join(missing) or 'none'))
    print('For user-installed CLIs, ensure ~/.local/bin is on PATH; log out/in and restart UNIT.')
    print('Gemini authentication is manual: run gemini. No credentials are collected here.')
    return 1 if failures or missing else 0

if __name__ == '__main__':
    try: sys.exit(main())
    except (KeyboardInterrupt, EOFError):
        print('\nCancelled. Completed package operations are not rolled back.');sys.exit(130)
    except OSError as exc:
        print(f'Installation stopped: {exc}. Retry after correcting this error.');sys.exit(1)
