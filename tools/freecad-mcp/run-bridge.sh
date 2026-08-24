#!/bin/bash
# Launch the FcBridge stdio MCP server (spawned by Claude Code via .mcp.json).
# Self-locating: finds its own venv regardless of the caller's cwd.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -x "$DIR/.venv/bin/freecad-mcp-agent" ]; then
  echo "FcBridge MCP venv missing — run tools/freecad-mcp/setup.sh first" >&2
  exit 1
fi
exec "$DIR/.venv/bin/freecad-mcp-agent"
