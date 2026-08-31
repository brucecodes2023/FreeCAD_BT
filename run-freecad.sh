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

unset QT_PLUGIN_PATH QT_QPA_PLATFORM_PLUGIN_PATH QT_QPA_PLATFORM || true

# pixi/rattler marks Qt plugin dylibs UF_HIDDEN. Qt's QDir scan skips Hidden
# files, so only the built-in "offscreen" plugin is visible and the GUI aborts.
# `ls | grep hidden` is the wrong test (Darwin flag column vs xattrs). Use st_flags.
unhide_qt_plugins() {
  local dir="$1"
  [ -d "$dir" ] || return 0
  chflags -R nohidden "$dir" 2>/dev/null || true
  # -R can skip already-hidden files on some Darwin builds; hit cocoa directly.
  local cocoa="$dir/platforms/libqcocoa.dylib"
  [ -f "$cocoa" ] && chflags nohidden "$cocoa" 2>/dev/null || true
}

plugin_is_hidden() {
  local f="$1"
  [ -f "$f" ] || return 1
  local flags
  flags="$(stat -f '%f' "$f" 2>/dev/null || echo 0)"
  # UF_HIDDEN = 0x8000 = 32768
  [ $((flags & 32768)) -ne 0 ]
}

PLUGINS="$PIXI_ROOT/.pixi/envs/default/lib/qt6/plugins"
COCOA="$PLUGINS/platforms/libqcocoa.dylib"
unhide_qt_plugins "$PLUGINS"
if plugin_is_hidden "$COCOA"; then
  echo "Qt cocoa plugin is still UF_HIDDEN at $COCOA" >&2
  echo "Run: chflags nohidden \"$COCOA\"" >&2
  exit 1
fi
if [ ! -f "$COCOA" ]; then
  echo "Qt cocoa plugin missing at $COCOA" >&2
  echo "pixi env may be incomplete. Try: pixi install" >&2
  exit 1
fi

echo "Using binary: $BIN"
echo "Loading overlay: $OVERLAY"
exec "$BIN" -M "$OVERLAY" "$@"
