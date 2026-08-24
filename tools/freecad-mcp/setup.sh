#!/bin/bash
# Create the FcBridge MCP bridge venv (Python >=3.10) and install it.
# Run once per checkout: `tools/freecad-mcp/setup.sh`
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Prefer the repo's pixi Python (3.11); else a system python3.10+.
PY="${PYTHON:-}"
if [ -z "$PY" ]; then
  PIXI_PY="$DIR/../../.pixi/envs/default/bin/python3.11"
  if [ -x "$PIXI_PY" ]; then PY="$PIXI_PY"; else PY="python3"; fi
fi

echo "Using Python: $("$PY" --version 2>&1) ($PY)"
"$PY" -m venv "$DIR/.venv"
"$DIR/.venv/bin/python" -m pip install -q --upgrade pip
"$DIR/.venv/bin/python" -m pip install -q "$DIR"
echo "FcBridge MCP bridge installed in $DIR/.venv"
echo "Bridge command: $DIR/.venv/bin/freecad-mcp-agent"
