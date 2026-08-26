#!/bin/bash
# Launch this worktree's BtStudio + FcBridge on the primary checkout's binary.
# Direct exec: pixi run re-hides Qt cocoa plugins (see run-freecad.sh).
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
  exit 1
fi

unset QT_PLUGIN_PATH QT_QPA_PLATFORM_PLUGIN_PATH || true
PLUGINS="$PIXI_ROOT/.pixi/envs/default/lib/qt6/plugins"
[ -d "$PLUGINS" ] && chflags -R nohidden "$PLUGINS"

export FCBRIDGE_TOKEN="${FCBRIDGE_TOKEN:-$(openssl rand -hex 16 2>/dev/null || echo dev-token)}"
export FCBRIDGE_DIR="$ROOT/src/Mod/FcBridge"
export FCBRIDGE_PORT="${FCBRIDGE_PORT:-9876}"

echo "FcBridge enabled on 127.0.0.1:${FCBRIDGE_PORT} (token set)."
echo "Using binary: $BIN"
exec "$BIN" -M "$ROOT/src/Mod/FcBridge" -M "$ROOT/src/Mod/BtStudio" "$@"
