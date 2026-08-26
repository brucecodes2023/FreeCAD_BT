# SPDX-License-Identifier: LGPL-2.1-or-later

"""Split Combo View and park Tasks as a tabbed left/right sidebar (or float it)."""

from __future__ import annotations

from .qtutil import app_gui, param_group, qt


def _docks():
    _, Gui = app_gui()
    QtCore, QtGui, QtWidgets = qt()
    mw = Gui.getMainWindow()
    return mw, list(mw.findChildren(QtWidgets.QDockWidget)), QtCore, QtWidgets


def _match(dw, names: tuple[str, ...]) -> bool:
    title = (dw.windowTitle() or "").lower()
    obj = (dw.objectName() or "").lower()
    return any(n.lower() in title or n.lower() in obj for n in names)


def apply_task_sidebar(side: str = "right") -> None:
    studio = param_group()
    if not studio.GetBool("TaskSidebar", True):
        return
    mw, docks, QtCore, QtWidgets = _docks()
    area = (
        QtCore.Qt.RightDockWidgetArea
        if side == "right"
        else QtCore.Qt.LeftDockWidgetArea
    )
    tasks = next((d for d in docks if _match(d, ("Tasks", "Task panel", "Std_TaskView"))), None)
    model = next((d for d in docks if _match(d, ("Model", "Tree view", "Combo View"))), None)
    if tasks is None:
        return
    mw.addDockWidget(area, tasks)
    tasks.setFeatures(
        QtWidgets.QDockWidget.DockWidgetMovable
        | QtWidgets.QDockWidget.DockWidgetFloatable
        | QtWidgets.QDockWidget.DockWidgetClosable
    )
    # Tabify with anything already on that side so we get SolidWorks-style tabs.
    same_side = [
        d
        for d in docks
        if d is not tasks
        and mw.dockWidgetArea(d) == area
        and d.isVisible()
        and (d.objectName() or "") != "BtStudioAnalysisWizard"
    ]
    for other in same_side:
        mw.tabifyDockWidget(other, tasks)
        break
    if model is not None and side == "right":
        mw.addDockWidget(QtCore.Qt.LeftDockWidgetArea, model)
    tasks.show()
