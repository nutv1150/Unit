#!/bin/bash
set -eu
unit_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
if ! command -v python3 >/dev/null 2>&1; then
    echo 'Python 3 is required. On Kali: sudo apt install python3'
    read -r -p 'Press Enter to close. ' || true
    exit 1
fi
if [ -f "$unit_dir/packaging/install_dependencies.py" ]; then
    unit_installer="$unit_dir/packaging/install_dependencies.py"
else
    unit_installer="$unit_dir/install_dependencies.py"
fi
unit_status=0
python3 "$unit_installer" "$@" || unit_status=$?
if [ -t 0 ] && [ "$#" -eq 0 ]; then
    read -r -p 'Press Enter to close. ' || true
fi
exit "$unit_status"
