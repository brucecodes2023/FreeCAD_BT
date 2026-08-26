# SPDX-License-Identifier: LGPL-2.1-or-later

"""Always-visible BtStudio toolbar so OpenFOAM/FEM commands are not FEM-only."""

from __future__ import annotations

from .qtutil import app_gui, qt

_TOOLBAR = None

_BUTTONS = (
    ("BtStudio_FoamWizard", "Analysis walkthrough"),
    ("BtStudio_FoamNewCase", "New FoamCase"),
    ("BtStudio_FoamWriteCase", "Write OpenFOAM case"),
    ("BtStudio_FemWizard", "FEM walkthrough"),
)


def install_studio_toolbar() -> None:
    global _TOOLBAR
    _, Gui = app_gui()
    QtCore, QtGui, QtWidgets = qt()
    mw = Gui.getMainWindow()
    existing = mw.findChild(QtWidgets.QToolBar, "BtStudioToolbar")
    if existing is not None:
        _TOOLBAR = existing
        existing.show()
        return
    tb = QtWidgets.QToolBar("BtStudio", mw)
    tb.setObjectName("BtStudioToolbar")
    tb.setMovable(True)
    for command, label in _BUTTONS:
        action = QtGui.QAction(label, tb)
        action.triggered.connect(lambda _checked=False, name=command: _run(name))
        tb.addAction(action)
    mw.addToolBar(QtCore.Qt.TopToolBarArea, tb)
    tb.show()
    _TOOLBAR = tb


def _run(name: str) -> None:
    _, Gui = app_gui()
    try:
        Gui.runCommand(name)
    except Exception as exc:
        try:
            Gui.getMainWindow().statusBar().showMessage(str(exc), 8000)
        except Exception:
            pass
