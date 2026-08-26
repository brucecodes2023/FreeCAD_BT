# SPDX-License-Identifier: LGPL-2.1-or-later

"""Qt + FreeCAD import helpers."""

from __future__ import annotations


def qt():
    try:
        from PySide6 import QtCore, QtGui, QtWidgets
    except ImportError:  # pragma: no cover - FreeCAD PySide2 builds
        from PySide2 import QtCore, QtGui, QtWidgets
    return QtCore, QtGui, QtWidgets


def qaction_type():
    """QAction lives in QtGui on PySide6 and QtWidgets on PySide2."""
    QtCore, QtGui, QtWidgets = qt()
    return getattr(QtGui, "QAction", None) or getattr(QtWidgets, "QAction", None)


def app_gui():
    import FreeCAD as App
    import FreeCADGui as Gui

    return App, Gui


def param_group(path: str = "User parameter:BaseApp/Preferences/Mod/BtStudio"):
    import FreeCAD as App

    return App.ParamGet(path)
