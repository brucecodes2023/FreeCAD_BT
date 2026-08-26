# SPDX-License-Identifier: LGPL-2.1-or-later

"""Always-visible BtStudio toolbar + Analysis menu (Ribbon hides custom bars)."""

from __future__ import annotations

from .qtutil import app_gui, qt

_TOOLBAR = None

_BUTTONS = (
    ("BtStudio_FoamWizard", "Analysis walkthrough"),
    ("BtStudio_FoamNewCase", "New FoamCase"),
    ("BtStudio_FoamWriteCase", "Write OpenFOAM case"),
    ("BtStudio_FemWizard", "FEM walkthrough"),
)


def install_studio_chrome() -> None:
    install_studio_toolbar()
    install_analysis_menu()


def install_studio_toolbar() -> None:
    global _TOOLBAR
    _, Gui = app_gui()
    QtCore, QtGui, QtWidgets = qt()
    mw = Gui.getMainWindow()
    existing = mw.findChild(QtWidgets.QToolBar, "BtStudioToolbar")
    if existing is not None:
        _TOOLBAR = existing
        existing.setVisible(True)
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


def install_analysis_menu() -> None:
    """Native macOS / Qt menu that survives Ribbon hiding the toolbar."""
    _, Gui = app_gui()
    QtCore, QtGui, QtWidgets = qt()
    mw = Gui.getMainWindow()
    mb = mw.menuBar()
    if mb is None:
        return
    for action in mb.actions():
        text = (action.text() or "").replace("&", "")
        if text == "Analysis":
            return
    menu = mb.addMenu("&Analysis")
    menu.setObjectName("BtStudioAnalysisMenu")
    for command, label in _BUTTONS:
        act = menu.addAction(label)
        act.triggered.connect(lambda _checked=False, name=command: _run(name))


def _run(name: str) -> None:
    _, Gui = app_gui()
    try:
        Gui.runCommand(name)
    except Exception as exc:
        try:
            Gui.getMainWindow().statusBar().showMessage(str(exc), 8000)
        except Exception:
            pass
