#!/bin/bash
# Build (if needed) and run the FreeCAD_BT development GUI.
# Must be executed from the FreeCAD_BT repo root.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [ ! -f build/release/bin/FreeCAD ]; then
  echo "No binary found — configuring and building first (this takes a while)..."
  pixi run cmake -S . -B build/release \
    -DCMAKE_OSX_SYSROOT=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk \
    -DCMAKE_CXX_FLAGS="-Wno-elaborated-enum-base -Wno-availability -Wno-nullability-extension" \
    -DFREECAD_3DCONNEXION_SUPPORT=None
  pixi run ninja -C build/release -j 12
fi

# Pixi/rattler marks extracted dylibs UF_HIDDEN on this Mac. Qt's plugin
# scanner uses QDir::Files without Hidden, so it cannot see libqcocoa.dylib
# and the GUI dies with "Could not find the Qt platform plugin cocoa".
# pixi re-applies the flag whenever it re-extracts the env, so clear it on
# every launch. This is the decisive fix; do NOT also set QT_PLUGIN_PATH /
# QT_QPA_PLATFORM_PLUGIN_PATH — Qt resolves the plugins relative to
# libQt6Core on its own, and those overrides can re-trigger the same failure.
PLUGINS="$ROOT/.pixi/envs/default/lib/qt6/plugins"
if [ -d "$PLUGINS" ]; then
  chflags -R nohidden "$PLUGINS" 2>/dev/null || true
fi

exec pixi run ./build/release/bin/FreeCAD "$@"
