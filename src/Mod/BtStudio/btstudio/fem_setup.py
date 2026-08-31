# SPDX-License-Identifier: LGPL-2.1-or-later

"""Create a Fem::Analysis + CalculiX solver for the chosen ANSYS-style system."""

from __future__ import annotations

from .core import ANALYSIS_STATIC, analysis_system
from .qtutil import app_gui


def create_analysis_container(analysis_id: str = ANALYSIS_STATIC):
    """New analysis, CalculiX ccx tools solver, AnalysisType from the catalog."""
    spec = analysis_system(analysis_id)
    solver_type = spec.get("solver_type")
    if spec.get("status") != "available" or not solver_type:
        raise RuntimeError(f"{spec['title']} is not available yet.")

    App, Gui = app_gui()
    import ObjectsFem

    doc = App.ActiveDocument
    if doc is None:
        doc = App.newDocument("Analysis")

    analysis = ObjectsFem.makeAnalysis(doc, "Analysis")
    try:
        import FemGui

        FemGui.setActiveAnalysis(analysis)
    except Exception:
        pass

    solver = ObjectsFem.makeSolverCalculiXCcxTools(doc, "SolverCcxTools")
    try:
        solver.AnalysisType = solver_type
    except Exception:
        pass
    try:
        analysis.addObject(solver)
    except Exception:
        pass

    try:
        Gui.activateWorkbench("FemWorkbench")
    except Exception:
        pass

    doc.recompute()
    try:
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(doc.Name, analysis.Name)
    except Exception:
        pass
    return analysis
