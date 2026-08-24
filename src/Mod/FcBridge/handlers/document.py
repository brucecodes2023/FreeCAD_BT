# SPDX-License-Identifier: LGPL-2.1-or-later
# Vendored from theosib/FreeCAD-MCP-Server (LGPL-2.1-or-later).
# Part of FcBridge, a fork-only dev/test module. See ATTRIBUTION.md.
"""Document-level inspection handlers.

These run inside FreeCAD's interpreter on the main thread.
"""

import FreeCAD


def list_documents() -> list[dict]:
    """Return a summary of all open FreeCAD documents."""
    result = []
    for name, doc in FreeCAD.listDocuments().items():
        result.append({
            "name": name,
            "label": doc.Label,
            "file_name": doc.FileName or None,
            "object_count": len(doc.Objects),
            "is_modified": not doc.isSaved() if hasattr(doc, "isSaved") else getattr(doc, "Modified", None),
        })
    return result


def get_document_graph(doc_name: str = "") -> dict:
    """Return a structured representation of the document's feature tree.

    If doc_name is empty, uses the active document.

    Returns a dict mapping object names to their metadata:
    type, label, properties, dependencies, sources, validity, touch state.
    """
    doc = _resolve_doc(doc_name)
    graph = {}
    for obj in doc.Objects:
        props = {}
        for prop_name in obj.PropertiesList:
            try:
                val = getattr(obj, prop_name)
                props[prop_name] = _serialize_value(val)
            except Exception:
                props[prop_name] = "<unreadable>"

        entry = {
            "type": obj.TypeId,
            "label": obj.Label,
            "properties": props,
            "dependencies": [d.Name for d in obj.InList],
            "sources": [s.Name for s in obj.OutList],
        }
        try:
            entry["state"] = "valid" if obj.isValid() else "invalid"
        except AttributeError:
            entry["state"] = "unknown"
        try:
            entry["touch_state"] = "touched" if obj.isTouched() else "clean"
        except AttributeError:
            entry["touch_state"] = "unknown"

        graph[obj.Name] = entry
    return {
        "document": doc.Name,
        "label": doc.Label,
        "objects": graph,
    }


def _resolve_doc(doc_name: str):
    """Resolve a document by name, defaulting to the active document."""
    if doc_name:
        doc = FreeCAD.getDocument(doc_name)
        if doc is None:
            raise ValueError(f"Document not found: {doc_name}")
        return doc
    doc = FreeCAD.ActiveDocument
    if doc is None:
        raise ValueError("No active document")
    return doc


def _serialize_value(val):
    """Best-effort serialization of a FreeCAD property value to JSON-safe types."""
    if val is None or isinstance(val, (bool, int, float, str)):
        return val
    if isinstance(val, (list, tuple)):
        return [_serialize_value(v) for v in val]
    if isinstance(val, dict):
        return {k: _serialize_value(v) for k, v in val.items()}

    # FreeCAD Vector
    if hasattr(val, "x") and hasattr(val, "y") and hasattr(val, "z"):
        return {"x": val.x, "y": val.y, "z": val.z}

    # FreeCAD Placement
    if hasattr(val, "Base") and hasattr(val, "Rotation"):
        return {
            "base": _serialize_value(val.Base),
            "rotation": _serialize_value(val.Rotation),
        }

    # FreeCAD Rotation (quaternion)
    if hasattr(val, "Q"):
        return {"Q": list(val.Q)}

    # Link to another object
    if hasattr(val, "Name") and hasattr(val, "TypeId"):
        return f"<{val.TypeId} '{val.Name}'>"

    # Fallback: string representation, truncated
    s = repr(val)
    if len(s) > 200:
        s = s[:200] + "..."
    return s
