# SPDX-License-Identifier: LGPL-2.1-or-later

"""Isometric origin-plane sketch creation (no attachment-mode combo box)."""

from __future__ import annotations

from .qtutil import app_gui, qt


def _attachment(sketch, support, sub: str = "") -> None:
    subtuple = (sub,) if sub else ("",)
    if hasattr(sketch, "AttachmentSupport"):
        sketch.AttachmentSupport = [(support, subtuple)]
    else:
        sketch.Support = [(support, subtuple)]
    sketch.MapMode = "FlatFace"


def _active_body():
    _, Gui = app_gui()
    try:
        return Gui.ActiveDocument.ActiveView.getActiveObject("pdbody")
    except Exception:
        return None


def _show_origin_and_iso() -> None:
    App, Gui = app_gui()
    try:
        Gui.ActiveDocument.ActiveView.viewAxonometric()
        Gui.SendMsgToActiveView("ViewFit")
    except Exception:
        pass
    body = _active_body()
    origin = getattr(body, "Origin", None) if body else None
    if origin is not None:
        try:
            origin.ViewObject.Visibility = True
            for feat in origin.OriginFeatures:
                feat.ViewObject.Visibility = True
        except Exception:
            pass
    doc = App.ActiveDocument
    if doc is None:
        return
    for name in ("XY_Plane", "XZ_Plane", "YZ_Plane"):
        obj = doc.getObject(name)
        if obj is not None:
            try:
                obj.ViewObject.Visibility = True
            except Exception:
                pass


def _plane_by_role(role: str):
    """role in {'XY','XZ','YZ'}."""
    App, _ = app_gui()
    body = _active_body()
    if body is not None and getattr(body, "Origin", None) is not None:
        for feat in body.Origin.OriginFeatures:
            name = feat.Name.upper()
            label = getattr(feat, "Label", "").upper()
            if role in name or role in label or role.replace("_", "") in name:
                return feat
    doc = App.ActiveDocument
    aliases = {
        "XY": ("XY_Plane", "Origin_XY", "DatumPlane"),
        "XZ": ("XZ_Plane", "Origin_XZ"),
        "YZ": ("YZ_Plane", "Origin_YZ"),
    }
    for name in aliases[role]:
        obj = doc.getObject(name) if doc else None
        if obj is not None:
            return obj
    return None


def create_sketch_on(support, sub: str = "") -> object:
    App, Gui = app_gui()
    doc = App.ActiveDocument
    if doc is None:
        raise RuntimeError("No active document")
    body = _active_body()
    sketch = doc.addObject("Sketcher::SketchObject", "Sketch")
    _attachment(sketch, support, sub)
    if body is not None:
        try:
            body.addObject(sketch)
        except Exception:
            pass
    doc.recompute()
    Gui.ActiveDocument.setEdit(sketch.Name)
    return sketch


def create_sketch_on_plane(role: str):
    plane = _plane_by_role(role)
    if plane is None:
        raise RuntimeError(
            f"No {role} origin plane. Create a PartDesign Body or Origin first."
        )
    return create_sketch_on(plane, "")


def create_sketch_from_selection() -> object | None:
    """If a face or plane is already selected, sketch on it (no dialog)."""
    _, Gui = app_gui()
    sel = Gui.Selection.getSelectionEx()
    if not sel:
        return None
    for s in sel:
        if s.SubElementNames:
            for sub in s.SubElementNames:
                if sub.startswith("Face") or sub.startswith("Plane") or not sub:
                    return create_sketch_on(s.Object, sub)
        elif s.Object is not None:
            typ = getattr(s.Object, "TypeId", "")
            if "Plane" in typ or "Datum" in typ or "Origin" in typ:
                return create_sketch_on(s.Object, "")
    return None


class PlanePicker:
    """Non-modal panel: iso view + three origin planes + pick-a-face."""

    def __init__(self):
        QtCore, QtGui, QtWidgets = qt()
        self._Qt = (QtCore, QtGui, QtWidgets)
        self.widget = QtWidgets.QDockWidget("New Sketch")
        self.widget.setObjectName("BtStudioSketchPlanes")
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)
        hint = QtWidgets.QLabel(
            "Isometric view. Pick a face in the 3D view, or an origin plane:"
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)
        for role, title in (("XY", "XY (top)"), ("XZ", "XZ (front)"), ("YZ", "YZ (side)")):
            btn = QtWidgets.QPushButton(title)
            btn.clicked.connect(lambda _=False, r=role: self._on_plane(r))
            layout.addWidget(btn)
        use = QtWidgets.QPushButton("Use selected face")
        use.clicked.connect(self._on_selected)
        layout.addWidget(use)
        cancel = QtWidgets.QPushButton("Cancel")
        cancel.clicked.connect(self.close)
        layout.addWidget(cancel)
        layout.addStretch(1)
        self.widget.setWidget(panel)

    def show(self) -> None:
        _, Gui = app_gui()
        QtCore, QtGui, QtWidgets = self._Qt
        _show_origin_and_iso()
        mw = Gui.getMainWindow()
        mw.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.widget)
        try:
            mw.tabifyDockWidget(
                next(
                    d
                    for d in mw.findChildren(QtWidgets.QDockWidget)
                    if d.objectName() == "Tasks" or d.windowTitle() in ("Tasks", "Task panel")
                ),
                self.widget,
            )
        except StopIteration:
            pass
        self.widget.show()
        self.widget.raise_()

    def close(self) -> None:
        self.widget.close()
        self.widget.deleteLater()

    def _on_plane(self, role: str) -> None:
        _, Gui = app_gui()
        try:
            create_sketch_on_plane(role)
            self.close()
        except Exception as exc:
            Gui.getMainWindow().statusBar().showMessage(str(exc), 8000)

    def _on_selected(self) -> None:
        _, Gui = app_gui()
        obj = create_sketch_from_selection()
        if obj is None:
            Gui.getMainWindow().statusBar().showMessage(
                "Select a face or datum plane first.", 5000
            )
            return
        self.close()


def start_new_sketch() -> None:
    App, Gui = app_gui()
    if App.ActiveDocument is None:
        App.newDocument()
    if create_sketch_from_selection() is not None:
        return
    PlanePicker().show()
