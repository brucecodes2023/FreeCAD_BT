# SPDX-License-Identifier: LGPL-2.1-or-later

"""Put overlay commands on the live FreeCAD-Ribbon panels.

Ribbon builds Part Design from a frozen RibbonStructure.json, so a
workbench-manipulator insert never shows. This injects buttons onto
already-built panels and the quick-access bar. It does not write JSON.
"""

from __future__ import annotations

from .core import safe_named_attr

PD_CATEGORY_HINTS = ("part design", "partdesign")
SKETCH_CATEGORY_HINTS = ("sketcher",)
HELPERS_PANEL_TITLES = ("helpers", "part design helper features")
SKETCH_PANEL_TITLES = ("sketch", "sketcher")
HISTORY_BUTTON = "BtStudio_History"
DATUM_BUTTON = "BtStudio_DatumPlane"
ZOOM_ALL_BUTTON = "BtStudio_ZoomAll"
ZOOM_TO_BUTTON = "BtStudio_ZoomTo"
ZOOM_PANEL_TITLE = "Zoom"

_TAB_HOOKED = False


def ribbon_inject_spec() -> tuple[dict, ...]:
    """Headless description of what the GUI injector adds."""
    return (
        {
            "command": HISTORY_BUTTON,
            "category": "Part Design",
            "panel": "Helpers",
            "size": "large",
        },
        {
            "command": DATUM_BUTTON,
            "category": "Part Design",
            "panel": "Helpers",
            "size": "large",
        },
        {
            "command": DATUM_BUTTON,
            "category": "Sketcher",
            "panel": "Sketch",
            "size": "large",
        },
        {
            "command": ZOOM_ALL_BUTTON,
            "category": "Part Design",
            "panel": "Zoom",
            "size": "large",
        },
        {
            "command": ZOOM_TO_BUTTON,
            "category": "Part Design",
            "panel": "Zoom",
            "size": "large",
        },
        {
            "command": ZOOM_ALL_BUTTON,
            "panel": "quickAccess",
            "size": "small",
        },
        {
            "command": ZOOM_TO_BUTTON,
            "panel": "quickAccess",
            "size": "small",
        },
    )


def install_ribbon_inject() -> None:
    try:
        inject_history_on_part_design()
        inject_datum_plane()
        inject_zoom_tools()
        _hook_tab_changes()
    except Exception:
        pass


def inject_history_on_part_design() -> bool:
    from .qtutil import app_gui, qt

    _App, Gui = app_gui()
    QtCore, QtGui, QtWidgets = qt()
    mw = Gui.getMainWindow()
    ribbon = _ribbon_bar(mw, QtWidgets)
    if ribbon is None:
        return False
    cat = _part_design_category(ribbon)
    if cat is None:
        return False
    panel = _helpers_panel(cat)
    if panel is None:
        return False
    if _panel_has_command(panel, HISTORY_BUTTON):
        return True
    btn = _command_button(
        HISTORY_BUTTON,
        Gui,
        QtCore,
        QtGui,
        QtWidgets,
        tooltip="Roll a PartDesign Body Tip back like a Fusion timeline.",
    )
    if btn is None:
        return False
    add = object.__getattribute__(panel, "addLargeWidget")
    add(btn)
    return True


def inject_datum_plane() -> bool:
    from .qtutil import app_gui, qt

    _App, Gui = app_gui()
    QtCore, QtGui, QtWidgets = qt()
    mw = Gui.getMainWindow()
    ribbon = _ribbon_bar(mw, QtWidgets)
    if ribbon is None:
        return False
    btn_kwargs = dict(
        Gui=Gui,
        QtCore=QtCore,
        QtGui=QtGui,
        QtWidgets=QtWidgets,
        tooltip="Add a datum plane in the active Body. Select a face or XY/XZ/YZ first.",
    )
    ok = False
    for hints, titles in (
        (PD_CATEGORY_HINTS, HELPERS_PANEL_TITLES),
        (SKETCH_CATEGORY_HINTS, SKETCH_PANEL_TITLES),
    ):
        cat = _category_by_hints(ribbon, hints)
        if cat is None:
            continue
        panel = _panel_by_titles(cat, titles)
        if panel is None:
            continue
        if _panel_has_command(panel, DATUM_BUTTON):
            ok = True
            continue
        btn = _command_button(DATUM_BUTTON, **btn_kwargs)
        if btn is None:
            continue
        object.__getattribute__(panel, "addLargeWidget")(btn)
        ok = True
    return ok


def inject_zoom_tools() -> bool:
    from .qtutil import app_gui, qt

    App, Gui = app_gui()
    QtCore, QtGui, QtWidgets = qt()
    mw = Gui.getMainWindow()
    ribbon = _ribbon_bar(mw, QtWidgets)
    if ribbon is None:
        return False
    qa_ok = _inject_zoom_quick_access(ribbon, Gui, QtCore, QtGui, QtWidgets)
    pd_ok = _inject_zoom_panel(ribbon, PD_CATEGORY_HINTS, HELPERS_PANEL_TITLES, App, Gui, QtCore, QtGui, QtWidgets)
    sk_ok = _inject_zoom_panel(ribbon, SKETCH_CATEGORY_HINTS, SKETCH_PANEL_TITLES, App, Gui, QtCore, QtGui, QtWidgets)
    return bool(qa_ok or pd_ok or sk_ok)


def _inject_zoom_quick_access(ribbon, Gui, QtCore, QtGui, QtWidgets) -> bool:
    qa_fn = safe_named_attr(ribbon, "quickAccessToolBar")
    if not callable(qa_fn):
        return False
    try:
        qa = qa_fn()
    except Exception:
        return False
    if qa is None:
        return False
    added = False
    if not _toolbar_has_command(qa, ZOOM_ALL_BUTTON):
        btn = _command_button(
            ZOOM_ALL_BUTTON,
            Gui,
            QtCore,
            QtGui,
            QtWidgets,
            tooltip="Zoom all — fit everything in the 3D view.",
        )
        if btn is not None:
            btn.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
            qa.addWidget(btn)
            added = True
    if not _toolbar_has_command(qa, ZOOM_TO_BUTTON):
        btn = _zoom_to_button(Gui, QtCore, QtGui, QtWidgets)
        if btn is not None:
            btn.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
            qa.addWidget(btn)
            added = True
    return added


def _inject_zoom_panel(ribbon, cat_hints, after_titles, App, Gui, QtCore, QtGui, QtWidgets) -> bool:
    cat = _category_by_hints(ribbon, cat_hints)
    if cat is None:
        return False
    panels = object.__getattribute__(cat, "panels")()
    if not isinstance(panels, dict):
        return False
    panel = None
    for title, existing in panels.items():
        if (title or "").strip().lower() == ZOOM_PANEL_TITLE.lower():
            panel = existing
            break
    if panel is None:
        insert = safe_named_attr(cat, "insertPanel")
        add_panel = safe_named_attr(cat, "addPanel")
        titles = list(panels.keys())
        idx = None
        wanted = {t.lower() for t in after_titles}
        for i, title in enumerate(titles):
            if (title or "").strip().lower() in wanted:
                idx = i
                break
        try:
            if idx is not None and callable(insert):
                panel = insert(idx + 1, ZOOM_PANEL_TITLE, False)
            elif callable(add_panel):
                panel = add_panel(ZOOM_PANEL_TITLE, False)
        except Exception:
            panel = None
    if panel is None:
        return False
    added = False
    if not _panel_has_command(panel, ZOOM_ALL_BUTTON):
        btn = _command_button(
            ZOOM_ALL_BUTTON,
            Gui,
            QtCore,
            QtGui,
            QtWidgets,
            tooltip="Fit everything in the 3D view.",
        )
        if btn is not None:
            object.__getattribute__(panel, "addLargeWidget")(btn)
            added = True
    if not _panel_has_command(panel, ZOOM_TO_BUTTON):
        btn = _zoom_to_button(Gui, QtCore, QtGui, QtWidgets)
        if btn is not None:
            object.__getattribute__(panel, "addLargeWidget")(btn)
            added = True
    return added


def _ribbon_bar(mw, QtWidgets):
    try:
        widgets = list(mw.findChildren(QtWidgets.QWidget))
    except Exception:
        return None
    for widget in widgets:
        if not callable(safe_named_attr(widget, "rightToolBar")):
            continue
        if not callable(safe_named_attr(widget, "categories")):
            continue
        return widget
    return None


def _category_by_hints(ribbon, hints):
    cats = object.__getattribute__(ribbon, "categories")()
    if not isinstance(cats, dict):
        return None
    for title, cat in cats.items():
        on = ""
        fn = safe_named_attr(cat, "objectName")
        if callable(fn):
            try:
                on = fn() or ""
            except Exception:
                on = ""
        blob = f"{title} {on}".lower().replace(" ", "")
        if any(hint.replace(" ", "") in blob for hint in hints):
            return cat
    return None


def _part_design_category(ribbon):
    return _category_by_hints(ribbon, PD_CATEGORY_HINTS)


def _panel_by_titles(cat, titles):
    panels = object.__getattribute__(cat, "panels")()
    if not isinstance(panels, dict):
        return None
    wanted = {t.lower() for t in titles}
    for title, panel in panels.items():
        if (title or "").strip().lower() in wanted:
            return panel
    return None


def _helpers_panel(cat):
    return _panel_by_titles(cat, HELPERS_PANEL_TITLES)


def _panel_has_command(panel, name: str) -> bool:
    widgets_fn = safe_named_attr(panel, "widgets")
    widgets = []
    if callable(widgets_fn):
        try:
            widgets = list(widgets_fn())
        except Exception:
            widgets = []
    for widget in widgets:
        try:
            if object.__getattribute__(widget, "objectName")() == name:
                return True
        except Exception:
            continue
    return False


def _toolbar_has_command(toolbar, name: str) -> bool:
    from .qtutil import qt

    _QtCore, _QtGui, QtWidgets = qt()
    try:
        for btn in toolbar.findChildren(QtWidgets.QToolButton):
            if btn.objectName() == name:
                return True
    except Exception:
        return False
    return False


def _command_button(name, Gui, QtCore, QtGui, QtWidgets, tooltip: str = ""):
    cmd = Gui.Command.get(name)
    if cmd is None:
        return None
    action = None
    try:
        action = cmd.getAction()
    except Exception:
        action = None
    if isinstance(action, (list, tuple)):
        action = action[0] if action else None
    btn = QtWidgets.QToolButton()
    btn.setObjectName(name)
    btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
    btn.setAutoRaise(True)
    if action is not None:
        btn.setDefaultAction(action)
    else:
        btn.setText(name.replace("BtStudio_", "").replace("_", " "))
        btn.clicked.connect(lambda _checked=False, n=name: Gui.runCommand(n))
    if tooltip:
        btn.setToolTip(tooltip)
    return btn


def _zoom_to_button(Gui, QtCore, QtGui, QtWidgets):
    from .zoom_view import _fill_zoom_to_menu

    btn = QtWidgets.QToolButton()
    btn.setObjectName(ZOOM_TO_BUTTON)
    btn.setText("Zoom to…")
    btn.setToolTip("Fit the selection, the active Body, or pick a part/body.")
    btn.setAutoRaise(True)
    btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
    btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)
    try:
        btn.setIcon(Gui.getIcon("zoom-selection"))
    except Exception:
        pass
    menu = QtWidgets.QMenu(btn)

    def _rebuild():
        from .qtutil import app_gui

        app, gui = app_gui()
        _fill_zoom_to_menu(menu, app, gui)

    menu.aboutToShow.connect(_rebuild)
    btn.setMenu(menu)
    return btn


def _hook_tab_changes() -> None:
    global _TAB_HOOKED
    if _TAB_HOOKED:
        return
    from .qtutil import app_gui, qt

    _App, Gui = app_gui()
    QtCore, QtGui, QtWidgets = qt()
    mw = Gui.getMainWindow()
    ribbon = _ribbon_bar(mw, QtWidgets)
    if ribbon is None:
        return
    tab_bar_fn = safe_named_attr(ribbon, "tabBar")
    if not callable(tab_bar_fn):
        return
    try:
        tab_bar = tab_bar_fn()
        tab_bar.currentChanged.connect(lambda _i: install_ribbon_inject())
        _TAB_HOOKED = True
    except Exception:
        pass
