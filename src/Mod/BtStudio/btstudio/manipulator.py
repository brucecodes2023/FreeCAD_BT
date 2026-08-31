# SPDX-License-Identifier: LGPL-2.1-or-later

"""Workbench manipulator: prepend BtStudio commands; drop noisy FEM utility bar."""

from __future__ import annotations


class StudioManipulator:
    def modifyMenuBar(self):
        return [
            {"insert": "BtStudio_NewSketch", "menuItem": "Sketcher_NewSketch", "after": ""},
            {"remove": "Sketcher_NewSketch"},
            {"remove": "PartDesign_NewSketch"},
            {"insert": "BtStudio_InsertDxf", "menuItem": "Sketcher_ValidateSketch", "after": ""},
            {"insert": "BtStudio_DatumPlane", "menuItem": "Sketcher_ValidateSketch", "after": ""},
            {"insert": "BtStudio_History", "menuItem": "PartDesign_Clone", "after": ""},
            {"insert": "BtStudio_ZoomAll", "menuItem": "Std_ViewFitAll", "after": ""},
            {"insert": "BtStudio_ZoomTo", "menuItem": "Std_ViewFitSelection", "after": ""},
            {"insert": "BtStudio_DatumPlane", "menuItem": "PartDesign_Clone", "after": ""},
            {"insert": "BtStudio_FemWizard", "menuItem": "FEM_Analysis", "after": ""},
            {"insert": "BtStudio_FemAutoMesh", "menuItem": "FEM_Analysis", "after": ""},
        ]

    def modifyToolBars(self):
        return [
            {"insert": "BtStudio_NewSketch", "toolItem": "Sketcher_NewSketch"},
            {"insert": "BtStudio_NewSketch", "toolItem": "PartDesign_NewSketch"},
            {"remove": "Sketcher_NewSketch"},
            {"remove": "PartDesign_NewSketch"},
            {"insert": "BtStudio_InsertDxf", "toolItem": "Sketcher_ValidateSketch"},
            {"insert": "BtStudio_History", "toolItem": "PartDesign_Clone"},
            {"insert": "BtStudio_DatumPlane", "toolItem": "BtStudio_NewSketch"},
            {"insert": "BtStudio_FemWizard", "toolItem": "FEM_Analysis"},
            {"insert": "BtStudio_FemAutoMesh", "toolItem": "FEM_Analysis"},
        ]
