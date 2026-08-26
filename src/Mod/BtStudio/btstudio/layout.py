# SPDX-License-Identifier: LGPL-2.1-or-later

"""BtStudio window layout.

Left column split: Tree view on top, the property/data table on the bottom as a
tabbed panel (Property/Data + Selection view as dock tabs). Toggle with the
``StudioLayout`` bool in ``BaseApp/Preferences/Mod/BtStudio``.
"""

from __future__ import annotations

from .qtutil import app_gui, param_group, qt


def clamp_windows_to_screens() -> None:
    """Move top-level widgets that restored off-screen (multi-monitor leftover)."""
    QtCore, QtGui, QtWidgets = qt()
    app = QtWidgets.QApplication.instance()
    if app is None:
        return
    screens = app.screens()
    if not screens:
        return
    unions = [s.availableGeometry() for s in screens]
    primary = app.primaryScreen().availableGeometry() if app.primaryScreen() else unions[0]
    for widget in app.topLevelWidgets():
        if not widget.isVisible() or widget.isMinimized():
            continue
        geo = widget.frameGeometry()
        if any(rect.intersects(geo) for rect in unions):
            continue
        widget.move(primary.x() + 24, primary.y() + 24)


def _find(docks, *names):
    for d in docks:
        title = (d.windowTitle() or "").lower()
        obj = (d.objectName() or "").lower()
        if any(n.lower() in title or n.lower() in obj for n in names):
            return d
    return None


def apply_studio_layout() -> None:
    if not param_group().GetBool("StudioLayout", True):
        return

    _, Gui = app_gui()
    QtCore, _QtGui, QtWidgets = qt()
    mw = Gui.getMainWindow()
    if mw is None:
        return
    docks = list(mw.findChildren(QtWidgets.QDockWidget))

    tree = _find(docks, "Tree view")
    prop = _find(docks, "Property view")
    sel = _find(docks, "Selection view")
    if tree is None or prop is None:
        return

    left = QtCore.Qt.LeftDockWidgetArea

    # Both docked in the left column: Tree on top, tables/data on the bottom.
    tree.setFloating(False)
    prop.setFloating(False)
    mw.addDockWidget(left, tree)
    mw.addDockWidget(left, prop)
    mw.splitDockWidget(tree, prop, QtCore.Qt.Vertical)  # prop sits BELOW tree

    # Bottom-left panel is tabbed: Property/Data + Selection view.
    if sel is not None:
        mw.addDockWidget(left, sel)
        mw.tabifyDockWidget(prop, sel)
        sel.show()
        prop.raise_()  # keep the data table as the active tab

    tree.show()
    prop.show()
    clamp_windows_to_screens()

    # Give the tree the top third, tables/data the rest.
    try:
        mw.resizeDocks([tree, prop], [300, 520], QtCore.Qt.Vertical)
    except Exception:
        pass
