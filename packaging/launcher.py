"""UNIT Linux entry point.

The command-line workers are dispatched before importing the GUI.  This keeps
the regex worker usable in a headless process and avoids importing Tk on CI.
"""
from __future__ import annotations

import sys
from pathlib import Path


def _project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    root = _project_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    if args and args[0] == "--unit-regex-worker":
        from Tools.regex_runner import main as worker_main
        return int(worker_main() or 0)
    if args and args[0] == "--check-tools":
        from Tools.system_check import main as check_main
        return int(check_main() or 0)
    if args and args[0] == "--smoke-test":
        from Tools.package_smoke import main as smoke_main
        return int(smoke_main() or 0)
    if args and args[0] == "--install-shortcut":
        from Tools.desktop_install import main as install_main
        return int(install_main() or 0)
    if args and args[0] in {"-h", "--help"}:
        print("Usage: UNIT [--check-tools|--smoke-test|--install-shortcut|--unit-regex-worker]")
        return 0
    if args:
        print(f"Unknown argument: {args[0]}", file=sys.stderr)
        return 2

    if getattr(sys, 'frozen', False):
        import os
        from Tools.app_paths import data_root
        work = data_root() / 'workspace'
        work.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chdir(work)
    from app import UNITApp
    app = UNITApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
