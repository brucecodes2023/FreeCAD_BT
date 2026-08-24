# SPDX-License-Identifier: LGPL-2.1-or-later

"""One-click Gmsh mesh using bbox diagonal / 20, plus MeshRegion on selected faces."""

from __future__ import annotations

from .core import characteristic_length
from .qtutil import app_gui


def _shape_from_selection():
    App, Gui = app_gui()
    sel = Gui.Selection.getSelection()
    for obj in sel:
        if hasattr(obj, "Shape"):
            return obj
    # fall back to PartDesign body tip / active object
    try:
        body = Gui.ActiveDocument.ActiveView.getActiveObject("pdbody")
        if body is not None and hasattr(body, "Shape"):
            return body
    except Exception:
        pass
    obj = App.ActiveDocument.ActiveObject if App.ActiveDocument else None
    if obj is not None and hasattr(obj, "Shape"):
        return obj
    return None


def _analysis():
    App, _ = app_gui()
    doc = App.ActiveDocument
    try:
        import FemGui

        active = FemGui.getActiveAnalysis()
        if active:
            return active
    except Exception:
        pass
    for obj in doc.Objects:
        if obj.TypeId == "Fem::FemAnalysis":
            return obj
    return None


def auto_mesh(divisor: float = 20.0) -> object:
    App, Gui = app_gui()
    doc = App.ActiveDocument
    if doc is None:
        raise RuntimeError("No active document")
    shape_obj = _shape_from_selection()
    if shape_obj is None:
        raise RuntimeError("Select a solid (or activate a PartDesign Body)")
    diag = shape_obj.Shape.BoundBox.DiagonalLength
    h = characteristic_length(float(diag), divisor)

    import ObjectsFem

    analysis = _analysis()
    if analysis is None:
        analysis = ObjectsFem.makeAnalysis(doc, "Analysis")
        try:
            import FemGui

            FemGui.setActiveAnalysis(analysis)
        except Exception:
            pass

    mesh = ObjectsFem.makeMeshGmsh(doc, "FEMMeshGmsh")
    if hasattr(mesh, "Shape"):
        mesh.Shape = shape_obj
    elif hasattr(mesh, "Part"):
        mesh.Part = shape_obj
    if hasattr(mesh, "CharacteristicLengthMax"):
        mesh.CharacteristicLengthMax = h
    if hasattr(mesh, "ElementOrder"):
        try:
            mesh.ElementOrder = "2nd"
        except Exception:
            pass
    analysis.addObject(mesh)

    # Concentrations: one MeshRegion per selected face/edge, at h/4.
    sel_ex = Gui.Selection.getSelectionEx()
    refs = []
    for s in sel_ex:
        for sub in s.SubElementNames:
            if sub.startswith("Face") or sub.startswith("Edge") or sub.startswith("Vertex"):
                refs.append((s.Object, sub))
    if refs:
        region = ObjectsFem.makeMeshRegion(doc, mesh, h / 4.0, "MeshRegion")
        try:
            region.References = refs
        except Exception:
            pass

    doc.recompute()
    try:
        from femmesh.gmshtools import GmshTools

        GmshTools(mesh).create_mesh()
        doc.recompute()
    except Exception as exc:
        Gui.getMainWindow().statusBar().showMessage(
            f"Gmsh did not run ({exc}). Mesh object created with h={h:.4g}; generate from the mesh task panel.",
            10000,
        )
        return mesh
    Gui.getMainWindow().statusBar().showMessage(
        f"Auto mesh h={h:.4g} (diagonal {diag:.4g} / {divisor})", 6000
    )
    return mesh
