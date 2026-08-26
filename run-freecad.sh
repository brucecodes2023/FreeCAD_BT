#!/bin/bash
# Build (if needed) and run FreeCAD with this tree's BtStudio overlay.
# Worktrees reuse the primary checkout's binary (OVERVIEW.md §10).
#
# Direct exec (not `pixi run`): pixi re-applies UF_HIDDEN on Qt plugins during
# env validation, which makes Qt miss libqcocoa.dylib and die with
# 'Could not find the Qt platform plugin "cocoa" in ""'.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRIMARY="$(cd "$ROOT/.." && pwd)/FreeCAD_BT"
OVERLAY="$ROOT/src/Mod/BtStudio"

if [ ! -d "$OVERLAY" ]; then
  echo "BtStudio overlay missing at $OVERLAY" >&2
  exit 1
fi

if [ -x "$ROOT/build/release/bin/FreeCAD" ]; then
  BIN="$ROOT/build/release/bin/FreeCAD"
  PIXI_ROOT="$ROOT"
elif [ -x "$PRIMARY/build/release/bin/FreeCAD" ]; then
  BIN="$PRIMARY/build/release/bin/FreeCAD"
  PIXI_ROOT="$PRIMARY"
elif [ -f "$ROOT/pixi.toml" ]; then
  echo "No binary found — configuring and building first (this takes a while)..."
  cd "$ROOT"
  pixi run cmake -S . -B build/release \
    -DCMAKE_OSX_SYSROOT=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk \
    -DCMAKE_CXX_FLAGS="-Wno-elaborated-enum-base -Wno-availability -Wno-nullability-extension" \
    -DFREECAD_3DCONNEXION_SUPPORT=None
  pixi run ninja -C build/release -j 12
  BIN="$ROOT/build/release/bin/FreeCAD"
  PIXI_ROOT="$ROOT"
else
  echo "No FreeCAD binary at $PRIMARY/build/release/bin/FreeCAD" >&2
  echo "This worktree is Python-only — build once in the primary checkout, then rerun." >&2
  exit 1
fi

unset QT_PLUGIN_PATH QT_QPA_PLATFORM_PLUGIN_PATH || true

PLUGINS="$PIXI_ROOT/.pixi/envs/default/lib/qt6/plugins"
COCOA="$PLUGINS/platforms/libqcocoa.dylib"
if [ -d "$PLUGINS" ]; then
  chflags -R nohidden "$PLUGINS"
fi
if [ -f "$COCOA" ] && ls -lO "$COCOA" | grep -q hidden; then
  echo "Qt cocoa plugin is still UF_HIDDEN at $COCOA" >&2
  echo "Run: chflags -R nohidden $PLUGINS" >&2
  exit 1
fi

echo "Using binary: $BIN"
echo "Loading overlay: $OVERLAY"
exec "$BIN" -M "$OVERLAY" "$@"
