# SPDX-License-Identifier: LGPL-2.1-or-later

"""Qt + FreeCAD import helpers."""

from __future__ import annotations


def qt():
    try:
        from PySide6 import QtCore, QtGui, QtWidgets
    except ImportError:  # pragma: no cover - FreeCAD PySide2 builds
        from PySide2 import QtCore, QtGui, QtWidgets
    return QtCore, QtGui, QtWidgets


def app_gui():
    import FreeCAD as App
    import FreeCADGui as Gui

    return App, Gui


def param_group(path: str = "User parameter:BaseApp/Preferences/Mod/BtStudio"):
    import FreeCAD as App

    return App.ParamGet(path)
