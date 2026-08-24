# SPDX-License-Identifier: LGPL-2.1-or-later
# Vendored from theosib/FreeCAD-MCP-Server (LGPL-2.1-or-later).
# Part of FcBridge, a fork-only dev/test module. See ATTRIBUTION.md.
"""Object and shape inspection handlers."""

import FreeCAD

from handlers.document import _resolve_doc, _serialize_value


def inspect_object(name: str, doc_name: str = "") -> dict:
    """Full property dump and shape analysis for a single object.

    Returns all properties, shape info (if the object has a Shape),
    dependency info, and validity state.
    """
    doc = _resolve_doc(doc_name)
    obj = doc.getObject(name)
    if obj is None:
        raise ValueError(f"Object not found: {name}")

    # Collect all properties grouped by their group
    properties = {}
    for prop_name in obj.PropertiesList:
        try:
            val = getattr(obj, prop_name)
            properties[prop_name] = {
                "value": _serialize_value(val),
                "type": obj.getTypeIdOfProperty(prop_name),
                "group": obj.getGroupOfProperty(prop_name),
                "doc": obj.getDocumentationOfProperty(prop_name),
            }
        except Exception as e:
            properties[prop_name] = {"value": f"<error: {e}>", "type": "unknown"}

    result = {
        "name": obj.Name,
        "label": obj.Label,
        "type_id": obj.TypeId,
        "state": _safe_validity(obj),
        "touch_state": _safe_touch_state(obj),
        "dependencies": [d.Name for d in obj.InList],
        "sources": [s.Name for s in obj.OutList],
        "properties": properties,
    }

    # Add shape analysis if the object has a Shape
    if hasattr(obj, "Shape") and obj.Shape and not obj.Shape.isNull():
        result["shape"] = _basic_shape_info(obj.Shape)

    return result


def analyze_shape(name: str, doc_name: str = "") -> dict:
    """Detailed topological analysis of an object's shape.

    Returns type, volume, area, center of mass, bounding box, topology counts,
    face classifications, and validity info.
    """
    doc = _resolve_doc(doc_name)
    obj = doc.getObject(name)
    if obj is None:
        raise ValueError(f"Object not found: {name}")
    if not hasattr(obj, "Shape") or obj.Shape.isNull():
        raise ValueError(f"Object '{name}' has no shape")

    shape = obj.Shape
    result = _basic_shape_info(shape)

    # Detailed face analysis
    result["faces"] = []
    for i, face in enumerate(shape.Faces):
        face_info = {
            "index": i,
            "area": face.Area,
            "center_of_mass": _vec_to_list(face.CenterOfMass),
        }
        # Classify the surface type
        surface = face.Surface
        surface_type = type(surface).__name__
        face_info["surface_type"] = surface_type

        if surface_type == "Plane":
            face_info["normal"] = _vec_to_list(surface.Axis)
            face_info["position"] = _vec_to_list(surface.Position)
        elif surface_type == "Cylinder":
            face_info["axis"] = _vec_to_list(surface.Axis)
            face_info["center"] = _vec_to_list(surface.Center)
            face_info["radius"] = surface.Radius
        elif surface_type == "Cone":
            face_info["axis"] = _vec_to_list(surface.Axis)
            face_info["apex"] = _vec_to_list(surface.Apex)
            face_info["semi_angle"] = surface.SemiAngle
        elif surface_type == "Sphere":
            face_info["center"] = _vec_to_list(surface.Center)
            face_info["radius"] = surface.Radius
        elif surface_type == "Toroid":
            face_info["axis"] = _vec_to_list(surface.Axis)
            face_info["center"] = _vec_to_list(surface.Center)
            face_info["major_radius"] = surface.MajorRadius
            face_info["minor_radius"] = surface.MinorRadius

        result["faces"].append(face_info)

    # Edge analysis
    result["edges"] = []
    for i, edge in enumerate(shape.Edges):
        edge_info = {
            "index": i,
            "length": edge.Length,
            "curve_type": type(edge.Curve).__name__,
        }
        result["edges"].append(edge_info)

    return result


def _basic_shape_info(shape) -> dict:
    """Extract basic shape metadata."""
    info = {
        "shape_type": shape.ShapeType,
        "is_valid": shape.isValid(),
        "is_null": shape.isNull(),
        "topology": {
            "vertices": len(shape.Vertexes),
            "edges": len(shape.Edges),
            "wires": len(shape.Wires),
            "faces": len(shape.Faces),
            "shells": len(shape.Shells),
            "solids": len(shape.Solids),
            "compounds": len(shape.Compounds),
        },
        "bounding_box": {
            "min": [shape.BoundBox.XMin, shape.BoundBox.YMin, shape.BoundBox.ZMin],
            "max": [shape.BoundBox.XMax, shape.BoundBox.YMax, shape.BoundBox.ZMax],
            "diagonal": shape.BoundBox.DiagonalLength,
        },
        "area": shape.Area,
    }

    if shape.ShapeType == "Solid" or shape.Solids:
        info["volume"] = shape.Volume
        info["center_of_mass"] = _vec_to_list(shape.CenterOfMass)

    try:
        info["is_closed"] = shape.isClosed()
    except Exception:
        pass

    return info


def _safe_validity(obj) -> str:
    try:
        return "valid" if obj.isValid() else "invalid"
    except AttributeError:
        return "unknown"


def _safe_touch_state(obj) -> str:
    try:
        return "touched" if obj.isTouched() else "clean"
    except AttributeError:
        return "unknown"


def _vec_to_list(vec) -> list:
    return [vec.x, vec.y, vec.z]
