# SPDX-License-Identifier: LGPL-2.1-or-later

# ***************************************************************************
# *   Copyright (c) 2026 FreeCAD contributors                              *
# *                                                                         *
# *   This file is part of FreeCAD.                                         *
# *                                                                         *
# *   FreeCAD is free software: you can redistribute it and/or modify it    *
# *   under the terms of the GNU Lesser General Public License as           *
# *   published by the Free Software Foundation, either version 2.1 of the  *
# *   License, or (at your option) any later version.                       *
# *                                                                         *
# *   FreeCAD is distributed in the hope that it will be useful, but        *
# *   WITHOUT ANY WARRANTY; without even the implied warranty of            *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU      *
# *   Lesser General Public License for more details.                       *
# *                                                                         *
# *   You should have received a copy of the GNU Lesser General Public      *
# *   License along with FreeCAD. If not, see                               *
# *   <https://www.gnu.org/licenses/>.                                      *
# *                                                                         *
# ***************************************************************************

__title__ = "FEM guided study wizard"
__author__ = "FreeCAD contributors"
__url__ = "https://www.freecad.org"

## @package study_wizard
#  \ingroup FEM
#  \brief Dialog that checks mesh, material, and boundary conditions before solve

import FreeCAD
import FreeCADGui
from FreeCAD import Qt

from PySide import QtGui

from femtools.study_presets import get_study_checklist

CMD_MESH = "FEM_MeshGmshFromShape"
CMD_MATERIAL = "FEM_MaterialSolid"
CMD_RUN = "FEM_SolverRun"


def command_exists(name):
    """Return True if *name* is a registered FreeCADGui command."""
    try:
        return name in FreeCADGui.listCommands()
    except Exception:
        return False


class StudyGuidedWizard(QtGui.QDialog):
    """Checklist dialog for the active FEM analysis."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(Qt.translate("FEM_StudyGuidedWizard", "Guided Study Wizard"))
        self.setObjectName("FEM_StudyGuidedWizard")
        self._status = None
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QtGui.QVBoxLayout(self)

        intro = QtGui.QLabel(
            Qt.translate(
                "FEM_StudyGuidedWizard",
                "Check that the active analysis has a mesh, a material, "
                "and at least one constraint or boundary condition.",
            )
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        grid = QtGui.QGridLayout()
        self._mesh_status = QtGui.QLabel()
        self._material_status = QtGui.QLabel()
        self._constraint_status = QtGui.QLabel()
        self._solver_status = QtGui.QLabel()

        self._mesh_button = QtGui.QPushButton(Qt.translate("FEM_StudyGuidedWizard", "Add mesh"))
        self._material_button = QtGui.QPushButton(
            Qt.translate("FEM_StudyGuidedWizard", "Add material")
        )
        self._mesh_button.setEnabled(command_exists(CMD_MESH))
        self._material_button.setEnabled(command_exists(CMD_MATERIAL))
        self._mesh_button.clicked.connect(self._add_mesh)
        self._material_button.clicked.connect(self._add_material)

        grid.addWidget(self._mesh_status, 0, 0)
        grid.addWidget(self._mesh_button, 0, 1)
        grid.addWidget(self._material_status, 1, 0)
        grid.addWidget(self._material_button, 1, 1)
        grid.addWidget(self._constraint_status, 2, 0)
        grid.addWidget(self._solver_status, 3, 0)
        grid.setColumnStretch(0, 1)
        layout.addLayout(grid)

        self._hint = QtGui.QLabel()
        self._hint.setWordWrap(True)
        layout.addWidget(self._hint)

        buttons = QtGui.QDialogButtonBox()
        self._refresh_button = buttons.addButton(
            Qt.translate("FEM_StudyGuidedWizard", "Refresh"),
            QtGui.QDialogButtonBox.ActionRole,
        )
        self._run_button = buttons.addButton(
            Qt.translate("FEM_StudyGuidedWizard", "Run"),
            QtGui.QDialogButtonBox.AcceptRole,
        )
        buttons.addButton(QtGui.QDialogButtonBox.Close)
        self._refresh_button.clicked.connect(self.refresh)
        self._run_button.clicked.connect(self._run_solver)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def refresh(self):
        import FemGui

        analysis = FemGui.getActiveAnalysis()
        if analysis is None:
            self._status = None
            missing = Qt.translate("FEM_StudyGuidedWizard", "Missing")
            self._set_status_label(self._mesh_status, False, "Mesh", missing)
            self._set_status_label(self._material_status, False, "Material", missing)
            self._set_status_label(self._constraint_status, False, "Constraint / BC", missing)
            self._set_status_label(self._solver_status, False, "Solver", missing)
            self._run_button.setEnabled(False)
            self._hint.setText(
                Qt.translate("FEM_StudyGuidedWizard", "No active analysis. Create one first.")
            )
            return

        self._status = get_study_checklist(analysis)
        self._set_status_label(
            self._mesh_status,
            self._status["has_mesh"],
            "Mesh",
            self._object_names(self._status["meshes"]),
        )
        self._set_status_label(
            self._material_status,
            self._status["has_material"],
            "Material",
            self._object_names(self._status["materials"]),
        )
        self._set_status_label(
            self._constraint_status,
            self._status["has_constraint"],
            "Constraint / BC",
            self._object_names(self._status["constraints"]),
        )
        self._set_status_label(
            self._solver_status,
            self._status["has_solver"],
            "Solver",
            self._object_names(self._status["solvers"]),
        )
        self._run_button.setEnabled(self._status["ready"])
        self._hint.setText(self._hint_text())

    def _set_status_label(self, label, ok, title, detail):
        mark = Qt.translate("FEM_StudyGuidedWizard", "Pass") if ok else Qt.translate(
            "FEM_StudyGuidedWizard", "Missing"
        )
        if detail:
            label.setText(f"{title}: {mark} ({detail})")
        else:
            label.setText(f"{title}: {mark}")
        color = "#2e7d32" if ok else "#c62828"
        label.setStyleSheet(f"color: {color};")

    def _object_names(self, objects):
        return ", ".join(obj.Label for obj in objects)

    def _hint_text(self):
        if self._status is None:
            return ""
        if self._status["ready"]:
            if self._status["has_solver"]:
                return Qt.translate(
                    "FEM_StudyGuidedWizard",
                    "Required items are present. Run uses the existing solver.",
                )
            return Qt.translate(
                "FEM_StudyGuidedWizard",
                "Required items are present, but the analysis has no solver yet.",
            )
        hints = []
        if not self._status["has_mesh"]:
            hints.append(
                Qt.translate(
                    "FEM_StudyGuidedWizard",
                    "Select a shape, then Add mesh (Mesh From Shape by Gmsh).",
                )
            )
        if not self._status["has_material"]:
            hints.append(
                Qt.translate("FEM_StudyGuidedWizard", "Add a solid material and assign properties.")
            )
        if not self._status["has_constraint"]:
            hints.append(
                Qt.translate(
                    "FEM_StudyGuidedWizard",
                    "Add at least one constraint or boundary condition.",
                )
            )
        return " ".join(hints)

    def _add_mesh(self):
        if not command_exists(CMD_MESH):
            return
        if not FreeCADGui.Selection.getSelection():
            QtGui.QMessageBox.information(
                self,
                Qt.translate("FEM_StudyGuidedWizard", "Select a shape"),
                Qt.translate(
                    "FEM_StudyGuidedWizard",
                    "Select a part or face first, then click Add mesh.",
                ),
            )
            return
        self.accept()
        FreeCADGui.runCommand(CMD_MESH)

    def _add_material(self):
        if not command_exists(CMD_MATERIAL):
            return
        self.accept()
        FreeCADGui.runCommand(CMD_MATERIAL)

    def _run_solver(self):
        self.refresh()
        if self._status is None or not self._status["ready"]:
            self._run_button.setEnabled(False)
            return
        solvers = self._status["solvers"]
        if not solvers:
            QtGui.QMessageBox.warning(
                self,
                Qt.translate("FEM_StudyGuidedWizard", "No solver"),
                Qt.translate(
                    "FEM_StudyGuidedWizard",
                    "Add a solver to the analysis before running.",
                ),
            )
            return
        self.accept()
        solver = solvers[0]
        if command_exists(CMD_RUN):
            FreeCADGui.Selection.clearSelection()
            FreeCADGui.Selection.addSelection(solver)
            FreeCADGui.runCommand(CMD_RUN)
            return
        from femsolver.run import run_fem_solver

        run_fem_solver(solver)
        FreeCAD.ActiveDocument.recompute()
