# SPDX-License-Identifier: LGPL-2.1-or-later

"""Keep macOS traffic lights (red / yellow / green) in the top-left.

Ribbon UI starts FreeCAD with CustomizeWindowHint ("loaded without titlebar"),
which strips the native NSWindow buttons. An earlier overlay then went
frameless and hid the Cocoa lights — that is the flash-then-gone race.

This module only restores a normal titled window and unhides the system
buttons. It never uses Qt.FramelessWindowHint and never hides Cocoa lights.
"""

from __future__ import annotations

import ctypes
import sys
from ctypes import CFUNCTYPE, c_bool, c_char_p, c_ulong, c_void_p

from .core import safe_named_attr
from .qtutil import app_gui, qt

# NSWindowStyleMask
_NS_TITLED = 1 << 0
_NS_CLOSABLE = 1 << 1
_NS_MINIATURIZABLE = 1 << 2
_NS_RESIZABLE = 1 << 3
_NS_FULL_SIZE_CONTENT = 1 << 15
_NS_NATIVE_MASK = _NS_TITLED | _NS_CLOSABLE | _NS_MINIATURIZABLE | _NS_RESIZABLE

_NS_CLOSE = 0
_NS_MINIATURIZE = 1
_NS_ZOOM = 2

_FILTER = None
_OBJC = None
_MacChromeFilter = None
_RESTORED_FLAGS = False
_LOGGED = False
_POLL = None
_POLL_TICKS = 0


def apply_mac_chrome() -> None:
    if sys.platform != "darwin":
        return
    _, Gui = app_gui()
    QtCore, QtGui, QtWidgets = qt()
    mw = Gui.getMainWindow()

    _disarm_ribbon_hide_titlebar()
    try:
        mb = mw.menuBar()
        if mb is not None:
            mb.setNativeMenuBar(True)
            mb.setVisible(True)
    except Exception:
        pass
    try:
        mw.setUnifiedTitleAndToolBarOnMac(False)
    except Exception:
        pass

    _remove_fake_chrome(mw, QtWidgets)
    _restore_qt_titlebar(mw, QtCore)
    _restore_cocoa_lights(mw)
    try:
        _strip_old_style_chrome(mw, QtWidgets)
    except Exception:
        pass
    _bind_filter(mw)
    _start_poll()
    _log_once()


def dismiss_open_menus() -> None:
    """Hide any QMenu left open by a toolbar rebuild."""
    QtCore, QtGui, QtWidgets = qt()
    app = QtWidgets.QApplication.instance()
    if app is None:
        return
    for widget in app.topLevelWidgets():
        if isinstance(widget, QtWidgets.QMenu) and widget.isVisible():
            widget.hide()
            widget.close()
    _, Gui = app_gui()
    try:
        mw = Gui.getMainWindow()
        for btn in mw.findChildren(QtWidgets.QToolButton):
            text = (btn.text() or btn.objectName() or "").lower()
            if text in {"menu", "&menu"} or btn.objectName() in {"qt_toolbar_ext_button"}:
                menu = btn.menu()
                if menu is not None:
                    menu.hide()
                btn.setDown(False)
                btn.setChecked(False)
    except Exception:
        pass


def _log_once() -> None:
    global _LOGGED
    if _LOGGED:
        return
    _LOGGED = True
    try:
        import FreeCAD as App

        App.Console.PrintMessage(
            "BtStudio: restoring native macOS traffic lights (top-left).\n"
        )
    except Exception:
        pass


def _disarm_ribbon_hide_titlebar() -> None:
    """Stop Ribbon UI from treating the FreeCAD title bar as hidden."""
    try:
        import FreeCAD as App

        App.ParamGet("User parameter:BaseApp/Preferences/Mod/FreeCAD-Ribbon").SetBool(
            "Hide_Titlebar_FC", False
        )
    except Exception:
        pass
    for name, mod in list(sys.modules.items()):
        if mod is None:
            continue
        if name == "Parameters_Ribbon" or name.endswith(".Parameters_Ribbon"):
            if hasattr(mod, "HIDE_TITLEBAR_FC"):
                try:
                    mod.HIDE_TITLEBAR_FC = False
                except Exception:
                    pass


def _restore_qt_titlebar(mw, QtCore) -> None:
    """Undo CustomizeWindowHint / FramelessWindowHint. Avoid repeating this —
    setWindowFlags recreates the NSWindow and is what makes lights flash off.
    """
    global _RESTORED_FLAGS
    try:
        flags = int(mw.windowFlags())
        broken = bool(flags & int(QtCore.Qt.FramelessWindowHint)) or bool(
            flags & int(QtCore.Qt.CustomizeWindowHint)
        )
        if _RESTORED_FLAGS or not broken:
            return
        wanted = (
            QtCore.Qt.Window
            | QtCore.Qt.WindowTitleHint
            | QtCore.Qt.WindowSystemMenuHint
            | QtCore.Qt.WindowMinMaxButtonsHint
            | QtCore.Qt.WindowCloseButtonHint
        )
        extra = getattr(QtCore.Qt, "WindowFullscreenButtonHint", None)
        if extra is not None:
            wanted |= extra
        visible = mw.isVisible()
        mw.setWindowFlags(wanted)
        _RESTORED_FLAGS = True
        if visible:
            mw.show()
            mw.raise_()
            mw.activateWindow()
    except Exception:
        pass


def _remove_fake_chrome(mw, QtWidgets) -> None:
    for name in ("BtStudioTitleBar", "BtStudioMacPad"):
        for w in mw.findChildren(QtWidgets.QWidget, name):
            try:
                if isinstance(w, QtWidgets.QToolBar):
                    mw.removeToolBar(w)
            except Exception:
                pass
            w.setParent(None)
            w.deleteLater()


def _strip_old_style_chrome(mw, QtWidgets) -> None:
    """Remove Ribbon's fake Windows min/max/close and duplicate window title.

    Native traffic lights already live in the macOS title bar; the old-style
    buttons on the right of the ribbon are redundant.
    """
    try:
        for restore in mw.findChildren(QtWidgets.QToolButton, "RestoreButton"):
            _hide_window_button_triple(restore, QtWidgets)
    except Exception:
        pass

    try:
        widgets = list(mw.findChildren(QtWidgets.QWidget))
    except Exception:
        return
    for widget in widgets:
        right = safe_named_attr(widget, "rightToolBar")
        if not callable(right):
            continue
        try:
            tb = right()
        except Exception:
            continue
        if tb is None:
            continue
        try:
            restore = tb.findChild(QtWidgets.QToolButton, "RestoreButton")
        except Exception:
            restore = None
        if restore is not None:
            _hide_window_button_triple(restore, QtWidgets)
        title_widget = safe_named_attr(widget, "_titleWidget")
        if title_widget is None:
            continue
        label = safe_named_attr(title_widget, "_titleLabel")
        if label is not None:
            try:
                label.hide()
                label.setText("")
            except Exception:
                pass


def _hide_window_button_triple(restore, QtWidgets) -> None:
    """Hide RestoreButton plus the minimize/close siblings beside it."""
    tb = restore.parent()
    while tb is not None and not isinstance(tb, QtWidgets.QToolBar):
        tb = tb.parent()
    buttons = list(tb.findChildren(QtWidgets.QToolButton)) if tb is not None else []
    if restore in buttons:
        i = buttons.index(restore)
        targets = buttons[max(0, i - 1) : i + 2]
    else:
        targets = [restore]
        parent = restore.parent()
        if parent is not None:
            for sibling in parent.findChildren(QtWidgets.QToolButton):
                if sibling is restore:
                    continue
                try:
                    if abs(sibling.x() - restore.x()) < 80 and abs(sibling.y() - restore.y()) < 12:
                        targets.append(sibling)
                except Exception:
                    pass
    for w in targets:
        try:
            w.hide()
            w.setEnabled(False)
            w.setFixedWidth(0)
        except Exception:
            pass


def _start_poll() -> None:
    """Ribbon rebuilds its right toolbar after first show; keep stripping it."""
    global _POLL, _POLL_TICKS
    QtCore, QtGui, QtWidgets = qt()
    if _POLL is not None:
        return
    _POLL_TICKS = 0
    _POLL = QtCore.QTimer()
    _POLL.setInterval(250)

    def tick():
        global _POLL_TICKS
        _POLL_TICKS += 1
        _reapply_cocoa()
        if _POLL_TICKS >= 40:
            _POLL.stop()

    _POLL.timeout.connect(tick)
    _POLL.start()


def _bind_filter(mw) -> None:
    global _FILTER, _MacChromeFilter
    QtCore, QtGui, QtWidgets = qt()
    if _MacChromeFilter is None:

        class MacChromeFilter(QtCore.QObject):
            def eventFilter(self, obj, event):
                et = event.type()
                if et in (
                    QtCore.QEvent.Show,
                    QtCore.QEvent.WindowActivate,
                    QtCore.QEvent.WinIdChange,
                ):
                    # Cocoa unhide only — do not setWindowFlags here (flicker).
                    QtCore.QTimer.singleShot(0, _reapply_cocoa)
                return False

        _MacChromeFilter = MacChromeFilter
    if _FILTER is None:
        _FILTER = _MacChromeFilter(mw)
        mw.installEventFilter(_FILTER)


def _reapply_cocoa() -> None:
    try:
        _, Gui = app_gui()
        QtCore, QtGui, QtWidgets = qt()
        mw = Gui.getMainWindow()
        flags = int(mw.windowFlags())
        if flags & int(QtCore.Qt.FramelessWindowHint) or flags & int(
            QtCore.Qt.CustomizeWindowHint
        ):
            _restore_qt_titlebar(mw, QtCore)
        _restore_cocoa_lights(mw)
        _strip_old_style_chrome(mw, QtWidgets)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Cocoa NSWindow
# ---------------------------------------------------------------------------


def _objc():
    global _OBJC
    if _OBJC is not None:
        return _OBJC
    lib = ctypes.CDLL("/usr/lib/libobjc.A.dylib")
    lib.sel_registerName.restype = c_void_p
    lib.sel_registerName.argtypes = [c_char_p]
    lib.objc_getClass.restype = c_void_p
    lib.objc_getClass.argtypes = [c_char_p]

    def sel(name: str):
        return lib.sel_registerName(name.encode("utf-8"))

    def msg(restype, argtypes):
        return CFUNCTYPE(restype, *argtypes)(("objc_msgSend", lib))

    _OBJC = {
        "id_id": msg(c_void_p, (c_void_p, c_void_p)),
        "id_id_u": msg(c_void_p, (c_void_p, c_void_p, c_ulong)),
        "void_u": msg(None, (c_void_p, c_void_p, c_ulong)),
        "void_b": msg(None, (c_void_p, c_void_p, c_bool)),
        "u_id": msg(c_ulong, (c_void_p, c_void_p)),
        "b_id": msg(c_bool, (c_void_p, c_void_p)),
        "is_kind": msg(c_bool, (c_void_p, c_void_p, c_void_p)),
        "sel": sel,
        "cls": lambda n: lib.objc_getClass(n.encode("utf-8")),
    }
    return _OBJC


def _nsview(widget) -> int:
    try:
        widget.winId()
        widget.createWinId()
    except Exception:
        pass
    try:
        return int(widget.winId())
    except Exception:
        return 0


def _nswindow(widget) -> int:
    o = _objc()
    view = _nsview(widget)
    if not view:
        return 0
    sel = o["sel"]
    ns_window_cls = o["cls"]("NSWindow")
    if o["is_kind"](view, sel("isKindOfClass:"), ns_window_cls):
        return view
    win = o["id_id"](view, sel("window"))
    return int(win or 0)


def _restore_cocoa_lights(mw) -> bool:
    """Unhide the real red/yellow/green NSWindow buttons."""
    try:
        o = _objc()
        win = _nswindow(mw)
        if not win:
            return False
        sel = o["sel"]
        mask = o["u_id"](win, sel("styleMask"))
        mask = (mask | _NS_NATIVE_MASK) & ~_NS_FULL_SIZE_CONTENT
        o["void_u"](win, sel("setStyleMask:"), mask)
        o["void_b"](win, sel("setTitlebarAppearsTransparent:"), False)
        o["void_u"](win, sel("setTitleVisibility:"), 0)  # NSWindowTitleVisible
        for btn_id in (_NS_CLOSE, _NS_MINIATURIZE, _NS_ZOOM):
            btn = o["id_id_u"](win, sel("standardWindowButton:"), btn_id)
            if btn:
                o["void_b"](btn, sel("setHidden:"), False)
        return True
    except Exception:
        return False
