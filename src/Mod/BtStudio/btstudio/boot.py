# SPDX-License-Identifier: LGPL-2.1-or-later

"""Deferred GUI startup for the BtStudio overlay."""

from __future__ import annotations

_MANIP = None


def _patch_viewfit() -> None:
    """Part_Box still calls Gui.SendMsgToActiveView('ViewFit'); that is deprecated."""
    try:
        import FreeCADGui as Gui
    except Exception:
        return
    if getattr(Gui, "_btstudio_view_patched", False):
        return
    orig = getattr(Gui, "SendMsgToActiveView", None)
    if orig is None:
        return

    def send(name, suppress=False):
        if name == "ViewFit":
            try:
                Gui.ActiveDocument.ActiveView.fitAll()
                return
            except Exception:
                pass
        try:
            return orig(name, suppress)
        except TypeError:
            return orig(name)

    Gui.SendMsgToActiveView = send
    Gui._btstudio_view_patched = True


def startup() -> None:
    import FreeCAD as App

    from .commands import register
    from .mac_chrome import apply_mac_chrome, dismiss_open_menus
    from .manipulator import StudioManipulator
    from .navigation import install_navigation
    from .prefs import apply_defaults
    from .task_sidebar import apply_task_sidebar
    from .layout import apply_studio_layout, clamp_windows_to_screens

    from .studio_toolbar import install_studio_toolbar

    register()
    apply_defaults()
    apply_mac_chrome()
    apply_task_sidebar("right")
    apply_studio_layout()
    install_navigation()
    _patch_viewfit()

    global _MANIP
    try:
        import FreeCADGui as Gui

        _MANIP = StudioManipulator()
        install_studio_toolbar()
        Gui.addWorkbenchManipulator(_MANIP)
        # Do not call reloadActive() here — rebuilding toolbars on startup
        # pops FreeCAD's Menu / File-toolbar overflow.
    except Exception as exc:
        App.Console.PrintWarning(f"BtStudio: manipulator not installed ({exc})\n")

    dismiss_open_menus()
    try:
        from .qtutil import qt

        QtCore, QtGui, QtWidgets = qt()
        QtCore.QTimer.singleShot(0, dismiss_open_menus)
        QtCore.QTimer.singleShot(0, clamp_windows_to_screens)
        QtCore.QTimer.singleShot(400, dismiss_open_menus)
        QtCore.QTimer.singleShot(400, clamp_windows_to_screens)
    except Exception:
        pass

    App.Console.PrintMessage(
        "BtStudio overlay loaded. Analysis walkthrough: BtStudio toolbar "
        "(Structures FEM or Fluids simpleFoam).\n"
    )
