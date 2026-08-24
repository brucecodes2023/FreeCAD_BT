# SPDX-License-Identifier: LGPL-2.1-or-later
# FcBridge — FreeCAD verification bridge (fork-only, dev/test use).
#
# Gated loader: starts a loopback TCP JSON-RPC server inside the running
# FreeCAD GUI *only* when the environment variable FCBRIDGE_TOKEN is set.
# In normal use (no token) this Mod does nothing. See OVERVIEW.md §9.
#
# The RPC handlers (rpc_server.py, mcp_commands.py, handlers/) are vendored
# from theosib/FreeCAD-MCP-Server (LGPL-2.1-or-later); see ATTRIBUTION.md.
# This InitGui replaces the upstream one (which had fork-compat bugs) with a
# minimal, env-gated, __file__-safe loader.

import os
import sys

import FreeCAD

# ── Locate this module's directory so siblings (rpc_server, mcp_commands,
#    handlers/) are importable. Prefer the explicit env the launcher sets;
#    fall back to __file__ (not always defined when FreeCAD execs InitGui). ──
_addon_dir = os.environ.get("FCBRIDGE_DIR")
if not _addon_dir:
    try:
        _addon_dir = os.path.dirname(os.path.realpath(__file__))
    except NameError:
        _addon_dir = None
if _addon_dir and _addon_dir not in sys.path:
    sys.path.insert(0, _addon_dir)


def _enabled() -> bool:
    """FcBridge only runs when a token is present (dev/test opt-in)."""
    return bool(os.environ.get("FCBRIDGE_TOKEN"))


def _start_server() -> None:
    try:
        import mcp_commands  # noqa: F401 — vendored, registers handlers
        port = int(os.environ.get("FCBRIDGE_PORT", "9876"))
        server = mcp_commands._get_server(port=port)
        if not server.is_running:
            server.start()
        FreeCAD.Console.PrintMessage(
            f"FcBridge: RPC server listening on 127.0.0.1:{port}\n"
        )
    except Exception as exc:  # pragma: no cover - startup diagnostics
        import traceback
        FreeCAD.Console.PrintError(
            f"FcBridge: failed to start RPC server: {exc}\n{traceback.format_exc()}\n"
        )


if _enabled():
    # Defer until the Qt event loop is running so the server's main-thread
    # QTimer work queue can be created safely.
    try:
        try:
            from PySide6.QtCore import QTimer
        except ImportError:  # older Qt bindings
            from PySide2.QtCore import QTimer
        QTimer.singleShot(1000, _start_server)
        FreeCAD.Console.PrintMessage(
            "FcBridge: enabled (FCBRIDGE_TOKEN set); server start scheduled\n"
        )
    except Exception as exc:  # no Qt (headless) — nothing to do
        FreeCAD.Console.PrintWarning(f"FcBridge: Qt unavailable, not starting: {exc}\n")
