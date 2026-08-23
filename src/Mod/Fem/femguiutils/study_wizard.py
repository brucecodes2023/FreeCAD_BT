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

from femtools.physics_modules import format_catalog
from femtools.study_presets import get_study_checklist, list_guided_scenarios

CMD_MESH = "FEM_MeshGmshFromShape"
CMD_MATERIAL = "FEM_MaterialSolid"
CMD_RUN = "FEM_SolverRun"
CMD_STATIC = "FEM_CalculiXStaticStudy"
CMD_THERMAL = "FEM_CalculiXThermalStudy"
CMD_FIRST_PRINCIPLES = "FEM_FirstPrinciplesStudy"


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

        # --- Quick-start scenarios (drone / robot structural + thermal) ---
        scenario_box = QtGui.QGroupBox(
            Qt.translate("FEM_StudyGuidedWizard", "Quick-start study (no CFD)")
        )
        scenario_layout = QtGui.QVBoxLayout(scenario_box)
        scenario_hint = QtGui.QLabel(
            Qt.translate(
                "FEM_StudyGuidedWizard",
                "Common drone / robot cases use CalculiX static or thermal presets. "
                "Fluid / propulsion CFD is not available here.",
            )
        )
        scenario_hint.setWordWrap(True)
        scenario_layout.addWidget(scenario_hint)

        row = QtGui.QHBoxLayout()
        self._scenario_combo = QtGui.QComboBox()
        self._scenario_combo.setSizePolicy(
            QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed
        )
        for scenario in list_guided_scenarios():
            self._scenario_combo.addItem(scenario.title, scenario.id)
        self._scenario_button = QtGui.QPushButton(
            Qt.translate("FEM_StudyGuidedWizard", "Create study")
        )
        self._scenario_button.clicked.connect(self._create_scenario)
        row.addWidget(self._scenario_combo)
        row.addWidget(self._scenario_button)
        scenario_layout.addLayout(row)

        self._scenario_detail = QtGui.QLabel()
        self._scenario_detail.setWordWrap(True)
        scenario_layout.addWidget(self._scenario_detail)
        self._scenario_combo.currentIndexChanged.connect(self._update_scenario_detail)
        self._update_scenario_detail()
        layout.addWidget(scenario_box)

        # --- Checklist ---
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

        # --- Registered physics modules (First Principles extensibility) ---
        modules_box = QtGui.QGroupBox(
            Qt.translate("FEM_StudyGuidedWizard", "Registered physics modules")
        )
        modules_layout = QtGui.QVBoxLayout(modules_box)
        modules_intro = QtGui.QLabel(
            Qt.translate(
                "FEM_StudyGuidedWizard",
                "Addons register PDE factories via femtools.physics_modules.register. "
                "First Principles Study attaches selected Elmer equations.",
            )
        )
        modules_intro.setWordWrap(True)
        modules_layout.addWidget(modules_intro)
        self._modules_list = QtGui.QPlainTextEdit()
        self._modules_list.setReadOnly(True)
        self._modules_list.setMaximumHeight(120)
        modules_layout.addWidget(self._modules_list)
        fp_row = QtGui.QHBoxLayout()
        self._first_principles_button = QtGui.QPushButton(
            Qt.translate("FEM_StudyGuidedWizard", "First Principles Study…")
        )
        self._first_principles_button.setEnabled(command_exists(CMD_FIRST_PRINCIPLES))
        self._first_principles_button.clicked.connect(self._run_first_principles)
        fp_row.addWidget(self._first_principles_button)
        fp_row.addStretch()
        modules_layout.addLayout(fp_row)
        layout.addWidget(modules_box)

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

    def _update_scenario_detail(self):
        scenario_id = self._scenario_combo.currentData()
        scenarios = {s.id: s for s in list_guided_scenarios()}
        scenario = scenarios.get(scenario_id)
        if scenario is None:
            self._scenario_detail.setText("")
            return
        self._scenario_detail.setText(
            f"{scenario.description}\n{scenario.next_steps}"
        )

    def _create_scenario(self):
        scenario_id = self._scenario_combo.currentData()
        if not scenario_id:
            return
        # Map to existing toolbar commands when possible (keeps doCommand path).
        scenarios = {s.id: s for s in list_guided_scenarios()}
        scenario = scenarios.get(scenario_id)
        if scenario is None:
            return
        self.accept()
        if scenario.setup == "setup_calculix_static_study" and command_exists(CMD_STATIC):
            FreeCADGui.runCommand(CMD_STATIC)
            return
        if scenario.setup == "setup_calculix_thermal_study" and command_exists(CMD_THERMAL):
            FreeCADGui.runCommand(CMD_THERMAL)
            return
        # Fallback: call preset API directly.
        import FemGui
        from femtools import study_presets

        doc = FreeCAD.ActiveDocument
        if doc is None:
            return
        doc.openTransaction(f"Guided scenario {scenario_id}")
        analysis = FemGui.getActiveAnalysis()
        if analysis is not None and analysis.Document == doc:
            analysis, solver, material, _ = study_presets.setup_guided_scenario(
                doc, scenario_id, analysis
            )
        else:
            analysis, solver, material, _ = study_presets.setup_guided_scenario(
                doc, scenario_id
            )
        FemGui.setActiveAnalysis(analysis)
        doc.commitTransaction()
        doc.recompute()
        QtGui.QMessageBox.information(
            FreeCADGui.getMainWindow(),
            scenario.title,
            f"{scenario.description}\n\n{scenario.next_steps}",
        )

    def _run_first_principles(self):
        if not command_exists(CMD_FIRST_PRINCIPLES):
            return
        self.accept()
        FreeCADGui.runCommand(CMD_FIRST_PRINCIPLES)

    def refresh(self):
        import FemGui

        self._modules_list.setPlainText(format_catalog())

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
