#!/bin/bash
# Launch the FreeCAD_BT dev GUI with the FcBridge verification server enabled,
# so the AI verification MCP can drive it (see OVERVIEW.md §9, src/Mod/FcBridge).
#
# Uses DIRECT exec (not `pixi run`): pixi intermittently re-applies the macOS
# UF_HIDDEN flag to the Qt plugins on env re-validation, causing the "cocoa"
# launch failure. Clearing the flag then exec'ing the binary directly (its
# rpath is absolute) is reliable.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [ ! -x build/release/bin/FreeCAD ]; then
  echo "No binary at build/release/bin/FreeCAD — build first (see run-freecad.sh)." >&2
  exit 1
fi

# Clear the UF_HIDDEN flag pixi puts on the Qt plugins (else: cocoa not found).
PLUGINS="$ROOT/.pixi/envs/default/lib/qt6/plugins"
[ -d "$PLUGINS" ] && chflags -R nohidden "$PLUGINS" 2>/dev/null || true

# FcBridge gating: the server only starts when FCBRIDGE_TOKEN is set.
export FCBRIDGE_TOKEN="${FCBRIDGE_TOKEN:-$(openssl rand -hex 16 2>/dev/null || echo dev-token)}"
export FCBRIDGE_DIR="$ROOT/src/Mod/FcBridge"
export FCBRIDGE_PORT="${FCBRIDGE_PORT:-9876}"

echo "FcBridge enabled on 127.0.0.1:${FCBRIDGE_PORT} (token set)."
# -M loads the in-tree module directly (no copy/rebuild).
exec ./build/release/bin/FreeCAD -M "$ROOT/src/Mod/FcBridge" "$@"
