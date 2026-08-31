# SPDX-License-Identifier: LGPL-2.1-or-later

"""ANSYS-style analysis walkthrough: physics picker + gated next-step Run."""

from __future__ import annotations

from pathlib import Path

from .core import (
    ACTION_CREATE_ANALYSIS,
    ACTION_CREATE_SAMPLE_CUBE,
    ANALYSIS_FLUIDS,
    ANALYSIS_STATIC,
    ANALYSIS_SYSTEMS,
    PHYSICS_FLUIDS,
    PHYSICS_STRUCTURES,
    STATE_COMING,
    STATE_CURRENT,
    STATE_LOCKED,
    STATE_PASSED,
    WizardFacts,
    analysis_system,
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


def collect_facts(physics: str, analysis: str = ANALYSIS_STATIC) -> WizardFacts:
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
        analysis=analysis,
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
    def __init__(self, physics: str = PHYSICS_STRUCTURES, analysis: str = ANALYSIS_STATIC):
        QtCore, QtGui, QtWidgets = qt()
        self.physics = physics if physics in (PHYSICS_STRUCTURES, PHYSICS_FLUIDS) else PHYSICS_STRUCTURES
        self.analysis = analysis if physics == PHYSICS_STRUCTURES else ANALYSIS_FLUIDS
        self.widget = QtWidgets.QDockWidget("Analysis wizard")
        self.widget.setObjectName("BtStudioAnalysisWizard")
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)

        self.tabs = QtWidgets.QTabBar()
        self.tabs.addTab("FEM")
        self.tabs.addTab("Fluids (later)")
        self.tabs.setExpanding(False)
        self.tabs.setToolTip(
            "FEM is the Mechanical-style wizard. Fluids/OpenFOAM will get its own tab."
        )
        self.tabs.currentChanged.connect(self._tab_changed)
        layout.addWidget(self.tabs)

        self.intro = QtWidgets.QLabel("")
        self.intro.setWordWrap(True)
        layout.addWidget(self.intro)

        type_row = QtWidgets.QHBoxLayout()
        self.analysis_label = QtWidgets.QLabel("Analysis system:")
        type_row.addWidget(self.analysis_label)
        self.analysis_combo = QtWidgets.QComboBox()
        for spec in ANALYSIS_SYSTEMS:
            if spec["domain"] != PHYSICS_STRUCTURES:
                continue
            label = spec["title"]
            if spec.get("status") == "coming":
                label = f"{label} (coming)"
            self.analysis_combo.addItem(label, spec["id"])
        self.analysis_combo.currentIndexChanged.connect(self._analysis_changed)
        type_row.addWidget(self.analysis_combo, 1)
        layout.addLayout(type_row)

        self.blurb = QtWidgets.QLabel("")
        self.blurb.setWordWrap(True)
        self.blurb.setStyleSheet("color: #5f6368;")
        layout.addWidget(self.blurb)

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

        self.docs = QtWidgets.QPushButton("Open FEM theory guide")
        self.docs.clicked.connect(self._open_docs)
        layout.addWidget(self.docs)

        self.widget.setWidget(panel)
        self._cards: list[dict] = []
        self._refreshing = False
        self._timer = None
        self._sel_obs = _SelectionObs(self)
        self._doc_obs = _DocumentObs(self)
        self._sync_tab()
        self._sync_analysis_combo()
        self._update_copy()
        self._rebuild_steps()

    def attach(self) -> None:
        App, Gui = app_gui()
        QtCore, QtGui, QtWidgets = qt()
        mw = Gui.getMainWindow()
        mw.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.widget)
        # Stay a real right dock. Tabifying with Tasks hid the walkthrough.
        self.widget.setFeatures(
            QtWidgets.QDockWidget.DockWidgetMovable
            | QtWidgets.QDockWidget.DockWidgetFloatable
            | QtWidgets.QDockWidget.DockWidgetClosable
        )
        try:
            self.widget.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)
        except Exception:
            pass
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
        if physics == PHYSICS_FLUIDS:
            self.physics = PHYSICS_FLUIDS
            self.analysis = ANALYSIS_FLUIDS
        else:
            self.physics = PHYSICS_STRUCTURES
            if self.analysis == ANALYSIS_FLUIDS:
                self.analysis = ANALYSIS_STATIC
        self._sync_tab()
        self._sync_analysis_combo()
        self._update_copy()
        self._rebuild_steps()
        self.widget.show()
        self.widget.raise_()
        self.refresh()

    def set_analysis(self, analysis_id: str) -> None:
        try:
            spec = analysis_system(analysis_id)
        except ValueError:
            return
        if spec["domain"] == PHYSICS_FLUIDS:
            self.set_physics(PHYSICS_FLUIDS)
            return
        self.physics = PHYSICS_STRUCTURES
        self.analysis = analysis_id
        self._sync_tab()
        self._sync_analysis_combo()
        self._update_copy()
        self._rebuild_steps()
        self.widget.show()
        self.widget.raise_()
        self.refresh()

    def _sync_tab(self) -> None:
        self.tabs.blockSignals(True)
        self.tabs.setCurrentIndex(1 if self.physics == PHYSICS_FLUIDS else 0)
        self.tabs.blockSignals(False)
        self.analysis_combo.setVisible(self.physics == PHYSICS_STRUCTURES)
        self.analysis_label.setVisible(self.physics == PHYSICS_STRUCTURES)

    def _sync_analysis_combo(self) -> None:
        if self.physics != PHYSICS_STRUCTURES:
            return
        self.analysis_combo.blockSignals(True)
        idx = self.analysis_combo.findData(self.analysis)
        if idx < 0:
            idx = self.analysis_combo.findData(ANALYSIS_STATIC)
            self.analysis = ANALYSIS_STATIC
        self.analysis_combo.setCurrentIndex(max(idx, 0))
        self.analysis_combo.blockSignals(False)

    def _tab_changed(self, index: int) -> None:
        physics = PHYSICS_FLUIDS if index == 1 else PHYSICS_STRUCTURES
        if physics == self.physics:
            return
        self.set_physics(physics)

    def _analysis_changed(self, _index: int) -> None:
        analysis_id = self.analysis_combo.currentData()
        if not analysis_id or analysis_id == self.analysis:
            return
        self.set_analysis(str(analysis_id))

    def _update_copy(self) -> None:
        if self.physics == PHYSICS_FLUIDS:
            self.intro.setText(
                "Fluids will become its own tab. For now this writes a simpleFoam case "
                "tree; it does not spawn blockMesh or the solver."
            )
            self.blurb.setText(analysis_system(ANALYSIS_FLUIDS)["blurb"])
            self.docs.setText("Open OpenFOAM architecture")
            return
        spec = analysis_system(self.analysis)
        self.intro.setText(
            "ANSYS Mechanical-style walkthrough. Pick an analysis system, then work "
            "top to bottom. Only the next required step is enabled."
        )
        self.blurb.setText(f"{spec['ansys']}: {spec['blurb']}")
        self.docs.setText("Open FEM theory guide")

    def _rebuild_steps(self) -> None:
        QtCore, QtGui, QtWidgets = qt()
        while self.steps_layout.count():
            item = self.steps_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._cards = []
        view = evaluate_wizard(WizardFacts(physics=self.physics, analysis=self.analysis))
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
            facts = collect_facts(self.physics, self.analysis)
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
        facts = collect_facts(self.physics, self.analysis)
        view = evaluate_wizard(facts)
        step = next((s for s in view.steps if s.id == step_id), None)
        if step is None or not step.run_enabled:
            self._show_error("That step is not the next required action.")
            return
        _, Gui = app_gui()
        try:
            if step.action == ACTION_CREATE_SAMPLE_CUBE:
                create_sample_cube()
            elif step.action == ACTION_CREATE_ANALYSIS:
                from .fem_setup import create_analysis_container

                create_analysis_container(self.analysis)
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


def _dock_alive(dock) -> bool:
    if dock is None:
        return False
    widget = getattr(dock, "widget", None)
    if widget is None:
        return False
    try:
        widget.objectName()
    except Exception:
        return False
    return True


def show_wizard(physics: str | None = None, analysis: str | None = None) -> None:
    """Open or re-show the walkthrough. Closing the dock must not lose it."""
    global _DOCK
    chosen_physics = physics or PHYSICS_STRUCTURES
    chosen_analysis = analysis or (
        ANALYSIS_FLUIDS if chosen_physics == PHYSICS_FLUIDS else ANALYSIS_STATIC
    )
    if not _dock_alive(_DOCK):
        _DOCK = AnalysisWizardDock(chosen_physics, chosen_analysis)
        _DOCK.attach()
        return
    if chosen_physics == PHYSICS_FLUIDS:
        _DOCK.set_physics(PHYSICS_FLUIDS)
    else:
        _DOCK.set_analysis(chosen_analysis)
    widget = _DOCK.widget
    try:
        _, Gui = app_gui()
        QtCore, QtGui, QtWidgets = qt()
        mw = Gui.getMainWindow()
        mw.addDockWidget(QtCore.Qt.RightDockWidgetArea, widget)
    except Exception:
        pass
    widget.setVisible(True)
    widget.show()
    widget.raise_()
