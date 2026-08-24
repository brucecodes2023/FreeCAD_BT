# SPDX-License-Identifier: LGPL-2.1-or-later
# Vendored from theosib/FreeCAD-MCP-Server (LGPL-2.1-or-later).
# FcBridge stdio MCP bridge (fork-only dev/test). See ATTRIBUTION.md.
"""FastMCP server — the entry point spawned by Claude via stdio.

This server exposes FreeCAD inspection tools over the Model Context Protocol.
It connects to the FreeCAD addon's RPC server via TCP to execute operations
in FreeCAD's runtime context.
"""

import base64

from mcp.server.fastmcp import FastMCP, Image

from freecad_mcp_agent.bridge import FreeCADBridge

mcp = FastMCP("freecad-debug")
bridge = FreeCADBridge()


# ── Document tools ───────────────────────────────────────────────────

@mcp.tool()
def list_documents() -> list[dict]:
    """List all open FreeCAD documents with their names, labels, file paths,
    object counts, and modification status."""
    return bridge.call("list_documents")


@mcp.tool()
def get_document_graph(doc_name: str = "") -> dict:
    """Get a structured representation of a document's feature tree.

    Returns every object with its TypeId, label, properties, dependency
    links (InList/OutList), validity state, and touch state. This is the
    primary tool for understanding what a FreeCAD model contains.

    Args:
        doc_name: Document name. Empty string uses the active document.
    """
    return bridge.call("get_document_graph", {"doc_name": doc_name})


# ── Object inspection tools ──────────────────────────────────────────

@mcp.tool()
def inspect_object(name: str, doc_name: str = "") -> dict:
    """Get a full property dump and shape analysis for a single FreeCAD object.

    Returns all properties (with types, groups, and documentation),
    dependency info, validity state, and basic shape metadata if the
    object has geometry.

    Args:
        name: Object name (e.g., "Pad001", "Sketch002").
        doc_name: Document name. Empty string uses the active document.
    """
    return bridge.call("inspect_object", {"name": name, "doc_name": doc_name})


@mcp.tool()
def analyze_shape(name: str, doc_name: str = "") -> dict:
    """Detailed topological analysis of an object's shape.

    Returns shape type, volume, area, center of mass, bounding box,
    topology counts (vertices/edges/faces/solids), face classifications
    (plane/cylinder/cone/sphere/toroid with parameters), and edge details.

    Use this to understand the geometric result of a feature — especially
    useful for diagnosing why a boolean or pocket operation produced
    unexpected geometry.

    Args:
        name: Object name that has a Shape (e.g., "Pad001", "Cut001").
        doc_name: Document name. Empty string uses the active document.
    """
    return bridge.call("analyze_shape", {"name": name, "doc_name": doc_name})


# ── Sketcher tools ───────────────────────────────────────────────────

@mcp.tool()
def get_sketch_diagnostics(name: str, doc_name: str = "") -> dict:
    """Deep inspection of a sketch's constraint health.

    Returns constraint count, geometry count, degrees of freedom,
    whether the sketch is fully constrained, and a detailed list of
    every constraint (type, value, referenced geometry indices, driving
    status, and whether it is redundant or conflicting).

    Also returns geometry elements with type-specific details (line
    endpoints, circle centers/radii, arc parameters).

    This is the primary diagnostic tool for sketch problems —
    over-constrained, under-constrained, or conflicting sketches.

    Args:
        name: Sketch object name (e.g., "Sketch001").
        doc_name: Document name. Empty string uses the active document.
    """
    return bridge.call("get_sketch_diagnostics", {"name": name, "doc_name": doc_name})


# ── Recompute tools ──────────────────────────────────────────────────

@mcp.tool()
def tracked_recompute(doc_name: str = "") -> dict:
    """Recompute a document and track what changed.

    Snapshots every object's validity before recomputing, then diffs
    against the post-recompute state. Reports:
    - new_errors: objects that were valid before but are now invalid
    - resolved: objects that were invalid but are now valid
    - persistent_errors: objects that remain invalid
    - valid_count: number of objects that stayed valid

    Use this instead of raw recompute to understand the impact of changes.

    Args:
        doc_name: Document name. Empty string uses the active document.
    """
    return bridge.call("tracked_recompute", {"doc_name": doc_name})


# ── Script execution ─────────────────────────────────────────────────

@mcp.tool()
def execute_script(script: str) -> dict:
    """Execute arbitrary Python code in FreeCAD's interpreter context.

    The script has access to: FreeCAD, FreeCADGui, App, Gui, doc (active document).
    Stdout and stderr are captured and returned.

    Use this as an escape hatch for operations not covered by the specific
    tools above. For example: creating objects, modifying properties,
    running macros, or accessing FreeCAD APIs not yet exposed as tools.

    Args:
        script: Python code to execute.
    """
    return bridge.call("execute_script", {"script": script})


# ── Viewport tools ───────────────────────────────────────────────────

@mcp.tool()
def get_screenshot(width: int = 1024, height: int = 768):
    """Capture the current 3D viewport as a PNG image for visual inspection.

    Returns a proper MCP image (so the caller can *see* it), or an error dict
    if the viewport could not be captured.

    Args:
        width: Image width in pixels.
        height: Image height in pixels.
    """
    # FcBridge fork change: return a real MCP Image instead of a base64 string,
    # so AI clients can view the render directly (see ATTRIBUTION.md).
    res = bridge.call("get_screenshot", {"width": width, "height": height})
    b64 = res.get("base64_png") if isinstance(res, dict) else None
    if not b64:
        return res  # surface the error payload as-is
    return Image(data=base64.b64decode(b64), format="png")


# ── Development tools ────────────────────────────────────────────────

@mcp.tool()
def reload_handlers() -> dict:
    """Hot-reload all FreeCAD addon handler modules.

    Call this after editing handler code (in freecad_addon/handlers/)
    to pick up changes without restarting FreeCAD. Reloads all handler
    modules and re-registers them with the RPC server.
    """
    return bridge.call("reload_handlers")


def main():
    """Entry point for the freecad-mcp-agent command."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
