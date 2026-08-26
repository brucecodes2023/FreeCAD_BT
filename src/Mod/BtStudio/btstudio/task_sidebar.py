# SPDX-License-Identifier: LGPL-2.1-or-later

"""Park Tasks on the right as a compact, resizable sidebar; keep the Model tree on the left.

FreeCAD already has a separate Tasks dock (Std_TaskView). Combo View is the
Model tree + properties — do not disable it or the tree disappears. Ribbon
overlay can swallow docks; we re-dock after it settles.
"""

from __future__ import annotations

from .core import (
    MODEL_DOCK_NAMES,
    TASK_DOCK_NAMES,
    TASK_SIDEBAR_FONT_PT,
    TASK_SIDEBAR_WIDTH_MAX,
    TASK_SIDEBAR_WIDTH_MIN,
    clamp_int,
    clamp_task_sidebar_width,
    match_dock,
    task_sidebar_needed_width,
    task_sidebar_stylesheet,
)
from .qtutil import app_gui, param_group, qt

_WATCHERS: list = []
_QUIT_GUARD = None


def _dismiss_open_task() -> None:
    """Close the active task dialog while MainWindow is still alive.

    TaskDlgAttacher::~TaskDlgAttacher calls getMainWindow()->hideHints()
    without a null check. On quit the Tasks dock destroys that dialog
    after MainWindow is already gone (this == nullptr → SIGSEGV at
    hideHints+0 / FAR 0x28). Dismissing first avoids the crash even
    before a C++ rebuild lands in the binary.
    """
    try:
        _, Gui = app_gui()
        if Gui.getMainWindow() is None:
            return
        ctrl = getattr(Gui, "Control", None)
        if ctrl is not None:
            ctrl.closeDialog()
        mw = Gui.getMainWindow()
        hide = getattr(mw, "hideHint", None) if mw is not None else None
        if callable(hide):
            hide()
    except Exception:
        pass


def install_quit_guard() -> None:
    global _QUIT_GUARD
    if _QUIT_GUARD is not None:
        return
    QtCore, QtGui, QtWidgets = qt()
    _, Gui = app_gui()
    app = QtWidgets.QApplication.instance()
    mw = Gui.getMainWindow()

    class _QuitGuard(QtCore.QObject):
        def eventFilter(self, obj, event):
            if event.type() == QtCore.QEvent.Close:
                _dismiss_open_task()
            return False

    parent = mw if mw is not None else app
    guard = _QuitGuard(parent)
    if mw is not None:
        mw.installEventFilter(guard)
    if app is not None:
        app.aboutToQuit.connect(_dismiss_open_task)
    _QUIT_GUARD = guard


def _docks():
    _, Gui = app_gui()
    QtCore, QtGui, QtWidgets = qt()
    mw = Gui.getMainWindow()
    return mw, list(mw.findChildren(QtWidgets.QDockWidget)), QtCore, QtGui, QtWidgets


def apply_task_sidebar(side: str = "right") -> None:
    studio = param_group()
    if not studio.GetBool("TaskSidebar", True):
        return
    mw, docks, QtCore, QtGui, QtWidgets = _docks()
    task_area = (
        QtCore.Qt.RightDockWidgetArea
        if side == "right"
        else QtCore.Qt.LeftDockWidgetArea
    )
    model_area = (
        QtCore.Qt.LeftDockWidgetArea
        if side == "right"
        else QtCore.Qt.RightDockWidgetArea
    )

    tasks = next(
        (
            d
            for d in docks
            if match_dock(d.windowTitle(), d.objectName(), TASK_DOCK_NAMES)
        ),
        None,
    )
    model = next(
        (
            d
            for d in docks
            if match_dock(d.windowTitle(), d.objectName(), MODEL_DOCK_NAMES)
        ),
        None,
    )
    if tasks is None:
        return

    _unpin_overlay(tasks)
    if mw.dockWidgetArea(tasks) != task_area or tasks.isFloating():
        mw.addDockWidget(task_area, tasks)
    tasks.setFeatures(
        QtWidgets.QDockWidget.DockWidgetMovable
        | QtWidgets.QDockWidget.DockWidgetFloatable
        | QtWidgets.QDockWidget.DockWidgetClosable
    )
    tasks.setAllowedAreas(
        QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea
    )
    tasks.setFloating(False)
    tasks.setMinimumWidth(TASK_SIDEBAR_WIDTH_MIN)
    tasks.setMaximumWidth(TASK_SIDEBAR_WIDTH_MAX)
    tasks.show()
    tasks.raise_()

    if model is not None and model is not tasks:
        mw.addDockWidget(model_area, model)
        model.show()

    # Tabify Tasks with other *panel* docks on that side (not Report/Python).
    skip = {"report view", "python console", "python", "report"}
    same_side = [
        d
        for d in docks
        if d is not tasks
        and mw.dockWidgetArea(d) == task_area
        and d.isVisible()
        and (d.windowTitle() or "").lower() not in skip
        and (d.objectName() or "").lower() not in skip
        and (d.objectName() or "") != "BtStudioAnalysisWizard"
    ]
    for other in same_side:
        if other is model:
            continue
        mw.tabifyDockWidget(other, tasks)
        break
    tasks.raise_()
    _compact_task_dock(tasks)
    _fit_task_width(tasks)
    _watch_task_dock(tasks)


def _unpin_overlay(dock) -> None:
    """If Ribbon/overlay stole the dock, put it back in the main window."""
    try:
        dock.setProperty("fc_overlay", False)
    except Exception:
        pass
    try:
        import FreeCADGui as Gui

        mgr = getattr(Gui, "OverlayManager", None)
        if mgr is None:
            inst = getattr(Gui, "OverlayManager", None)
            mgr = inst.instance() if inst is not None and hasattr(inst, "instance") else inst
        if mgr is not None:
            for meth, args in (
                ("unsetupDockWidget", (dock,)),
                ("toggleOverlay", (dock, False)),
                ("toggle", (dock, False)),
            ):
                if hasattr(mgr, meth):
                    getattr(mgr, meth)(*args)
                    break
    except Exception:
        pass


def _compact_task_dock(dock) -> None:
    """Smaller type and wrapping labels so Attachment forms fit a Fusion-style sidebar."""
    QtCore, QtGui, QtWidgets = qt()
    studio = param_group()
    pt = clamp_int(studio.GetInt("TaskSidebarFontPt", TASK_SIDEBAR_FONT_PT), 8, 14)
    font = dock.font()
    font.setPointSize(pt)
    dock.setFont(font)
    inner = dock.widget()
    target = inner if inner is not None else dock
    target.setFont(font)
    target.setStyleSheet(task_sidebar_stylesheet(pt))
    _compact_task_widgets(target)


def _compact_task_widgets(root) -> None:
    QtCore, QtGui, QtWidgets = qt()
    for label in root.findChildren(QtWidgets.QLabel):
        try:
            label.setWordWrap(True)
        except Exception:
            pass
    for layout in root.findChildren(QtWidgets.QLayout):
        try:
            layout.setContentsMargins(6, 4, 6, 4)
            layout.setSpacing(4)
        except Exception:
            pass
        if isinstance(layout, QtWidgets.QFormLayout):
            try:
                layout.setRowWrapPolicy(QtWidgets.QFormLayout.WrapLongRows)
                layout.setHorizontalSpacing(6)
                layout.setVerticalSpacing(3)
            except Exception:
                pass
        elif isinstance(layout, QtWidgets.QGridLayout):
            try:
                layout.setHorizontalSpacing(4)
                layout.setVerticalSpacing(3)
            except Exception:
                pass


def _content_min_width(dock) -> int:
    QtCore, QtGui, QtWidgets = qt()
    inner = dock.widget() if hasattr(dock, "widget") else dock
    if inner is None:
        inner = dock
    hint = 0
    boxes = [inner]
    try:
        boxes.extend(inner.findChildren(QtWidgets.QGroupBox))
    except Exception:
        pass
    for widget in boxes:
        try:
            hint = max(
                hint,
                int(widget.sizeHint().width()),
                int(widget.minimumSizeHint().width()),
            )
        except Exception:
            continue
    return hint


def _main_window_for(dock):
    QtCore, QtGui, QtWidgets = qt()
    parent = dock.parent()
    while parent is not None and not isinstance(parent, QtWidgets.QMainWindow):
        parent = parent.parent()
    return parent


def _fit_task_width(dock) -> None:
    """Pop the dock out to at least the width of the current task form."""
    QtCore, QtGui, QtWidgets = qt()
    needed = task_sidebar_needed_width(_content_min_width(dock))
    studio = param_group()
    saved = int(studio.GetInt("TaskSidebarWidth", 0) or 0)
    width = clamp_task_sidebar_width(max(dock.width(), saved), needed=needed)
    dock.setMinimumWidth(needed)
    dock.setMaximumWidth(TASK_SIDEBAR_WIDTH_MAX)
    if dock.width() >= width:
        return
    mw = _main_window_for(dock)
    try:
        if mw is not None:
            mw.resizeDocks([dock], [width], QtCore.Qt.Horizontal)
        else:
            dock.resize(width, dock.height())
    except Exception:
        dock.resize(width, dock.height())


def _save_task_width(width: int) -> None:
    if width < TASK_SIDEBAR_WIDTH_MIN:
        return
    param_group().SetInt(
        "TaskSidebarWidth",
        clamp_task_sidebar_width(width),
    )


def _on_task_form_changed(root) -> None:
    _compact_task_widgets(root)
    dock = root
    QtCore, QtGui, QtWidgets = qt()
    while dock is not None and not isinstance(dock, QtWidgets.QDockWidget):
        dock = dock.parent()
    if dock is not None:
        _fit_task_width(dock)


def _watch_task_dock(dock) -> None:
    """Remember drag-resized width and compact widgets when a new task form loads."""
    if dock.property("btstudio_task_watch"):
        return
    QtCore, QtGui, QtWidgets = qt()

    class _Filter(QtCore.QObject):
        def eventFilter(self, obj, event):
            et = event.type()
            if et == QtCore.QEvent.Resize:
                _save_task_width(obj.width())
            elif et == QtCore.QEvent.ChildAdded:
                QtCore.QTimer.singleShot(0, lambda: _on_task_form_changed(obj))
            return False

    watcher = _Filter(dock)
    dock.installEventFilter(watcher)
    widget = dock.widget()
    if widget is not None:
        widget.installEventFilter(watcher)
    dock.setProperty("btstudio_task_watch", True)
    _WATCHERS.append(watcher)


def schedule_task_sidebar(side: str = "right") -> None:
    """Ribbon reshuffles docks after startup; re-apply a few times."""
    QtCore, QtGui, QtWidgets = qt()
    apply_task_sidebar(side)
    install_quit_guard()
    for msec in (400, 1200, 2500):
        QtCore.QTimer.singleShot(msec, lambda s=side: apply_task_sidebar(s))
