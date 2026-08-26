#!/bin/bash
# Launch this worktree's BtStudio overlay on the primary checkout's binary.
# Python-only worktrees do not configure/build (OVERVIEW.md §10).
#
# Direct exec (not `pixi run`): pixi re-applies UF_HIDDEN on Qt plugins during
# env validation, which makes Qt miss libqcocoa.dylib and die with
# 'Could not find the Qt platform plugin "cocoa" in ""'.
# The binary rpath already points at the primary pixi env.
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

# Empty/wrong QT_PLUGIN_PATH is exactly the `in ""` search path. Let Qt
# resolve plugins from libQt6Core via rpath.
unset QT_PLUGIN_PATH QT_QPA_PLATFORM_PLUGIN_PATH || true

PLUGINS="$PIXI_ROOT/.pixi/envs/default/lib/qt6/plugins"
COCOA="$PLUGINS/platforms/libqcocoa.dylib"
if [ -d "$PLUGINS" ]; then
  chflags -R nohidden "$PLUGINS"
fi
if [ ! -f "$COCOA" ]; then
  echo "Qt cocoa plugin missing at $COCOA" >&2
  exit 1
fi
if ls -lO "$COCOA" | grep -q hidden; then
  echo "Qt cocoa plugin is still UF_HIDDEN at $COCOA" >&2
  echo "Run: chflags -R nohidden $PLUGINS" >&2
  exit 1
fi

echo "Using binary: $BIN"
echo "Loading overlay: $OVERLAY"
exec "$BIN" -M "$OVERLAY" "$@"
