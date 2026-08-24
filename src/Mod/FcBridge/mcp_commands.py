# SPDX-License-Identifier: LGPL-2.1-or-later
# Vendored from theosib/FreeCAD-MCP-Server (LGPL-2.1-or-later).
# Part of FcBridge, a fork-only dev/test module. See ATTRIBUTION.md.
"""FreeCAD GUI commands for starting/stopping the MCP RPC server."""

import importlib

import FreeCAD
import FreeCADGui

from rpc_server import RPCServer, DEFAULT_PORT

# Module-level server instance, shared across commands.
_server: RPCServer | None = None

# Handler modules that get reloaded on hot-reload.
_HANDLER_MODULES = [
    "handlers.document",
    "handlers.execution",
    "handlers.inspection",
    "handlers.sketcher",
    "handlers.recompute",
    "handlers.viewport",
]


def _get_server(port=None) -> RPCServer:
    global _server
    if _server is None:
        _server = RPCServer(port=port) if port else RPCServer()
        _register_handlers(_server)
    return _server


def _register_handlers(server: RPCServer) -> None:
    """Register all handler functions with the RPC server."""
    from handlers.document import list_documents, get_document_graph
    from handlers.execution import execute_script
    from handlers.inspection import inspect_object, analyze_shape
    from handlers.sketcher import get_sketch_diagnostics
    from handlers.recompute import tracked_recompute
    from handlers.viewport import get_screenshot

    server.register_all({
        "list_documents": list_documents,
        "get_document_graph": get_document_graph,
        "execute_script": execute_script,
        "inspect_object": inspect_object,
        "analyze_shape": analyze_shape,
        "get_sketch_diagnostics": get_sketch_diagnostics,
        "tracked_recompute": tracked_recompute,
        "get_screenshot": get_screenshot,
        "reload_handlers": _reload_handlers,
    })


def _reload_handlers() -> dict:
    """Hot-reload all handler modules and re-register them.

    Call this after editing handler code to pick up changes
    without restarting FreeCAD.
    """
    import sys

    reloaded = []
    errors = []

    for mod_name in _HANDLER_MODULES:
        if mod_name in sys.modules:
            try:
                importlib.reload(sys.modules[mod_name])
                reloaded.append(mod_name)
            except Exception as e:
                errors.append({"module": mod_name, "error": str(e)})
        else:
            # Not yet imported — will be fresh on next _register_handlers
            reloaded.append(f"{mod_name} (not loaded, will be fresh)")

    # Re-register handlers with freshly-reloaded functions
    server = _get_server()
    _register_handlers(server)

    return {
        "success": len(errors) == 0,
        "reloaded": reloaded,
        "errors": errors,
    }


class StartRPCServer:
    """Start the MCP RPC server."""

    def GetResources(self):
        return {
            "MenuText": "Start RPC Server",
            "ToolTip": f"Start the MCP debug agent RPC server on port {DEFAULT_PORT}",
        }

    def Activated(self):
        server = _get_server()
        if server.is_running:
            FreeCAD.Console.PrintWarning("MCP RPC server is already running\n")
            return
        server.start()
        FreeCAD.Console.PrintMessage(
            f"MCP RPC server started on {server.host}:{server.port}\n"
        )

    def IsActive(self):
        return True


class StopRPCServer:
    """Stop the MCP RPC server."""

    def GetResources(self):
        return {
            "MenuText": "Stop RPC Server",
            "ToolTip": "Stop the MCP debug agent RPC server",
        }

    def Activated(self):
        server = _get_server()
        if not server.is_running:
            FreeCAD.Console.PrintWarning("MCP RPC server is not running\n")
            return
        server.stop()
        FreeCAD.Console.PrintMessage("MCP RPC server stopped\n")

    def IsActive(self):
        return True


FreeCADGui.addCommand("StartRPCServer", StartRPCServer())
FreeCADGui.addCommand("StopRPCServer", StopRPCServer())
