# SPDX-License-Identifier: LGPL-2.1-or-later
# Vendored from theosib/FreeCAD-MCP-Server (LGPL-2.1-or-later).
# Part of FcBridge, a fork-only dev/test module. See ATTRIBUTION.md.
"""Tracked recompute handler — recompute with full error capture."""

import FreeCAD

from handlers.document import _resolve_doc


def _is_valid(obj) -> bool:
    try:
        return obj.isValid()
    except AttributeError:
        return True  # assume valid if we can't check


def tracked_recompute(doc_name: str = "") -> dict:
    """Recompute a document and track what changed.

    Snapshots object validity before and after recompute, then
    reports new errors, resolved errors, and persistent errors.
    """
    doc = _resolve_doc(doc_name)

    # Snapshot state before recompute
    before = {}
    for obj in doc.Objects:
        before[obj.Name] = {
            "valid": _is_valid(obj),
        }

    # Recompute
    doc.recompute()

    # Analyze changes
    new_errors = []
    resolved = []
    persistent_errors = []
    still_valid = []

    for obj in doc.Objects:
        was_valid = before.get(obj.Name, {}).get("valid", True)
        is_valid = _is_valid(obj)

        if not is_valid and was_valid:
            new_errors.append(_obj_summary(obj))
        elif not is_valid and not was_valid:
            persistent_errors.append(_obj_summary(obj))
        elif is_valid and not was_valid:
            resolved.append(obj.Name)
        else:
            still_valid.append(obj.Name)

    # Check for any new objects (created during recompute, unlikely but possible)
    new_objects = [
        obj.Name for obj in doc.Objects if obj.Name not in before
    ]

    return {
        "document": doc.Name,
        "total_objects": len(doc.Objects),
        "new_errors": new_errors,
        "resolved": resolved,
        "persistent_errors": persistent_errors,
        "valid_count": len(still_valid),
        "new_objects": new_objects,
    }


def _obj_summary(obj) -> dict:
    """Compact summary of an object for error reporting."""
    summary = {
        "name": obj.Name,
        "label": obj.Label,
        "type": obj.TypeId,
    }
    try:
        summary["state"] = list(obj.State) if obj.State else []
    except Exception:
        pass
    return summary
