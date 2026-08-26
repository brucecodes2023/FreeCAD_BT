# SPDX-License-Identifier: LGPL-2.1-or-later

"""FoamCase FeaturePython — stores spec, writes the case directory."""

from __future__ import annotations

from pathlib import Path

from .foam_write import FoamCaseSpec, bbox_mm_from_boundbox, write_case
from .openfoam import INCOMPRESSIBLE_SOLVERS


class FoamCaseProxy:
    def __init__(self, obj):
        obj.Proxy = self
        self.ensure_properties(obj)

    def execute(self, obj):
        pass

    def onDocumentRestored(self, obj):
        self.ensure_properties(obj)

    def ensure_properties(self, obj) -> None:
        def add(ptype, name, group, doc, value=None):
            if hasattr(obj, name):
                return
            obj.addProperty(ptype, name, group, doc, locked=True)
            if value is not None:
                setattr(obj, name, value)

        if not hasattr(obj, "Application"):
            obj.addProperty(
                "App::PropertyEnumeration",
                "Application",
                "Foam",
                "Incompressible OpenFOAM application",
                locked=True,
            )
            obj.Application = list(INCOMPRESSIBLE_SOLVERS)
        if not hasattr(obj, "Turbulence"):
            obj.addProperty(
                "App::PropertyEnumeration",
                "Turbulence",
                "Foam",
                "laminar or RAS model",
                locked=True,
            )
            obj.Turbulence = ["laminar", "kOmegaSST", "kEpsilon"]
        add("App::PropertyFloat", "StartTime", "Foam", "controlDict startTime", 0.0)
        add("App::PropertyFloat", "EndTime", "Foam", "controlDict endTime", 100.0)
        add("App::PropertyFloat", "DeltaT", "Foam", "controlDict deltaT", 1.0)
        add("App::PropertyInteger", "WriteInterval", "Foam", "time-step write interval", 20)
        add("App::PropertyFloat", "Nu", "Foam", "Kinematic viscosity (m^2/s)", 1.0e-5)
        add("App::PropertyIntegerList", "Cells", "Foam", "blockMesh cells in x, y, z", [20, 20, 1])
        add("App::PropertyVector", "InletVelocity", "Foam", "Inlet velocity (m/s)", (1.0, 0.0, 0.0))
        add(
            "App::PropertyLink",
            "Geometry",
            "Foam",
            "Part/PartDesign object whose BoundBox becomes blockMesh (mm → m)",
        )
        add(
            "App::PropertyPath",
            "CasePath",
            "Foam",
            "Directory to write. Empty = <document folder>/<label>",
        )


class FoamCaseView:
    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj):
        pass

    def dumps(self):
        return None

    def loads(self, state):
        return None


def is_foam_case(obj) -> bool:
    return isinstance(getattr(obj, "Proxy", None), FoamCaseProxy)


def spec_from_object(obj) -> FoamCaseSpec:
    bbox = (0.0, 100.0, 0.0, 100.0, 0.0, 10.0)
    geom = getattr(obj, "Geometry", None)
    if geom is not None and hasattr(geom, "Shape"):
        bbox = bbox_mm_from_boundbox(geom.Shape.BoundBox)
    cells = tuple(int(n) for n in obj.Cells)
    if len(cells) != 3:
        cells = (20, 20, 1)
    vel = obj.InletVelocity
    return FoamCaseSpec(
        application=str(obj.Application),
        start_time=float(obj.StartTime),
        end_time=float(obj.EndTime),
        delta_t=float(obj.DeltaT),
        write_interval=int(obj.WriteInterval),
        nu=float(obj.Nu),
        turbulence=str(obj.Turbulence),
        bbox_mm=bbox,
        cells=cells,
        inlet_velocity=(float(vel.x), float(vel.y), float(vel.z)),
    )


def case_directory(obj) -> Path:
    raw = str(getattr(obj, "CasePath", "") or "").strip()
    if raw:
        return Path(raw).expanduser()
    import FreeCAD as App

    doc = obj.Document
    folder = Path(doc.FileName).parent if doc.FileName else Path(App.getUserCachePath())
    return folder / obj.Label


def make_foam_case(name: str = "FoamCase"):
    import FreeCAD as App

    doc = App.ActiveDocument
    if doc is None:
        raise RuntimeError("No active document")
    obj = doc.addObject("App::FeaturePython", name)
    FoamCaseProxy(obj)
    sel = []
    try:
        import FreeCADGui as Gui

        sel = Gui.Selection.getSelection()
        if App.GuiUp and hasattr(obj, "ViewObject") and obj.ViewObject is not None:
            FoamCaseView(obj.ViewObject)
    except Exception:
        pass
    for candidate in sel:
        if hasattr(candidate, "Shape"):
            obj.Geometry = candidate
            break
    doc.recompute()
    return obj


def write_foam_case(obj=None) -> Path:
    import FreeCAD as App

    if obj is None:
        obj = _selected_or_new()
    spec = spec_from_object(obj)
    dest = case_directory(obj)
    write_case(dest, spec)
    if not str(getattr(obj, "CasePath", "") or "").strip():
        obj.CasePath = str(dest)
    App.Console.PrintMessage(f"BtStudio: wrote OpenFOAM case to {dest}\n")
    return dest


def _selected_or_new():
    import FreeCAD as App

    try:
        import FreeCADGui as Gui

        for obj in Gui.Selection.getSelection():
            if is_foam_case(obj):
                return obj
    except Exception:
        pass
    doc = App.ActiveDocument
    if doc is not None:
        for obj in doc.Objects:
            if is_foam_case(obj):
                return obj
    return make_foam_case()
