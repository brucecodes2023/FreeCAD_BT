# FcBridge — attribution & provenance

FcBridge is a **fork-only, dev/test** FreeCAD module that exposes the running
FreeCAD GUI's runtime state over a loopback TCP JSON-RPC server, so the AI
verification MCP (see `OVERVIEW.md` §9) can drive and observe the GUI.

## Vendored source

The RPC server and handlers are **vendored from**:

- Project: **theosib/FreeCAD-MCP-Server**
- URL: https://github.com/theosib/FreeCAD-MCP-Server
- License: **LGPL-2.1-or-later** (identical to FreeCAD and this fork)

Vendored files: `rpc_server.py`, `mcp_commands.py`, `handlers/*.py`, `__init__.py`.

## Changes made in this fork

- **`InitGui.py` rewritten** (the upstream one had fork-compat bugs — `__file__`
  not defined during FreeCAD's exec, and a `NameError` in a workbench command).
  Ours is a minimal, `__file__`-safe loader that starts the server **only when
  `FCBRIDGE_TOKEN` is set** (off by default), on loopback, deferred to the Qt
  event loop. The upstream workbench/menu machinery is dropped.
- **`mcp_commands._get_server(port=None)`** — accept a port (from `FCBRIDGE_PORT`).
- Added `SPDX-License-Identifier: LGPL-2.1-or-later` headers to vendored files.

## Security posture

Executes arbitrary Python inside FreeCAD — **dev/test only**. It binds
`127.0.0.1` and starts **only** when `FCBRIDGE_TOKEN` is present in the
environment (the `run-freecad-mcp.sh` launcher sets it). Normal launches never
start the server. Per-request token auth is a future hardening.
