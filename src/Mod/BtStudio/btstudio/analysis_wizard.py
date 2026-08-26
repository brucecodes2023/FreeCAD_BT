# SPDX-License-Identifier: LGPL-2.1-or-later

"""ANSYS-style analysis walkthrough: physics picker + gated next-step Run."""

from __future__ import annotations

from pathlib import Path

from .core import (
    ACTION_CREATE_SAMPLE_CUBE,
    PHYSICS_FLUIDS,
    PHYSICS_STRUCTURES,
    STATE_COMING,
    STATE_CURRENT,
    STATE_LOCKED,
    STATE_PASSED,
    WizardFacts,
    evaluate_wizard,
)
from .qtutil import app_gui, qt

_DOCK = None

_STATE_BADGE = {
    STATE_CURRENT: ("Next", "#1a73e8"),
    STATE_PASSED: ("Done", "#188038"),
    STATE_LOCKED: ("Locked", "#5f6368"),
    STATE_COMING: ("Coming", "#80868b"),
}

_INCOMPRESSIBLE = ("simpleFoam", "pimpleFoam", "potentialFoam")
_TURBULENCE = ("laminar", "kOmegaSST", "kEpsilon")


def create_sample_cube(name: str = "Cube"):
    """Part::Box the designer can pick. Does not call ViewFit (that froze chrome)."""
    import FreeCAD as App

    doc = App.ActiveDocument
    if doc is None:
        doc = App.newDocument("Analysis")
    try:
        import Part  # noqa: F401
    except Exception:
        pass
    obj = doc.addObject("Part::Box", name)
    obj.Length = 100.0
    obj.Width = 100.0
    obj.Height = 100.0
    doc.recompute()
    try:
        import FreeCADGui as Gui

        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(doc.Name, obj.Name)
    except Exception:
        pass
    return obj


def collect_facts(physics: str) -> WizardFacts:
    """Read the active document into WizardFacts (FreeCAD-only; tests skip this)."""
    App, Gui = app_gui()
    doc = App.ActiveDocument
    selection = []
    try:
        selection = list(Gui.Selection.getSelection())
    except Exception:
        selection = []
    names = tuple(
        str(getattr(obj, "Label", None) or getattr(obj, "Name", "") or "") for obj in selection
    )
    has_shape = False
    for obj in selection:
        shape = getattr(obj, "Shape", None)
        if shape is None:
            continue
        try:
            if float(shape.Volume) > 0:
                has_shape = True
                break
        except Exception:
            continue

    has_foam_case = False
    geometry_link_set = False
    case_path = ""
    case_files: tuple[str, ...] | None = None
    has_analysis = False
    has_material = False
    has_constraint = False
    has_mesh = False
    has_solver_run = False
    has_results = False

    if doc is not None:
        for obj in doc.Objects:
            if _is_foam_case(obj):
                has_foam_case = True
                if getattr(obj, "Geometry", None) is not None:
                    geometry_link_set = True
                raw = str(getattr(obj, "CasePath", "") or "").strip()
                if raw:
                    case_path = raw
            tid = str(getattr(obj, "TypeId", "") or "")
            low = tid.lower()
            if "femanalysis" in low or tid == "Fem::FemAnalysis":
                has_analysis = True
            if low.startswith("fem::") and "material" in low:
                has_material = True
            if low.startswith("fem::") and "constraint" in low:
                has_constraint = True
            if low.startswith("fem::") and "mesh" in low:
                has_mesh = True
            if low.startswith("fem::") and "solver" in low:
                if getattr(obj, "Results", None) or getattr(obj, "ResultFiles", None):
                    has_solver_run = True
            if "result" in low or "postpipeline" in low:
                has_results = True
                has_solver_run = True

    if case_path:
        root = Path(case_path)
        found = []
        if (root / "system" / "controlDict").is_file():
            found.append("system/controlDict")
        if (root / "0" / "U").is_file():
            found.append("0/U")
        case_files = tuple(found)

    return WizardFacts(
        physics=physics,
        selection_names=names,
        has_shape=has_shape,
        geometry_link_set=geometry_link_set,
        has_foam_case=has_foam_case,
        case_path=case_path,
        case_files=case_files,
        has_analysis=has_analysis,
        has_material=has_material,
        has_constraint=has_constraint,
        has_mesh=has_mesh,
        has_solver_run=has_solver_run,
        has_results=has_results,
    )


def _is_foam_case(obj) -> bool:
    try:
        from solvers.foam_objects import is_foam_case

        return is_foam_case(obj)
    except Exception:
        proxy = getattr(obj, "Proxy", None)
        return type(proxy).__name__ == "FoamCaseProxy"


def _find_foam_case():
    App, Gui = app_gui()
    try:
        for obj in Gui.Selection.getSelection():
            if _is_foam_case(obj):
                return obj
    except Exception:
        pass
    doc = App.ActiveDocument
    if doc is None:
        return None
    for obj in doc.Objects:
        if _is_foam_case(obj):
            return obj
    return None


class AnalysisWizardDock:
    def __init__(self, physics: str = PHYSICS_FLUIDS):
        QtCore, QtGui, QtWidgets = qt()
        self.physics = physics if physics in (PHYSICS_STRUCTURES, PHYSICS_FLUIDS) else PHYSICS_FLUIDS
        self.widget = QtWidgets.QDockWidget("Analysis walkthrough")
        self.widget.setObjectName("BtStudioAnalysisWizard")
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)

        intro = QtWidgets.QLabel(
            "Work top to bottom. Only the next required step is enabled. "
            "Fluids writes a simpleFoam case tree; it does not spawn blockMesh or the solver."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        phys_row = QtWidgets.QHBoxLayout()
        phys_row.addWidget(QtWidgets.QLabel("Physics:"))
        self.radio_structures = QtWidgets.QRadioButton("Structures (FEM)")
        self.radio_fluids = QtWidgets.QRadioButton("Fluids (simpleFoam)")
        self.radio_structures.toggled.connect(self._physics_toggled)
        self.radio_fluids.toggled.connect(self._physics_toggled)
        phys_row.addWidget(self.radio_structures)
        phys_row.addWidget(self.radio_fluids)
        phys_row.addStretch(1)
        layout.addLayout(phys_row)

        self.output = QtWidgets.QLabel("")
        self.output.setWordWrap(True)
        self.output.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.output.hide()
        layout.addWidget(self.output)

        self.error = QtWidgets.QLabel("")
        self.error.setWordWrap(True)
        self.error.setStyleSheet("color: #c5221f;")
        self.error.hide()
        layout.addWidget(self.error)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        self.steps_host = QtWidgets.QWidget()
        self.steps_layout = QtWidgets.QVBoxLayout(self.steps_host)
        self.steps_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(self.steps_host)
        layout.addWidget(scroll, 1)

        self.settings = QtWidgets.QGroupBox("Solver and boundary conditions")
        settings_l = QtWidgets.QFormLayout(self.settings)
        self.solver = QtWidgets.QComboBox()
        self.solver.addItems(list(_INCOMPRESSIBLE))
        self.turbulence = QtWidgets.QComboBox()
        self.turbulence.addItems(list(_TURBULENCE))
        self.inlet_ux = QtWidgets.QDoubleSpinBox()
        self.inlet_ux.setRange(-1.0e6, 1.0e6)
        self.inlet_ux.setDecimals(3)
        self.inlet_ux.setValue(1.0)
        self.inlet_ux.setSuffix(" m/s")
        settings_l.addRow("Solver", self.solver)
        settings_l.addRow("Turbulence", self.turbulence)
        settings_l.addRow("Inlet Ux", self.inlet_ux)
        hint = QtWidgets.QLabel("Applied when you write the case tree. Mesh/solve stay Coming.")
        hint.setWordWrap(True)
        settings_l.addRow(hint)
        layout.addWidget(self.settings)

        self.docs = QtWidgets.QPushButton("Open architecture / theory")
        self.docs.clicked.connect(self._open_docs)
        layout.addWidget(self.docs)

        self.widget.setWidget(panel)
        self._cards: list[dict] = []
        self._refreshing = False
        self._timer = None
        self._sel_obs = _SelectionObs(self)
        self._doc_obs = _DocumentObs(self)
        self._rebuild_steps()
        self._sync_physics_radios()

    def attach(self) -> None:
        App, Gui = app_gui()
        QtCore, QtGui, QtWidgets = qt()
        mw = Gui.getMainWindow()
        mw.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.widget)
        tasks = [
            d
            for d in mw.findChildren(QtWidgets.QDockWidget)
            if (d.windowTitle() or "").lower().startswith("task")
        ]
        if tasks:
            mw.tabifyDockWidget(tasks[0], self.widget)
        try:
            Gui.Selection.addObserver(self._sel_obs)
        except Exception:
            pass
        try:
            App.addDocumentObserver(self._doc_obs)
        except Exception:
            pass
        self._timer = QtCore.QTimer(self.widget)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()
        self.widget.show()
        self.widget.raise_()
        self.refresh()

    def set_physics(self, physics: str) -> None:
        if physics not in (PHYSICS_STRUCTURES, PHYSICS_FLUIDS):
            return
        if physics == self.physics:
            self.widget.show()
            self.widget.raise_()
            self.refresh()
            return
        self.physics = physics
        self._sync_physics_radios()
        self._rebuild_steps()
        self.widget.show()
        self.widget.raise_()
        self.refresh()

    def _sync_physics_radios(self) -> None:
        self.radio_structures.blockSignals(True)
        self.radio_fluids.blockSignals(True)
        self.radio_structures.setChecked(self.physics == PHYSICS_STRUCTURES)
        self.radio_fluids.setChecked(self.physics == PHYSICS_FLUIDS)
        self.radio_structures.blockSignals(False)
        self.radio_fluids.blockSignals(False)

    def _physics_toggled(self, checked: bool) -> None:
        if not checked:
            return
        physics = PHYSICS_STRUCTURES if self.radio_structures.isChecked() else PHYSICS_FLUIDS
        if physics == self.physics:
            return
        self.physics = physics
        self._rebuild_steps()
        self.refresh()

    def _rebuild_steps(self) -> None:
        QtCore, QtGui, QtWidgets = qt()
        while self.steps_layout.count():
            item = self.steps_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._cards = []
        view = evaluate_wizard(WizardFacts(physics=self.physics))
        for i, step in enumerate(view.steps, start=1):
            box = QtWidgets.QGroupBox()
            v = QtWidgets.QVBoxLayout(box)
            head = QtWidgets.QHBoxLayout()
            title = QtWidgets.QLabel(f"{i}. {step.title}")
            title.setStyleSheet("font-weight: 600;")
            badge = QtWidgets.QLabel("")
            head.addWidget(title)
            head.addStretch(1)
            head.addWidget(badge)
            v.addLayout(head)
            hint = QtWidgets.QLabel(step.hint)
            hint.setWordWrap(True)
            v.addWidget(hint)
            row = QtWidgets.QHBoxLayout()
            btn = QtWidgets.QPushButton(step.run_label)
            btn.clicked.connect(lambda _=False, sid=step.id: self._run_step(sid))
            row.addWidget(btn)
            row.addStretch(1)
            v.addLayout(row)
            self.steps_layout.addWidget(box)
            self._cards.append(
                {
                    "id": step.id,
                    "box": box,
                    "title": title,
                    "badge": badge,
                    "hint": hint,
                    "button": btn,
                    "index": i,
                }
            )
        self.steps_layout.addStretch(1)

    def refresh(self) -> None:
        if self._refreshing:
            return
        if self.widget is None or not self.widget.isVisible():
            return
        self._refreshing = True
        try:
            facts = collect_facts(self.physics)
            view = evaluate_wizard(facts)
            if len(view.steps) != len(self._cards):
                self._rebuild_steps()
            for card, step in zip(self._cards, view.steps):
                card["id"] = step.id
                card["title"].setText(f"{card['index']}. {step.title}")
                card["hint"].setText(step.hint)
                label, color = _STATE_BADGE[step.state]
                card["badge"].setText(label)
                card["badge"].setStyleSheet(f"color: {color}; font-weight: 600;")
                card["button"].setText(step.run_label)
                card["button"].setEnabled(step.run_enabled)
                card["box"].setProperty("wizardState", step.state)
                if step.state == STATE_CURRENT:
                    card["box"].setStyleSheet("QGroupBox { border: 1px solid #1a73e8; margin-top: 6px; }")
                elif step.state == STATE_PASSED:
                    card["box"].setStyleSheet("QGroupBox { border: 1px solid #188038; margin-top: 6px; }")
                else:
                    card["box"].setStyleSheet("QGroupBox { margin-top: 6px; }")
            if view.output_path:
                self.output.setText(f"Wrote case tree:\n{view.output_path}")
                self.output.show()
            else:
                self.output.hide()
            self.settings.setVisible(self.physics == PHYSICS_FLUIDS)
            self.settings.setEnabled(view.foam_settings_enabled)
            if view.foam_settings_enabled:
                self._load_foam_settings()
            self.docs.setText(
                "Open FEM theory guide"
                if self.physics == PHYSICS_STRUCTURES
                else "Open OpenFOAM architecture"
            )
        except Exception as exc:
            self._show_error(str(exc))
        finally:
            self._refreshing = False

    def _load_foam_settings(self) -> None:
        obj = _find_foam_case()
        if obj is None:
            return
        focused = False
        try:
            QtCore, QtGui, QtWidgets = qt()
            w = QtWidgets.QApplication.focusWidget()
            focused = w in (self.solver, self.turbulence, self.inlet_ux)
        except Exception:
            focused = False
        if focused:
            return
        try:
            app = str(obj.Application)
            if app in _INCOMPRESSIBLE:
                self.solver.setCurrentText(app)
        except Exception:
            pass
        try:
            turb = str(obj.Turbulence)
            if turb in _TURBULENCE:
                self.turbulence.setCurrentText(turb)
        except Exception:
            pass
        try:
            vel = obj.InletVelocity
            self.inlet_ux.setValue(float(vel.x))
        except Exception:
            pass

    def _apply_foam_settings(self, obj) -> None:
        try:
            obj.Application = self.solver.currentText()
        except Exception:
            pass
        try:
            obj.Turbulence = self.turbulence.currentText()
        except Exception:
            pass
        try:
            import FreeCAD as App

            obj.InletVelocity = App.Vector(float(self.inlet_ux.value()), 0.0, 0.0)
        except Exception:
            pass

    def _run_step(self, step_id: str) -> None:
        self.error.hide()
        facts = collect_facts(self.physics)
        view = evaluate_wizard(facts)
        step = next((s for s in view.steps if s.id == step_id), None)
        if step is None or not step.run_enabled:
            self._show_error("That step is not the next required action.")
            return
        _, Gui = app_gui()
        try:
            if step.action == ACTION_CREATE_SAMPLE_CUBE:
                create_sample_cube()
            elif step.command == "BtStudio_FoamNewCase":
                from solvers.foam_objects import make_foam_case

                make_foam_case()
            elif step.command == "BtStudio_FoamWriteCase":
                from solvers.foam_objects import write_foam_case

                obj = _find_foam_case()
                if obj is not None:
                    self._apply_foam_settings(obj)
                dest = write_foam_case(obj)
                self.output.setText(f"Wrote case tree:\n{dest}")
                self.output.show()
            elif step.command:
                Gui.runCommand(step.command)
            else:
                raise RuntimeError("This step has no action yet.")
        except Exception as exc:
            self._show_error(str(exc))
            try:
                Gui.getMainWindow().statusBar().showMessage(str(exc), 8000)
            except Exception:
                pass
        self.refresh()

    def _show_error(self, message: str) -> None:
        self.error.setText(message)
        self.error.show()

    def _open_docs(self) -> None:
        import os

        QtCore, QtGui, QtWidgets = qt()
        name = (
            "FEM_THEORY_GUIDE.md"
            if self.physics == PHYSICS_STRUCTURES
            else "OPENFOAM_ARCHITECTURE.md"
        )
        here = os.path.join(os.path.dirname(__file__), "..", "docs", name)
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(os.path.abspath(here)))


class _SelectionObs:
    def __init__(self, dock: AnalysisWizardDock):
        self.dock = dock

    def addSelection(self, *args) -> None:
        self.dock.refresh()

    def removeSelection(self, *args) -> None:
        self.dock.refresh()

    def setSelection(self, *args) -> None:
        self.dock.refresh()

    def clearSelection(self, *args) -> None:
        self.dock.refresh()


class _DocumentObs:
    def __init__(self, dock: AnalysisWizardDock):
        self.dock = dock

    def slotCreatedObject(self, *_args) -> None:
        self.dock.refresh()

    def slotDeletedObject(self, *_args) -> None:
        self.dock.refresh()

    def slotChangedObject(self, obj, prop) -> None:
        if prop in ("Geometry", "CasePath", "Application", "Turbulence", "InletVelocity"):
            self.dock.refresh()

    def slotActivateDocument(self, *_args) -> None:
        self.dock.refresh()


def show_wizard(physics: str | None = None) -> None:
    global _DOCK
    chosen = physics or PHYSICS_FLUIDS
    if _DOCK is None:
        _DOCK = AnalysisWizardDock(chosen)
        _DOCK.attach()
    else:
        _DOCK.set_physics(chosen)
