#!/bin/bash
# Launch this worktree's BtStudio overlay on the primary checkout's binary.
# Python-only worktrees do not configure/build (OVERVIEW.md §10).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAIN="/Users/brucetokar/Documents/GitHub/FreeCAD_BT"
BIN="$MAIN/build/release/bin/FreeCAD"
PIXI_ROOT="$MAIN"

if [ ! -x "$BIN" ]; then
  BIN="$ROOT/build/release/bin/FreeCAD"
  PIXI_ROOT="$ROOT"
fi
if [ ! -x "$BIN" ]; then
  echo "No FreeCAD binary at $MAIN/build/release/bin/FreeCAD" >&2
  echo "This worktree is Python-only — build once in the primary checkout, then rerun." >&2
  exit 1
fi

OVERLAY="$ROOT/src/Mod/BtStudio"
if [ ! -d "$OVERLAY" ]; then
  echo "BtStudio overlay missing at $OVERLAY" >&2
  exit 1
fi

PLUGINS="$PIXI_ROOT/.pixi/envs/default/lib/qt6/plugins"
if [ -d "$PLUGINS" ]; then
  chflags -R nohidden "$PLUGINS" 2>/dev/null || true
fi

echo "Using binary: $BIN"
echo "Loading overlay: $OVERLAY"
cd "$PIXI_ROOT"
exec pixi run -- bash -c '
  set -euo pipefail
  plugins="${CONDA_PREFIX}/lib/qt6/plugins"
  if [ -d "$plugins" ]; then
    chflags -R nohidden "$plugins" 2>/dev/null || true
  fi
  exec "$1" -M "$2" "${@:3}"
' bash "$BIN" "$OVERLAY" "$@"
