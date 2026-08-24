# SPDX-License-Identifier: LGPL-2.1-or-later
# Vendored from theosib/FreeCAD-MCP-Server (LGPL-2.1-or-later).
# Part of FcBridge, a fork-only dev/test module. See ATTRIBUTION.md.
"""Sketcher constraint diagnostics handler."""

import FreeCAD

from handlers.document import _resolve_doc


def get_sketch_diagnostics(name: str, doc_name: str = "") -> dict:
    """Deep inspection of sketch constraint health.

    Returns constraint count, geometry count, degrees of freedom,
    full constraint list with conflict/redundancy flags, and
    geometry element details.
    """
    doc = _resolve_doc(doc_name)
    obj = doc.getObject(name)
    if obj is None:
        raise ValueError(f"Object not found: {name}")
    if not hasattr(obj, "ConstraintCount"):
        raise ValueError(f"Object '{name}' is not a sketch (TypeId: {obj.TypeId})")

    sketch = obj

    # Get conflict/redundancy info
    redundant = []
    conflicting = []
    try:
        redundant = list(sketch.getRedundantConstraints())
    except Exception:
        pass
    try:
        conflicting = list(sketch.getConflictingConstraints())
    except Exception:
        pass

    # Solve to get DOF
    dof = None
    try:
        dof = sketch.solve()
    except Exception:
        pass

    # Build constraint list
    constraints = []
    for i, c in enumerate(sketch.Constraints):
        info = {
            "index": i,
            "type": c.Type,
            "name": c.Name if c.Name else None,
            "first": c.First,
            "first_pos": c.FirstPos,
            "second": c.Second,
            "second_pos": c.SecondPos,
            "third": c.Third,
            "third_pos": c.ThirdPos,
            "is_driving": c.Driving,
            "is_in_virtual_space": c.InVirtualSpace,
            "is_active": c.IsActive,
            "is_redundant": i in redundant,
            "is_conflicting": i in conflicting,
        }
        # Value for dimensional constraints
        if hasattr(c, "Value"):
            info["value"] = c.Value
        constraints.append(info)

    # Build geometry list — use sk.Geometry property (getGeometry() removed in weekly)
    geometries = []
    try:
        geo_list = sketch.Geometry
    except AttributeError:
        geo_list = []

    for i, geo in enumerate(geo_list):
        try:
            geo_type = type(geo).__name__
            geo_info = {
                "index": i,
                "type": geo_type,
                "construction": getattr(geo, "Construction", False),
            }
            # Add type-specific details based on available attributes
            if hasattr(geo, "StartPoint") and hasattr(geo, "EndPoint"):
                # LineSegment, BSplineCurve, etc.
                geo_info["start"] = _point_to_list(geo.StartPoint)
                geo_info["end"] = _point_to_list(geo.EndPoint)
            if hasattr(geo, "Center"):
                geo_info["center"] = _point_to_list(geo.Center)
            if hasattr(geo, "Radius"):
                geo_info["radius"] = geo.Radius
            if hasattr(geo, "FirstParameter") and hasattr(geo, "LastParameter"):
                geo_info["first_param"] = geo.FirstParameter
                geo_info["last_param"] = geo.LastParameter
            if geo_type == "Point" and hasattr(geo, "X"):
                geo_info["position"] = [geo.X, geo.Y, geo.Z]

            geometries.append(geo_info)
        except Exception as e:
            geometries.append({"index": i, "error": str(e)})

    # External geometry
    external_count = 0
    try:
        external_count = sketch.ExternalGeometryCount
    except Exception:
        pass

    return {
        "name": sketch.Name,
        "label": sketch.Label,
        "constraint_count": sketch.ConstraintCount,
        "geometry_count": sketch.GeometryCount,
        "external_geometry_count": external_count,
        "degrees_of_freedom": dof,
        "fully_constrained": getattr(sketch, "FullyConstrained", None),
        "redundant_indices": redundant,
        "conflicting_indices": conflicting,
        "constraints": constraints,
        "geometries": geometries,
    }


def _point_to_list(pt) -> list:
    """Convert a FreeCAD vector/point to a list."""
    if hasattr(pt, "x"):
        return [pt.x, pt.y, pt.z]
    return [pt.X, pt.Y, pt.Z]
