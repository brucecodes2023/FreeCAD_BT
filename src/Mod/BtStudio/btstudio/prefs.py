# SPDX-License-Identifier: LGPL-2.1-or-later

"""One-shot preference defaults. Never rewrite a key the user already set."""

from __future__ import annotations

from .core import DESIGN_WORKBENCH_ORDER, merge_workbench_order
from .qtutil import app_gui, param_group


def _set_bool_if_missing(grp, key: str, value: bool) -> None:
    if key not in grp.GetBools():
        grp.SetBool(key, value)


def _set_string_if_missing(grp, key: str, value: str) -> None:
    if key not in grp.GetStrings():
        grp.SetString(key, value)


def apply_defaults(force_order: bool = False) -> None:
    App, Gui = app_gui()
    studio = param_group()

    snap = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Sketcher/Snap")
    _set_bool_if_missing(snap, "Snap", True)
    _set_bool_if_missing(snap, "SnapToGrid", True)
    _set_bool_if_missing(snap, "SnapToObjects", True)

    auto = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Sketcher")
    _set_bool_if_missing(auto, "AutoConstraints", True)

    preview = App.ParamGet("User parameter:BaseApp/Preferences/Mod/PartDesign/Preview")
    _set_bool_if_missing(preview, "ShowTransparentPreview", True)

    # DAG view rebuilds on every new object and can freeze the GUI (Cube, etc.).
    dag = App.ParamGet("User parameter:BaseApp/Preferences/DockWindows/DAGView")
    dag.SetBool("Enabled", False)

    # Combo View is the Model tree. Disabling it hides the tree and hangs
    # Part commands that fit the view after adding a solid.
    combo = App.ParamGet("User parameter:BaseApp/Preferences/DockWindows/ComboView")
    combo.SetBool("Enabled", True)
    studio.SetBool("SplitComboView", False)
    tree = App.ParamGet("User parameter:BaseApp/Preferences/DockWindows/TreeView")
    _set_bool_if_missing(tree, "Enabled", True)

    nav = App.ParamGet("User parameter:BaseApp/Preferences/View")
    # Gesture style already implements pinch-zoom; we layer modifiers in navigation.py.
    if "NavigationStyle" not in nav.GetStrings() and studio.GetBool("ForceGestureNav", False):
        nav.SetString("NavigationStyle", "Gui::GestureNavigationStyle")

    apply_workbench_order(force=force_order)


def apply_workbench_order(force: bool = False) -> None:
    App, _ = app_gui()
    studio = param_group()
    wb = App.ParamGet("User parameter:BaseApp/Preferences/Workbenches")
    if wb.GetString("Ordered", "") and not force and studio.GetBool("WorkbenchOrderApplied", False):
        return
    try:
        import FreeCADGui as Gui

        known = list(Gui.listWorkbenches().keys())
    except Exception:
        known = list(DESIGN_WORKBENCH_ORDER)
    ordered = merge_workbench_order(known, DESIGN_WORKBENCH_ORDER)
    wb.SetString("Ordered", ",".join(ordered))
    studio.SetBool("WorkbenchOrderApplied", True)
