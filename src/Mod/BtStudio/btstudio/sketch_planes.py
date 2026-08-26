# SPDX-License-Identifier: LGPL-2.1-or-later

"""Isometric origin-plane sketch creation (no attachment-mode combo box)."""

from __future__ import annotations

from .core import (
    SHADED_SKETCH_DISPLAY_MODE,
    SKETCH_FACE_RGB,
    SKETCH_FACE_TRANSPARENCY,
    STOCK_NEW_SKETCH_COMMANDS,
    is_sketch_support_pick,
    pick_display_mode,
)
from .qtutil import app_gui, qaction_type, qt


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


def _set_view_bool(obj, name: str, value: bool) -> None:
    vo = getattr(obj, "ViewObject", None)
    if vo is None or not hasattr(vo, name):
        return
    try:
        setattr(vo, name, value)
    except Exception:
        pass


def _iter_origin_planes():
    App, _ = app_gui()
    seen = []
    body = _active_body()
    if body is not None and getattr(body, "Origin", None) is not None:
        for feat in body.Origin.OriginFeatures:
            typ = getattr(feat, "TypeId", "")
            if "Plane" in typ or "plane" in getattr(feat, "Label", "").lower():
                seen.append(feat)
    doc = App.ActiveDocument
    if doc is not None:
        for name in ("XY_Plane", "XZ_Plane", "YZ_Plane"):
            obj = doc.getObject(name)
            if obj is not None and obj not in seen:
                seen.append(obj)
    return seen


def grid_line_vertices(size: float, divisions: int = 10):
    """Points and per-line vertex counts for a square grid on Z=0, covering [-size, size]."""
    if size <= 0 or divisions < 1:
        raise ValueError("size and divisions must be positive")
    step = (2.0 * size) / divisions
    points: list[tuple[float, float, float]] = []
    counts: list[int] = []
    for i in range(divisions + 1):
        t = -size + i * step
        points.append((t, -size, 0.0))
        points.append((t, size, 0.0))
        counts.append(2)
        points.append((-size, t, 0.0))
        points.append((size, t, 0.0))
        counts.append(2)
    return points, counts


_GRID_OVERLAYS: list[tuple[object, object]] = []
_DRAFT_GRID_PREV: bool | None = None
_GRID_NODE_NAME = "BtStudioPlaneGrid"


def _datum_plane_size() -> float:
    try:
        App, _ = app_gui()
        grp = App.ParamGet("User parameter:BaseApp/Preferences/View")
        size = grp.GetFloat("DatumPlaneSize", 62.0)
        scale = grp.GetFloat("DatumScale", 100.0) / 100.0
        return max(size * scale, 20.0)
    except Exception:
        return 62.0


def _find_named_child(parent, name: str):
    try:
        n = parent.getNumChildren()
    except Exception:
        return None
    for i in range(n):
        child = parent.getChild(i)
        try:
            if child.getName() == name:
                return child
        except Exception:
            continue
    return None


def _make_coin_grid(size: float, divisions: int = 10, color=(0.45, 0.5, 0.58)):
    from pivy import coin

    points, counts = grid_line_vertices(size, divisions)
    sep = coin.SoSeparator()
    sep.setName(_GRID_NODE_NAME)
    pick = coin.SoPickStyle()
    pick.style.setValue(coin.SoPickStyle.UNPICKABLE)
    light = coin.SoLightModel()
    light.model.setValue(coin.SoLightModel.BASE_COLOR)
    mat = coin.SoMaterial()
    mat.diffuseColor.setValue(color)
    mat.emissiveColor.setValue(color)
    mat.transparency.setValue(0.35)
    style = coin.SoDrawStyle()
    style.lineWidth.setValue(1)
    coords = coin.SoCoordinate3()
    coords.point.setValues(0, len(points), points)
    lines = coin.SoLineSet()
    lines.numVertices.setValues(0, len(counts), counts)
    sep.addChild(pick)
    sep.addChild(light)
    sep.addChild(mat)
    sep.addChild(style)
    sep.addChild(coords)
    sep.addChild(lines)
    return sep


def _attach_grid(parent, node) -> None:
    existing = _find_named_child(parent, _GRID_NODE_NAME)
    if existing is not None:
        return
    parent.addChild(node)
    _GRID_OVERLAYS.append((parent, node))


def hide_plane_grids() -> None:
    """Remove Coin overlays and restore Draft grid visibility."""
    global _DRAFT_GRID_PREV
    while _GRID_OVERLAYS:
        parent, child = _GRID_OVERLAYS.pop()
        try:
            if _find_named_child(parent, _GRID_NODE_NAME) is not None:
                parent.removeChild(child)
        except Exception:
            pass
    if _DRAFT_GRID_PREV is None:
        return
    prev = _DRAFT_GRID_PREV
    _DRAFT_GRID_PREV = None
    try:
        _, Gui = app_gui()
        snapper = getattr(Gui, "Snapper", None)
        grid = getattr(snapper, "grid", None) if snapper is not None else None
        if grid is None:
            return
        if prev:
            return
        if hasattr(grid, "show_always"):
            grid.show_always = False
        if hasattr(grid, "off"):
            grid.off()
    except Exception:
        pass


def _show_draft_grid(plane=None) -> None:
    global _DRAFT_GRID_PREV
    try:
        _, Gui = app_gui()
        snapper = getattr(Gui, "Snapper", None)
        if snapper is None:
            import draftguitools.gui_snapper as gui_snapper

            Gui.Snapper = gui_snapper.Snapper()
            snapper = Gui.Snapper
        import WorkingPlane

        wp = WorkingPlane.get_working_plane()
        if plane is not None and hasattr(plane, "Placement"):
            wp.align_to_placement(plane.Placement)
        elif hasattr(wp, "set_to_top"):
            wp.set_to_top()
        if hasattr(snapper, "setTrackers"):
            snapper.setTrackers()
        grid = getattr(snapper, "grid", None)
        if grid is None:
            return
        if _DRAFT_GRID_PREV is None:
            _DRAFT_GRID_PREV = bool(getattr(grid, "Visible", False))
        if hasattr(grid, "show_always"):
            grid.show_always = True
        if hasattr(grid, "set"):
            grid.set()
        elif hasattr(grid, "on"):
            grid.on()
    except Exception:
        pass


def _attach_origin_plane_grids() -> None:
    size = max(_datum_plane_size(), 50.0)
    attached = False
    for obj in _iter_origin_planes():
        _set_view_bool(obj, "Visibility", True)
        _set_view_bool(obj, "ShowGrid", True)
        _set_view_bool(obj, "ShowOnlyInEditMode", False)
        vo = getattr(obj, "ViewObject", None)
        root = getattr(vo, "RootNode", None) if vo is not None else None
        if root is None:
            continue
        try:
            _attach_grid(root, _make_coin_grid(size))
            attached = True
        except Exception:
            continue
    if attached:
        return
    _attach_world_grids(size)


def _attach_world_grids(size: float) -> None:
    """Fallback: three origin-aligned grids in the active 3D view."""
    import math

    from pivy import coin

    _, Gui = app_gui()
    try:
        view = Gui.ActiveDocument.ActiveView
        sg = view.getSceneGraph()
    except Exception:
        return
    if sg is None:
        return
    group = coin.SoSeparator()
    group.setName(_GRID_NODE_NAME)
    for axis, angle, color in (
        ((0, 0, 1), 0.0, (0.35, 0.45, 0.75)),
        ((1, 0, 0), math.pi / 2, (0.35, 0.65, 0.4)),
        ((0, 1, 0), math.pi / 2, (0.75, 0.4, 0.4)),
    ):
        branch = coin.SoSeparator()
        rot = coin.SoRotation()
        rot.rotation.setValue(coin.SbVec3f(*axis), angle)
        branch.addChild(rot)
        branch.addChild(_make_coin_grid(size, color=color))
        group.addChild(branch)
    _attach_grid(sg, group)


def enable_plane_grids() -> None:
    """Show origin planes and a grid in the 3D view while picking a sketch plane."""
    hide_plane_grids()
    _attach_origin_plane_grids()
    xy = _plane_by_role("XY")
    _show_draft_grid(xy)


def enable_sketch_grid(sketch) -> None:
    """Default the sketch editor grid on (3D view while editing)."""
    _set_view_bool(sketch, "ShowGrid", True)
    _set_view_bool(sketch, "GridAuto", True)


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
    enable_sketch_grid(sketch)
    doc.recompute()
    Gui.ActiveDocument.setEdit(sketch.Name)
    enable_sketch_grid(sketch)
    hide_plane_grids()
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
        obj = s.Object
        if obj is None:
            continue
        tid = getattr(obj, "TypeId", "")
        name = getattr(obj, "Name", "")
        if s.SubElementNames:
            for sub in s.SubElementNames:
                if is_sketch_support_pick(tid, sub, name):
                    return create_sketch_on(obj, sub)
        elif is_sketch_support_pick(tid, "", name):
            return create_sketch_on(obj, "")
    return None


def _ensure_body():
    App, Gui = app_gui()
    body = _active_body()
    if body is not None:
        return body
    doc = App.ActiveDocument
    if doc is None:
        return None
    try:
        body = doc.addObject("PartDesign::Body", "Body")
        try:
            Gui.ActiveDocument.ActiveView.setActiveObject("pdbody", body)
        except Exception:
            pass
        doc.recompute()
        return body
    except Exception:
        try:
            Gui.runCommand("PartDesign_Body", 0)
        except Exception:
            return None
        return _active_body()


def _status(msg: str, ms: int = 8000) -> None:
    try:
        _, Gui = app_gui()
        Gui.getMainWindow().statusBar().showMessage(msg, ms)
    except Exception:
        pass


def shade_closed_sketch(obj) -> None:
    """Show a closed sketch as a filled face, not an edge-only wireframe."""
    if obj is None:
        return
    tid = getattr(obj, "TypeId", "")
    if "Sketch" not in tid:
        return
    vo = getattr(obj, "ViewObject", None)
    if vo is None:
        return
    try:
        modes = list(vo.listDisplayModes() or [])
    except Exception:
        try:
            modes = list(vo.getEnumerationsOfProperty("DisplayMode") or [])
        except Exception:
            modes = []
    mode = pick_display_mode(modes, (SHADED_SKETCH_DISPLAY_MODE, "Shaded"))
    if mode:
        try:
            vo.DisplayMode = mode
        except Exception:
            pass
    try:
        vo.ShapeColor = SKETCH_FACE_RGB
        vo.Transparency = SKETCH_FACE_TRANSPARENCY
    except Exception:
        pass
    try:
        mats = list(vo.ShapeAppearance)
        if mats:
            mats[0].DiffuseColor = SKETCH_FACE_RGB
            vo.ShapeAppearance = mats
    except Exception:
        pass


def shade_solid(obj) -> None:
    if obj is None:
        return
    vo = getattr(obj, "ViewObject", None)
    if vo is None:
        return
    try:
        modes = list(vo.listDisplayModes() or [])
    except Exception:
        try:
            modes = list(vo.getEnumerationsOfProperty("DisplayMode") or [])
        except Exception:
            modes = []
    mode = pick_display_mode(modes)
    if mode:
        try:
            vo.DisplayMode = mode
        except Exception:
            pass
    try:
        vo.Transparency = 0
    except Exception:
        pass


_PICK_OBS = None
_ESC_FILTER = None
_SHADE_OBS = None
_HIJACKED: list = []


class _PlanePickObserver:
    """Click a plane in the 3D view or Origin in the tree — no orientation dialog."""

    def addSelection(self, doc, obj, sub, _pos=None):
        self._consume(doc, obj, sub or "")

    def setSelection(self, *_a):
        self._from_current()

    def removeSelection(self, *_a):
        return

    def clearSelection(self, *_a):
        return

    def _from_current(self) -> None:
        try:
            _, Gui = app_gui()
            for s in Gui.Selection.getSelectionEx():
                if s.Object is None:
                    continue
                subs = s.SubElementNames or [""]
                for sub in subs:
                    if self._consume(
                        s.Document.Name if getattr(s, "Document", None) else "",
                        s.ObjectName,
                        sub or "",
                    ):
                        return
        except Exception:
            return

    def _consume(self, doc, obj_name, sub) -> bool:
        App, Gui = app_gui()
        try:
            document = App.getDocument(doc) if doc else App.ActiveDocument
            obj = document.getObject(obj_name) if document is not None else None
        except Exception:
            return False
        if obj is None:
            return False
        tid = getattr(obj, "TypeId", "")
        if not is_sketch_support_pick(tid, sub or "", obj_name):
            return False
        stop_plane_pick()
        try:
            create_sketch_on(obj, sub or "")
        except Exception as exc:
            _status(str(exc))
        return True


class _EscFilter:
    def eventFilter(self, _obj, event):
        QtCore, QtGui, QtWidgets = qt()
        if event.type() == QtCore.QEvent.KeyPress and event.key() == QtCore.Qt.Key_Escape:
            stop_plane_pick()
            return True
        return False


def stop_plane_pick() -> None:
    global _PICK_OBS, _ESC_FILTER
    hide_plane_grids()
    try:
        _, Gui = app_gui()
        if _PICK_OBS is not None:
            Gui.Selection.removeObserver(_PICK_OBS)
    except Exception:
        pass
    _PICK_OBS = None
    if _ESC_FILTER is not None:
        try:
            QtCore, QtGui, QtWidgets = qt()
            app = QtWidgets.QApplication.instance()
            if app is not None:
                app.removeEventFilter(_ESC_FILTER)
        except Exception:
            pass
        _ESC_FILTER = None


def begin_plane_pick() -> None:
    """Show origin planes and wait for a 3D or tree click."""
    global _PICK_OBS, _ESC_FILTER
    stop_plane_pick()
    _ensure_body()
    _show_origin_and_iso()
    enable_plane_grids()
    _, Gui = app_gui()
    QtCore, QtGui, QtWidgets = qt()
    Gui.Selection.clearSelection()
    obs = _PlanePickObserver()
    Gui.Selection.addObserver(obs)
    _PICK_OBS = obs
    filt = _EscFilter()
    app = QtWidgets.QApplication.instance()
    if app is not None:
        # QObject parent: wrap via Qt so eventFilter is a real QObject
        class _QtEsc(QtCore.QObject):
            def eventFilter(self, obj, event):
                return filt.eventFilter(obj, event)

        qf = _QtEsc(app)
        app.installEventFilter(qf)
        _ESC_FILTER = qf
    _status("Click a plane in the 3D view or Origin in the Model tree. Esc cancels.")


def start_new_sketch() -> None:
    App, Gui = app_gui()
    if App.ActiveDocument is None:
        App.newDocument()
    _ensure_body()
    if create_sketch_from_selection() is not None:
        return
    begin_plane_pick()


class _ShadeObserver:
    def slotResetEdit(self, vp):
        obj = getattr(vp, "Object", None)
        shade_closed_sketch(obj)

    def slotCreatedObject(self, vp):
        obj = getattr(vp, "Object", vp)
        tid = getattr(obj, "TypeId", "")
        if any(n in tid for n in ("Pad", "Pocket", "Revolution", "Extrusion")):
            shade_solid(obj)
            profile = None
            try:
                profile = obj.Profile[0] if getattr(obj, "Profile", None) else None
            except Exception:
                profile = getattr(obj, "Sketch", None)
            shade_closed_sketch(profile)


def install_shade_observer() -> None:
    global _SHADE_OBS
    if _SHADE_OBS is not None:
        return
    _, Gui = app_gui()
    obs = _ShadeObserver()
    try:
        Gui.addDocumentObserver(obs)
        _SHADE_OBS = obs
    except Exception:
        pass


def _hijack_action(act, QtCore) -> None:
    if act.property("btstudio_new_sketch"):
        return
    try:
        act.triggered.disconnect()
    except Exception:
        pass
    act.triggered.connect(lambda *_a: start_new_sketch())
    act.setProperty("btstudio_new_sketch", True)
    _HIJACKED.append(act)


def hijack_stock_new_sketch() -> None:
    """Route stock New Sketch toolbar/menu actions through the in-view picker."""
    try:
        _, Gui = app_gui()
        QtCore, QtGui, QtWidgets = qt()
        mw = Gui.getMainWindow()
        action_type = qaction_type()
        if mw is None or action_type is None:
            return
        for act in mw.findChildren(action_type):
            blob = " ".join(
                [
                    act.objectName() or "",
                    str(act.data() or ""),
                    act.whatsThis() or "",
                ]
            )
            if any(cmd in blob for cmd in STOCK_NEW_SKETCH_COMMANDS):
                _hijack_action(act, QtCore)
            elif any(cmd in blob for cmd in ("PartDesign_Pad", "Part_Extrude")):
                if not act.property("btstudio_shade_profile"):
                    act.triggered.connect(_shade_current_profile)
                    act.setProperty("btstudio_shade_profile", True)
    except Exception:
        pass


def _shade_current_profile(*_a) -> None:
    _, Gui = app_gui()
    try:
        for obj in Gui.Selection.getSelection():
            shade_closed_sketch(obj)
        edit = Gui.ActiveDocument.getInEdit() if Gui.ActiveDocument else None
        if edit is not None:
            shade_closed_sketch(getattr(edit, "Object", None))
    except Exception:
        pass


def install_sketch_hooks() -> None:
    try:
        install_shade_observer()
    except Exception:
        pass
    hijack_stock_new_sketch()
    try:
        QtCore, QtGui, QtWidgets = qt()
        for msec in (800, 1800, 3500):
            QtCore.QTimer.singleShot(msec, hijack_stock_new_sketch)
    except Exception:
        pass
