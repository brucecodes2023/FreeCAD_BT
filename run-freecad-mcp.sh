#!/bin/bash
# Launch FreeCAD with this tree's BtStudio + FcBridge on the local or primary binary.
# Direct exec: pixi run re-hides Qt cocoa plugins (see run-freecad.sh).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRIMARY="$(cd "$ROOT/.." && pwd)/FreeCAD_BT"

if [ -x "$ROOT/build/release/bin/FreeCAD" ]; then
  BIN="$ROOT/build/release/bin/FreeCAD"
  PIXI_ROOT="$ROOT"
elif [ -x "$PRIMARY/build/release/bin/FreeCAD" ]; then
  BIN="$PRIMARY/build/release/bin/FreeCAD"
  PIXI_ROOT="$PRIMARY"
else
  echo "No FreeCAD binary — build first (see run-freecad.sh)." >&2
  exit 1
fi

unset QT_PLUGIN_PATH QT_QPA_PLATFORM_PLUGIN_PATH QT_QPA_PLATFORM || true
PLUGINS="$PIXI_ROOT/.pixi/envs/default/lib/qt6/plugins"
if [ -d "$PLUGINS" ]; then
  chflags -R nohidden "$PLUGINS" 2>/dev/null || true
  [ -f "$PLUGINS/platforms/libqcocoa.dylib" ] && chflags nohidden "$PLUGINS/platforms/libqcocoa.dylib" 2>/dev/null || true
fi

export FCBRIDGE_TOKEN="${FCBRIDGE_TOKEN:-$(openssl rand -hex 16 2>/dev/null || echo dev-token)}"
export FCBRIDGE_DIR="$ROOT/src/Mod/FcBridge"
export FCBRIDGE_PORT="${FCBRIDGE_PORT:-9876}"

echo "FcBridge enabled on 127.0.0.1:${FCBRIDGE_PORT} (token set)."
echo "Using binary: $BIN"
exec "$BIN" -M "$ROOT/src/Mod/FcBridge" -M "$ROOT/src/Mod/BtStudio" "$@"
