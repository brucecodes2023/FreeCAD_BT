# SPDX-License-Identifier: LGPL-2.1-or-later

"""Workbench manipulator: prepend BtStudio commands; drop noisy FEM utility bar."""

from __future__ import annotations


class StudioManipulator:
    def modifyMenuBar(self):
        return [
            {"insert": "BtStudio_NewSketch", "menuItem": "Sketcher_NewSketch", "after": ""},
            {"insert": "BtStudio_FemWizard", "menuItem": "FEM_Analysis", "after": ""},
        ]

    def modifyToolBars(self):
        return [
            {"insert": "BtStudio_NewSketch", "toolItem": "Sketcher_NewSketch"},
            {"insert": "BtStudio_NewSketch", "toolItem": "PartDesign_NewSketch"},
            {"insert": "BtStudio_FemWizard", "toolItem": "FEM_Analysis"},
            {"insert": "BtStudio_FemAutoMesh", "toolItem": "FEM_Analysis"},
        ]
