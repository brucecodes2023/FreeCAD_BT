# SPDX-License-Identifier: LGPL-2.1-or-later

"""ANSYS/SolidWorks-style property table for the current selection."""

from __future__ import annotations

from .qtutil import app_gui, qt

_DOCK = None


def _rows_for(obj) -> list[tuple[str, str]]:
    rows = [("Name", obj.Name), ("Label", obj.Label), ("Type", obj.TypeId)]
    for name in getattr(obj, "PropertiesList", []) or []:
        try:
            val = obj.getPropertyByName(name)
        except Exception:
            continue
        if name in ("Name", "Label", "ExpressionEngine", "Visibility"):
            continue
        text = str(val)
        if len(text) > 120:
            text = text[:117] + "..."
        rows.append((name, text))
    return rows


class PropertyDock:
    def __init__(self):
        QtCore, QtGui, QtWidgets = qt()
        self.widget = QtWidgets.QDockWidget("Component data")
        self.widget.setObjectName("BtStudioProperties")
        self.table = QtWidgets.QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Property", "Value"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.widget.setWidget(self.table)
        self._obs = _SelectionObs(self)

    def attach(self) -> None:
        _, Gui = app_gui()
        QtCore, QtGui, QtWidgets = qt()
        mw = Gui.getMainWindow()
        mw.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.widget)
        try:
            Gui.Selection.addObserver(self._obs)
        except Exception:
            pass
        self.widget.show()
        self.refresh()

    def refresh(self) -> None:
        _, Gui = app_gui()
        QtCore, QtGui, QtWidgets = qt()
        sel = Gui.Selection.getSelection()
        self.table.setRowCount(0)
        if not sel:
            return
        rows = _rows_for(sel[0])
        self.table.setRowCount(len(rows))
        for i, (k, v) in enumerate(rows):
            self.table.setItem(i, 0, QtWidgets.QTableWidgetItem(k))
            self.table.setItem(i, 1, QtWidgets.QTableWidgetItem(v))


class _SelectionObs:
    def __init__(self, dock: PropertyDock):
        self.dock = dock

    def addSelection(self, *args) -> None:
        self.dock.refresh()

    def removeSelection(self, *args) -> None:
        self.dock.refresh()

    def setSelection(self, *args) -> None:
        self.dock.refresh()

    def clearSelection(self, *args) -> None:
        self.dock.refresh()


def show_properties() -> None:
    global _DOCK
    if _DOCK is None:
        _DOCK = PropertyDock()
        _DOCK.attach()
    else:
        _DOCK.widget.show()
        _DOCK.refresh()
