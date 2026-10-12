#!/bin/sh
set -eu
# Optional shortcut helper for an already-extracted bundle. It never copies
# application files or changes UNIT's data directory.
exec "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/UNIT" --install-shortcut "$@"
