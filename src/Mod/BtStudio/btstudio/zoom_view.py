# SPDX-License-Identifier: LGPL-2.1-or-later

"""Fit the 3D view to everything, the selection, or a picked Body/Part.

Headless helpers live at module top. GUI fit runs from the commands / ribbon.
"""

from __future__ import annotations


def is_zoom_target(
    *,
    type_id: str,
    parent_type_ids: tuple[str, ...] = (),
    volume: float = 0.0,
) -> bool:
    """True for a Body, App::Part, or a free solid (not nested in a Body)."""
    tid = type_id or ""
    if "Origin" in tid or "Sketch" in tid:
        return False
    if "PartDesign::Body" in tid or tid.endswith("::Body"):
        return True
    if tid == "App::Part":
        return True
    if any("Body" in p or p == "App::Part" for p in parent_type_ids):
        return False
    return float(volume or 0.0) > 0.0


def _status(msg: str, ms: int = 6000) -> None:
    try:
        from .qtutil import app_gui

        _, Gui = app_gui()
        Gui.getMainWindow().statusBar().showMessage(msg, ms)
    except Exception:
        pass


def _active_view():
    from .qtutil import app_gui

    _, Gui = app_gui()
    try:
        return Gui.ActiveDocument.ActiveView
    except Exception:
        return None


def _active_body():
    from .qtutil import app_gui

    _, Gui = app_gui()
    try:
        return Gui.ActiveDocument.ActiveView.getActiveObject("pdbody")
    except Exception:
        return None


def zoom_all() -> None:
    view = _active_view()
    if view is None:
        _status("No 3D view to zoom.")
        return
    try:
        view.fitAll()
    except Exception:
        from .qtutil import app_gui

        _, Gui = app_gui()
        Gui.SendMsgToActiveView("ViewFit")


def zoom_selection() -> None:
    from .qtutil import app_gui

    _, Gui = app_gui()
    if not Gui.Selection.getSelection():
        body = _active_body()
        if body is not None:
            zoom_to_object(body)
            return
        _status("Select a part or body, or activate a Body.")
        return
    Gui.SendMsgToActiveView("ViewSelection")


def list_zoom_targets(doc) -> list:
    out = []
    if doc is None:
        return out
    for obj in getattr(doc, "Objects", []) or []:
        parents = tuple(getattr(p, "TypeId", "") for p in (getattr(obj, "InList", None) or []))
        volume = 0.0
        try:
            volume = float(obj.Shape.Volume)
        except Exception:
            volume = 0.0
        if is_zoom_target(
            type_id=getattr(obj, "TypeId", ""),
            parent_type_ids=parents,
            volume=volume,
        ):
            out.append(obj)
    return out


def zoom_to_object(obj) -> None:
    from .qtutil import app_gui

    _, Gui = app_gui()
    if obj is None:
        return
    saved = list(Gui.Selection.getSelection())
    try:
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(obj)
        Gui.SendMsgToActiveView("ViewSelection")
    finally:
        Gui.Selection.clearSelection()
        for sel in saved:
            try:
                Gui.Selection.addSelection(sel)
            except Exception:
                pass
    _status(f"Zoomed to {getattr(obj, 'Label', obj)}")


def show_zoom_to_menu(parent=None) -> None:
    from .qtutil import app_gui, qt

    App, Gui = app_gui()
    QtCore, QtGui, QtWidgets = qt()
    if parent is None:
        parent = Gui.getMainWindow()
    menu = QtWidgets.QMenu(parent)
    _fill_zoom_to_menu(menu, App, Gui)
    menu.exec(QtGui.QCursor.pos())


def _fill_zoom_to_menu(menu, App, Gui) -> None:
    menu.clear()
    act_sel = menu.addAction("Selection")
    act_sel.triggered.connect(zoom_selection)
    act_body = menu.addAction("Active body")
    act_body.triggered.connect(lambda: zoom_to_object(_active_body()) if _active_body() else _status("No active Body."))
    menu.addSeparator()
    doc = getattr(App, "ActiveDocument", None)
    targets = list_zoom_targets(doc)
    if not targets:
        empty = menu.addAction("No parts or bodies in the document")
        empty.setEnabled(False)
        return
    for obj in targets:
        act = menu.addAction(obj.Label)
        act.triggered.connect(lambda _checked=False, o=obj: zoom_to_object(o))
