# SPDX-License-Identifier: LGPL-2.1-or-later

"""Insert DXF/DWG into a sketch.

Simple ASCII DXF (LINE / CIRCLE / ARC only) is written straight into the
sketch so inner slots (e.g. header pin rails) are not dropped by Draft's
fused C++ importer. DWG and complex DXF still go through Draft, with the
import dialog and fused mode suppressed.
"""

from __future__ import annotations

import os

MODE_ACTIVE = "active"
MODE_NEW = "new"
CAD_EXTENSIONS = (".dxf", ".dwg")
_ENTITY_TYPES = ("LINE", "CIRCLE", "ARC", "LWPOLYLINE", "POLYLINE", "SPLINE")
_SIMPLE_KINDS = frozenset({"LINE", "CIRCLE", "ARC"})
_COMPLEX_KINDS = frozenset(
    {
        "LWPOLYLINE",
        "POLYLINE",
        "SPLINE",
        "ELLIPSE",
        "INSERT",
        "HATCH",
        "SOLID",
        "3DFACE",
        "MLINE",
        "HELIX",
        "MESH",
        "TRACE",
        "REGION",
        "BODY",
        "WIPEOUT",
    }
)


def is_cad_path(path: str) -> bool:
    return os.path.splitext(path or "")[1].lower() in CAD_EXTENSIONS


def choose_insert_mode(*, editing_sketch: bool) -> str:
    """In-edit → addTo active sketch. Idle → new sketch on a plane."""
    return MODE_ACTIVE if editing_sketch else MODE_NEW


def dxf_entity_counts(text: str) -> dict[str, int]:
    """Count common entity types in the ENTITIES section of an ASCII DXF."""
    counts = {name: 0 for name in _ENTITY_TYPES}
    if not text:
        return counts
    upper = text.upper()
    start = upper.find("\nENTITIES")
    if start < 0:
        start = upper.find("ENTITIES")
    if start < 0:
        return counts
    end = upper.find("ENDSEC", start)
    body = upper[start : end if end >= 0 else None]
    lines = [ln.strip() for ln in body.splitlines()]
    for i, ln in enumerate(lines):
        if ln == "0" and i + 1 < len(lines) and lines[i + 1] in counts:
            counts[lines[i + 1]] += 1
    return counts


def dxf_geometry_count(text: str) -> int:
    return sum(dxf_entity_counts(text).values())


def _iter_dxf_pairs(text: str):
    lines = text.splitlines()
    i = 0
    while i + 1 < len(lines):
        raw_code = lines[i].strip()
        value = lines[i + 1].strip()
        i += 2
        try:
            yield int(raw_code), value
        except ValueError:
            continue


def _float_code(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_ascii_dxf_entities(text: str) -> tuple[list[dict], list[str]]:
    """Parse LINE / CIRCLE / ARC in ENTITIES. Returns (entities, complex types)."""
    entities: list[dict] = []
    complex_kinds: list[str] = []
    if not text or text.startswith("AutoCAD Binary"):
        return entities, complex_kinds

    in_entities = False
    current: dict | None = None

    def flush() -> None:
        nonlocal current
        if current is None:
            return
        kind = current.get("kind")
        if kind == "LINE" and all(k in current for k in ("x1", "y1", "x2", "y2")):
            current.setdefault("z1", 0.0)
            current.setdefault("z2", 0.0)
            entities.append(current)
        elif kind == "CIRCLE" and all(k in current for k in ("x", "y", "r")):
            current.setdefault("z", 0.0)
            entities.append(current)
        elif kind == "ARC" and all(k in current for k in ("x", "y", "r", "start", "end")):
            current.setdefault("z", 0.0)
            entities.append(current)
        current = None

    for code, value in _iter_dxf_pairs(text):
        if not in_entities:
            if code == 2 and value.upper() == "ENTITIES":
                in_entities = True
            continue
        if code == 0 and value.upper() == "ENDSEC":
            flush()
            break
        if code == 0:
            flush()
            kind = value.upper()
            if kind in _SIMPLE_KINDS:
                current = {"kind": kind}
            else:
                current = None
                if kind in _COMPLEX_KINDS:
                    complex_kinds.append(kind)
            continue
        if current is None:
            continue
        kind = current["kind"]
        if kind == "LINE":
            if code == 10:
                current["x1"] = _float_code(value)
            elif code == 20:
                current["y1"] = _float_code(value)
            elif code == 30:
                current["z1"] = _float_code(value)
            elif code == 11:
                current["x2"] = _float_code(value)
            elif code == 21:
                current["y2"] = _float_code(value)
            elif code == 31:
                current["z2"] = _float_code(value)
        elif kind in ("CIRCLE", "ARC"):
            if code == 10:
                current["x"] = _float_code(value)
            elif code == 20:
                current["y"] = _float_code(value)
            elif code == 30:
                current["z"] = _float_code(value)
            elif code == 40:
                current["r"] = _float_code(value)
            elif kind == "ARC" and code == 50:
                current["start"] = _float_code(value)
            elif kind == "ARC" and code == 51:
                current["end"] = _float_code(value)
    flush()
    return entities, complex_kinds


def ascii_dxf_is_simple(text: str) -> bool:
    entities, complex_kinds = parse_ascii_dxf_entities(text)
    return bool(entities) and not complex_kinds


def sample_rectangle_dxf(width: float = 100.0, height: float = 50.0) -> str:
    """Minimal R12 DXF: closed rectangle of four LINE entities (test fixture)."""

    def line(x1: float, y1: float, x2: float, y2: float, layer: str = "0") -> str:
        return (
            f"0\nLINE\n8\n{layer}\n10\n{x1}\n20\n{y1}\n30\n0.0\n"
            f"11\n{x2}\n21\n{y2}\n31\n0.0\n"
        )

    w, h = float(width), float(height)
    ents = (
        line(0, 0, w, 0)
        + line(w, 0, w, h)
        + line(w, h, 0, h)
        + line(0, h, 0, 0)
    )
    return (
        "0\nSECTION\n2\nHEADER\n0\nENDSEC\n"
        "0\nSECTION\n2\nENTITIES\n"
        f"{ents}"
        "0\nENDSEC\n0\nEOF\n"
    )


def sample_pin_slot_dxf() -> str:
    """Outer rectangle plus a 3.2 mm header slot (PINS-layer rails)."""

    def line(x1: float, y1: float, x2: float, y2: float, layer: str) -> str:
        return (
            f"0\nLINE\n8\n{layer}\n10\n{x1}\n20\n{y1}\n30\n0.0\n"
            f"11\n{x2}\n21\n{y2}\n31\n0.0\n"
        )

    ents = (
        line(0, 0, 40, 0, "OUTLINE")
        + line(40, 0, 40, 50, "OUTLINE")
        + line(40, 50, 0, 50, "OUTLINE")
        + line(0, 50, 0, 0, "OUTLINE")
        + line(-14.3, -4, -11.1, -4, "PINS")
        + line(-11.1, -4, -11.1, 36, "PINS")
        + line(-11.1, 36, -14.3, 36, "PINS")
        + line(-14.3, 36, -14.3, -4, "PINS")
    )
    return (
        "0\nSECTION\n2\nHEADER\n0\nENDSEC\n"
        "0\nSECTION\n2\nENTITIES\n"
        f"{ents}"
        "0\nENDSEC\n0\nEOF\n"
    )


def _status(msg: str, ms: int = 8000) -> None:
    try:
        from .qtutil import app_gui

        _, Gui = app_gui()
        Gui.getMainWindow().statusBar().showMessage(msg, ms)
    except Exception:
        pass


def editing_sketch():
    """Return the SketchObject currently in edit, or None."""
    from .qtutil import app_gui

    App, Gui = app_gui()
    try:
        vp = Gui.ActiveDocument.getInEdit()
        obj = getattr(vp, "Object", None) if vp is not None else None
    except Exception:
        obj = None
    if obj is None:
        return None
    tid = getattr(obj, "TypeId", "")
    if "Sketch" in tid:
        return obj
    return None


def _read_ascii_dxf(path: str) -> str | None:
    with open(path, "rb") as fh:
        raw = fh.read()
    if raw.startswith(b"AutoCAD Binary"):
        return None
    return raw.decode("latin-1")


def _restore_draft_prefs(hgrp, saved: dict) -> None:
    for key, (kind, value) in saved.items():
        if kind == "bool":
            hgrp.SetBool(key, value)
        elif kind == "float":
            hgrp.SetFloat(key, value)
        elif kind == "int":
            hgrp.SetInt(key, value)


def _snapshot_draft_prefs(hgrp) -> dict:
    return {
        "dxfCreateSketch": ("bool", hgrp.GetBool("dxfCreateSketch", False)),
        "dxfCreateDraft": ("bool", hgrp.GetBool("dxfCreateDraft", False)),
        "dxfCreatePart": ("bool", hgrp.GetBool("dxfCreatePart", True)),
        "dxfScaling": ("float", hgrp.GetFloat("dxfScaling", 1.0)),
        "dxfShowDialog": ("bool", hgrp.GetBool("dxfShowDialog", True)),
        "dxfUseLegacyImporter": ("bool", hgrp.GetBool("dxfUseLegacyImporter", False)),
        "joingeometry": ("bool", hgrp.GetBool("joingeometry", False)),
        "dxfUseDraftVisGroups": ("bool", hgrp.GetBool("dxfUseDraftVisGroups", True)),
        "dxfImportAsDraft": ("bool", hgrp.GetBool("dxfImportAsDraft", False)),
        "dxfImportAsPrimitives": ("bool", hgrp.GetBool("dxfImportAsPrimitives", False)),
        "dxfImportAsShapes": ("bool", hgrp.GetBool("dxfImportAsShapes", False)),
        "dxfImportAsFused": ("bool", hgrp.GetBool("dxfImportAsFused", False)),
        "DxfImportMode": ("int", hgrp.GetInt("DxfImportMode", 2)),
    }


def _import_as_draft(path: str, doc, scale: float) -> list:
    import FreeCAD as App

    hgrp = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Draft")
    saved = _snapshot_draft_prefs(hgrp)
    before = {obj.Name for obj in doc.Objects}
    try:
        # Individual Draft objects, no dialog, no fused compound, no join.
        hgrp.SetBool("dxfCreateSketch", False)
        hgrp.SetBool("dxfCreateDraft", True)
        hgrp.SetBool("dxfCreatePart", False)
        hgrp.SetFloat("dxfScaling", float(scale))
        hgrp.SetBool("dxfShowDialog", False)
        hgrp.SetBool("dxfUseLegacyImporter", True)
        hgrp.SetBool("joingeometry", False)
        hgrp.SetBool("dxfUseDraftVisGroups", False)
        hgrp.SetBool("dxfImportAsDraft", True)
        hgrp.SetBool("dxfImportAsPrimitives", False)
        hgrp.SetBool("dxfImportAsShapes", False)
        hgrp.SetBool("dxfImportAsFused", False)
        hgrp.SetInt("DxfImportMode", 0)
        ext = os.path.splitext(path)[1].lower()
        if ext == ".dwg":
            import importDWG

            importDWG.insert(path, doc.Name)
        else:
            import importDXF

            importDXF.insert(path, doc.Name)
        doc.recompute()
        return [obj for obj in doc.Objects if obj.Name not in before]
    finally:
        _restore_draft_prefs(hgrp, saved)


def _flatten_imported(objs: list) -> list:
    """Prefer objects with a Shape; expand groups from the DXF vis-group import."""
    out = []
    for obj in objs:
        kids = getattr(obj, "Group", None)
        if kids:
            out.extend(_flatten_imported(list(kids)))
            continue
        if hasattr(obj, "Shape"):
            out.append(obj)
    return [obj for obj in (out or list(objs)) if hasattr(obj, "Shape")]


def _ensure_target_sketch():
    """Idle path: sketch on selected plane/face, else XY origin plane."""
    from .sketch_planes import (
        _ensure_body,
        create_sketch_from_selection,
        create_sketch_on_plane,
    )

    sketch = create_sketch_from_selection()
    if sketch is not None:
        return sketch
    _ensure_body()
    return create_sketch_on_plane("XY")


def _apply_autoconstraints(sketch) -> None:
    try:
        from draftutils import utils as draft_utils

        tol = draft_utils.tolerance()
    except Exception:
        tol = 1e-3
    sketch.detectMissingPointOnPointConstraints(tol)
    sketch.makeMissingPointOnPointCoincident(False)
    sketch.detectMissingVerticalHorizontalConstraints(tol)
    sketch.makeMissingVerticalHorizontal(False)
    sketch.solve()
    for idx in list(sketch.RedundantConstraints)[::-1]:
        sketch.delConstraint(idx - 1)


def _add_simple_entities_to_sketch(sketch, entities: list[dict], scale: float) -> int:
    """Map DXF XY onto sketch XY (Fusion-style). Returns geometry added."""
    import math

    import Part
    from FreeCAD import Vector

    s = float(scale)
    added = 0
    for ent in entities:
        kind = ent["kind"]
        if kind == "LINE":
            p1 = Vector(ent["x1"] * s, ent["y1"] * s, 0)
            p2 = Vector(ent["x2"] * s, ent["y2"] * s, 0)
            if p1.distanceToPoint(p2) < 1e-12:
                continue
            sketch.addGeometry(Part.LineSegment(p1, p2), False)
            added += 1
        elif kind == "CIRCLE":
            r = abs(ent["r"] * s)
            if r < 1e-12:
                continue
            center = Vector(ent["x"] * s, ent["y"] * s, 0)
            sketch.addGeometry(Part.Circle(center, Vector(0, 0, 1), r), False)
            added += 1
        elif kind == "ARC":
            r = abs(ent["r"] * s)
            if r < 1e-12:
                continue
            center = Vector(ent["x"] * s, ent["y"] * s, 0)
            circle = Part.Circle(center, Vector(0, 0, 1), r)
            start = math.radians(ent["start"])
            end = math.radians(ent["end"])
            sketch.addGeometry(Part.ArcOfCircle(circle, start, end), False)
            added += 1
    return added


def _insert_simple_ascii(path: str, scale: float, autoconstraints: bool, sketch):
    text = _read_ascii_dxf(path)
    if text is None or not ascii_dxf_is_simple(text):
        return None
    entities, _complex = parse_ascii_dxf_entities(text)
    from .qtutil import app_gui

    App, Gui = app_gui()
    if App.ActiveDocument is None:
        App.newDocument()
    doc = App.ActiveDocument
    target = sketch if sketch is not None else editing_sketch()
    if target is None:
        target = _ensure_target_sketch()
    added = _add_simple_entities_to_sketch(target, entities, scale)
    if added == 0:
        return None
    if autoconstraints:
        try:
            _apply_autoconstraints(target)
        except Exception:
            pass
    doc.recompute()
    try:
        Gui.ActiveDocument.setEdit(target.Name)
    except Exception:
        pass
    n = 0
    try:
        n = len(target.Geometry)
    except Exception:
        n = added
    _status(f"Inserted {added} DXF entities into {target.Label} ({n} geometry).")
    return target


def insert_file(
    path: str,
    *,
    scale: float = 1.0,
    autoconstraints: bool = True,
    sketch=None,
):
    """Import path into sketch (addTo) or a new sketch. Returns the sketch."""
    if not is_cad_path(path):
        raise ValueError(f"not a DXF/DWG file: {path}")
    if not os.path.isfile(path):
        raise FileNotFoundError(path)

    if os.path.splitext(path)[1].lower() == ".dxf":
        simple = _insert_simple_ascii(path, scale, autoconstraints, sketch)
        if simple is not None:
            return simple

    from draftmake.make_sketch import make_sketch

    from .qtutil import app_gui

    App, Gui = app_gui()
    if App.ActiveDocument is None:
        App.newDocument()
    doc = App.ActiveDocument

    imported = _flatten_imported(_import_as_draft(path, doc, scale))
    if not imported:
        raise RuntimeError("DXF/DWG import produced no objects")

    target = sketch if sketch is not None else editing_sketch()
    if target is None:
        target = _ensure_target_sketch()

    saved_plm = target.Placement
    result = make_sketch(
        imported,
        autoconstraints=autoconstraints,
        addTo=target,
        delete=True,
    )
    # make_sketch overwrites Placement when addTo is set; keep the sketch plane.
    try:
        target.Placement = saved_plm
    except Exception:
        pass
    doc.recompute()
    sketch_obj = result if result is not None else target
    try:
        Gui.ActiveDocument.setEdit(sketch_obj.Name)
    except Exception:
        pass
    n = 0
    try:
        n = len(sketch_obj.Geometry)
    except Exception:
        pass
    _status(f"Inserted DXF/DWG into {sketch_obj.Label} ({n} geometry).")
    return sketch_obj


def _ask_path_and_scale():
    from .qtutil import qt

    _QtCore, _QtGui, QtWidgets = qt()
    parent = None
    try:
        from .qtutil import app_gui

        _, Gui = app_gui()
        parent = Gui.getMainWindow()
    except Exception:
        pass
    path, _filt = QtWidgets.QFileDialog.getOpenFileName(
        parent,
        "Insert DXF / DWG",
        "",
        "CAD drawings (*.dxf *.dwg);;DXF (*.dxf);;DWG (*.dwg)",
    )
    if not path:
        return None, None
    scale, ok = QtWidgets.QInputDialog.getDouble(
        parent,
        "Insert DXF / DWG",
        "Scale (1 = file units as millimetres):",
        1.0,
        1e-6,
        1e6,
        4,
    )
    if not ok:
        return None, None
    return path, scale


def run_insert_dxf() -> None:
    path, scale = _ask_path_and_scale()
    if not path:
        return
    try:
        insert_file(path, scale=scale, autoconstraints=True)
    except Exception as exc:
        _status(str(exc))
        try:
            from .qtutil import app_gui

            App, _Gui = app_gui()
            App.Console.PrintError(f"BtStudio Insert DXF: {exc}\n")
        except Exception:
            pass
