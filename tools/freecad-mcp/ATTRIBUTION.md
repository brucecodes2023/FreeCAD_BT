# FcBridge MCP bridge — attribution & provenance

The **stdio MCP bridge** half of the FreeCAD verification MCP (see `OVERVIEW.md`
§9). Claude Code spawns it via the repo-root `.mcp.json`; it connects to the
in-FreeCAD **FcBridge** server (`src/Mod/FcBridge/`, loopback TCP `127.0.0.1:9876`)
and exposes its capabilities as MCP tools.

## Vendored source

- Project: **theosib/FreeCAD-MCP-Server** — https://github.com/theosib/FreeCAD-MCP-Server
- License: **LGPL-2.1-or-later** (identical to FreeCAD and this fork)
- Vendored: `src/freecad_mcp_agent/{server,bridge,__init__}.py`, `tools/__init__.py`, `pyproject.toml`.

## Tools exposed

`execute_script` (run_python), `get_screenshot`, `list_documents` /
`get_document_graph` / `inspect_object` (get_state), plus `analyze_shape`,
`get_sketch_diagnostics`, `tracked_recompute`, `reload_handlers`. All forward
JSON-RPC to the FcBridge server; host/port via `FREECAD_MCP_HOST`/`FREECAD_MCP_PORT`.

## Fork changes

- Added `SPDX-License-Identifier: LGPL-2.1-or-later` headers.
- Repackaged under `tools/freecad-mcp/`; added `setup.sh` (venv bootstrap),
  `run-bridge.sh` (self-locating launcher), and the repo-root `.mcp.json`.
- **`get_screenshot` now returns a proper MCP `Image`** (was a base64 string in a
  text payload) so AI clients can *view* the render directly.
- Pinned **`mcp[cli]>=1.2.0,<2`** — the vendored `server.py` targets the FastMCP
  1.x API (`mcp.server.fastmcp`), which moved in mcp 2.0. Installed non-editable
  (`pip install .`, not `-e`) so the console script imports reliably.

## Usage

1. `tools/freecad-mcp/setup.sh` — once per checkout (creates `.venv`, installs).
2. Start FreeCAD with the FcBridge server: `./run-freecad-mcp.sh`.
3. Claude Code auto-spawns the bridge from `.mcp.json`; the `freecad` MCP tools
   then drive the running GUI. (Registering a new MCP server requires Claude Code
   to reload `.mcp.json` — i.e. a restart.)
