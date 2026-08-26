# SPDX-License-Identifier: LGPL-2.1-or-later

"""FreeCAD command registrations for BtStudio."""

from __future__ import annotations


def _resources(text: str, tip: str, pixmap: str = "FEM_Analysis"):
    return {"MenuText": text, "ToolTip": tip, "Pixmap": pixmap}


class CmdNewSketch:
    def GetResources(self):
        return _resources(
            "New Sketch (iso planes)",
            "Isometric view of the model and origin planes. Click a face or XY/XZ/YZ — no dropdown.",
            "Sketcher_NewSketch",
        )

    def IsActive(self):
        import FreeCAD as App

        return App.ActiveDocument is not None

    def Activated(self):
        from .sketch_planes import start_new_sketch

        start_new_sketch()


class CmdFemWizard:
    def GetResources(self):
        return _resources(
            "FEM walkthrough",
            "Analysis walkthrough on Structures: geometry → analysis → material → BCs → mesh → solve.",
            "FEM_Analysis",
        )

    def IsActive(self):
        return True

    def Activated(self):
        from .fem_wizard import show_wizard

        show_wizard()


class CmdFemAutoMesh:
    def GetResources(self):
        return _resources(
            "Auto mesh",
            "Gmsh mesh with h = bounding-box diagonal / 20. Selected faces become MeshRegions (h/4).",
            "FEM_MeshGmshFromShape",
        )

    def IsActive(self):
        import FreeCAD as App

        return App.ActiveDocument is not None

    def Activated(self):
        from .fem_automesh import auto_mesh

        auto_mesh()


class CmdHistory:
    def GetResources(self):
        return _resources(
            "Feature history",
            "Roll a PartDesign Body Tip back like a Fusion timeline. Also enable DAG View.",
        )

    def IsActive(self):
        return True

    def Activated(self):
        from .history_tree import show_history

        show_history()


class CmdProperties:
    def GetResources(self):
        return _resources(
            "Component data table",
            "Spreadsheet-style properties for the selected object (under the tree / right dock).",
        )

    def IsActive(self):
        return True

    def Activated(self):
        from .property_table import show_properties

        show_properties()


class CmdWorkbenchOrder:
    def GetResources(self):
        return _resources(
            "Apply design-flow workbenches",
            "Reorder the workbench selector: Sketch → Part → Part Design → Assembly → FEM → …",
        )

    def IsActive(self):
        return True

    def Activated(self):
        from .prefs import apply_workbench_order

        apply_workbench_order(force=True)


class CmdFoamWizard:
    def GetResources(self):
        return _resources(
            "Analysis walkthrough",
            "Guided right-sidebar: pick Structures or Fluids, then only the next required step is enabled.",
            "FEM_Analysis",
        )

    def IsActive(self):
        return True

    def Activated(self):
        from .foam_wizard import show_wizard

        show_wizard()


class CmdFoamNewCase:
    def GetResources(self):
        return _resources(
            "New FoamCase",
            "Create a FoamCase object. Selected solid becomes the blockMesh bounding box.",
            "Part_Box",
        )

    def IsActive(self):
        import FreeCAD as App

        return App.ActiveDocument is not None

    def Activated(self):
        from solvers.foam_objects import make_foam_case

        make_foam_case()


class CmdFoamWriteCase:
    def GetResources(self):
        return _resources(
            "Write OpenFOAM case",
            "Emit 0/, constant/, system/ for simpleFoam. Does not call blockMesh.",
            "FEM_MeshGmshFromShape",
        )

    def IsActive(self):
        import FreeCAD as App

        return App.ActiveDocument is not None

    def Activated(self):
        from solvers.foam_objects import write_foam_case

        write_foam_case()


class CmdOpenTheory:
    def GetResources(self):
        return _resources("FEM theory guide", "Open the fork FEM theory guide.")

    def IsActive(self):
        return True

    def Activated(self):
        import os
        from .qtutil import qt

        QtCore, QtGui, QtWidgets = qt()
        path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "docs", "FEM_THEORY_GUIDE.md")
        )
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(path))


COMMANDS = {
    "BtStudio_NewSketch": CmdNewSketch,
    "BtStudio_FemWizard": CmdFemWizard,
    "BtStudio_FemAutoMesh": CmdFemAutoMesh,
    "BtStudio_FoamWizard": CmdFoamWizard,
    "BtStudio_FoamNewCase": CmdFoamNewCase,
    "BtStudio_FoamWriteCase": CmdFoamWriteCase,
    "BtStudio_History": CmdHistory,
    "BtStudio_Properties": CmdProperties,
    "BtStudio_WorkbenchOrder": CmdWorkbenchOrder,
    "BtStudio_FemTheory": CmdOpenTheory,
}


def register() -> None:
    import FreeCADGui as Gui

    for name, cls in COMMANDS.items():
        try:
            Gui.addCommand(name, cls())
        except Exception:
            pass
