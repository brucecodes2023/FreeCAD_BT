# SPDX-License-Identifier: LGPL-2.1-or-later

"""macOS traffic lights in the top-left (red / yellow / green).

FreeCAD's Fusion style paints Windows min / max / close on the *right*.
This overlay goes frameless and draws stoplights on the left so those
right-side buttons are gone. Unified title+toolbar is left off — that
popped the in-window Menu on launch.
"""

from __future__ import annotations

import ctypes
import sys
from ctypes import CFUNCTYPE, c_bool, c_char_p, c_ulong, c_void_p

from .core import TRAFFIC_LIGHT_BAR_HEIGHT, traffic_light_layout
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

_TITLE_BAR = None
_TITLE_TOOLBAR = None
_FILTER = None
_OBJC = None
_TrafficTitleBar = None
_MacChromeFilter = None


def apply_mac_chrome() -> None:
    if sys.platform != "darwin":
        return
    _, Gui = app_gui()
    QtCore, QtGui, QtWidgets = qt()
    mw = Gui.getMainWindow()

    try:
        mb = mw.menuBar()
        if mb is not None:
            mb.setNativeMenuBar(True)
            mb.setVisible(True)
    except Exception:
        pass

    # Real title bar, not fused into the first toolbar (that popped Menu).
    try:
        mw.setUnifiedTitleAndToolBarOnMac(False)
    except Exception:
        pass

    _remove_legacy_pads(mw, QtWidgets)
    _bind_qt_types()
    _install_filter(mw)
    # Fusion paints min/max/close on the right. Replace that chrome now —
    # waiting for native NSWindow lights left those Windows buttons in place.
    _install_custom_title_bar(mw)
    QtCore.QTimer.singleShot(0, lambda: _install_custom_title_bar(mw))
    QtCore.QTimer.singleShot(400, lambda: _install_custom_title_bar(mw))


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


def _ensure_traffic_lights(allow_custom: bool = True) -> None:
    if sys.platform != "darwin":
        return
    _, Gui = app_gui()
    mw = Gui.getMainWindow()
    _install_custom_title_bar(mw)


def _remove_legacy_pads(mw, QtWidgets) -> None:
    for pad in mw.findChildren(QtWidgets.QWidget, "BtStudioMacPad"):
        pad.setParent(None)
        pad.deleteLater()


def _bind_qt_types() -> None:
    global _TrafficTitleBar, _MacChromeFilter
    if _TrafficTitleBar is not None:
        return
    QtCore, QtGui, QtWidgets = qt()

    class MacChromeFilter(QtCore.QObject):
        def eventFilter(self, obj, event):
            if event.type() in (
                QtCore.QEvent.Show,
                QtCore.QEvent.WinIdChange,
            ):
                QtCore.QTimer.singleShot(0, _reapply_custom_title_bar)
            return False

    class TrafficTitleBar(QtWidgets.QWidget):
        _COLORS = {
            "close": (QtGui.QColor(255, 95, 87), QtGui.QColor(224, 68, 62)),
            "min": (QtGui.QColor(255, 189, 46), QtGui.QColor(222, 161, 35)),
            "zoom": (QtGui.QColor(40, 200, 64), QtGui.QColor(26, 171, 41)),
        }
        _INACTIVE = (QtGui.QColor(210, 210, 214), QtGui.QColor(180, 180, 185))

        def __init__(self, host):
            super().__init__(host)
            self._host = host
            self.setObjectName("BtStudioTrafficTitleBar")
            self.setFixedHeight(TRAFFIC_LIGHT_BAR_HEIGHT)
            self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
            self._hover = None
            self.setMouseTracking(True)

        def _rects(self):
            r = self.rect()
            return traffic_light_layout(r.width(), r.height())

        def _hit(self, pos):
            pt = pos.toPoint() if hasattr(pos, "toPoint") else pos
            for name, (x, y, w, h) in self._rects().items():
                if QtCore.QRect(x, y, w, h).contains(pt):
                    return name
            return None

        def paintEvent(self, event):
            p = QtGui.QPainter(self)
            p.setRenderHint(QtGui.QPainter.Antialiasing, True)
            pal = self.palette()
            p.fillRect(self.rect(), pal.color(QtGui.QPalette.Window))

            active = bool(self._host.isActiveWindow())
            rects = self._rects()
            for name, (x, y, w, h) in rects.items():
                fill, stroke = self._COLORS[name] if active else self._INACTIVE
                p.setBrush(fill)
                p.setPen(QtGui.QPen(stroke, 0.8))
                p.drawEllipse(x, y, w, h)
                if self._hover == name and active:
                    p.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 140), 1.2))
                    cx, cy, rr = x + w / 2.0, y + h / 2.0, w * 0.22
                    if name == "close":
                        p.drawLine(cx - rr, cy - rr, cx + rr, cy + rr)
                        p.drawLine(cx + rr, cy - rr, cx - rr, cy + rr)
                    elif name == "min":
                        p.drawLine(cx - rr, cy, cx + rr, cy)
                    else:
                        p.drawLine(cx, cy - rr, cx, cy + rr)
                        p.drawLine(cx - rr, cy, cx + rr, cy)

            p.setPen(pal.color(QtGui.QPalette.WindowText))
            title = self._host.windowTitle() or "FreeCAD"
            zx, zy, zw, zh = rects["zoom"]
            left = zx + zw + 12
            text_rect = QtCore.QRect(
                left, 0, max(self.width() - left - 8, 0), self.height()
            )
            p.drawText(
                text_rect, int(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft), title
            )
            p.end()

        def mouseMoveEvent(self, event):
            pos = event.position() if hasattr(event, "position") else event.pos()
            name = self._hit(pos)
            if name != self._hover:
                self._hover = name
                self.update()
            super().mouseMoveEvent(event)

        def leaveEvent(self, event):
            self._hover = None
            self.update()
            super().leaveEvent(event)

        def mousePressEvent(self, event):
            if event.button() != QtCore.Qt.LeftButton:
                return super().mousePressEvent(event)
            pos = event.position() if hasattr(event, "position") else event.pos()
            name = self._hit(pos)
            if name == "close":
                self._host.close()
                return
            if name == "min":
                self._host.showMinimized()
                return
            if name == "zoom":
                if self._host.isMaximized():
                    self._host.showNormal()
                else:
                    self._host.showMaximized()
                return
            wh = self._host.windowHandle()
            if wh is not None:
                try:
                    wh.startSystemMove()
                    return
                except Exception:
                    pass
            super().mousePressEvent(event)

        def mouseDoubleClickEvent(self, event):
            if event.button() != QtCore.Qt.LeftButton:
                return super().mouseDoubleClickEvent(event)
            pos = event.position() if hasattr(event, "position") else event.pos()
            if self._hit(pos) is None:
                if self._host.isMaximized():
                    self._host.showNormal()
                else:
                    self._host.showMaximized()
                return
            super().mouseDoubleClickEvent(event)

    _TrafficTitleBar = TrafficTitleBar
    _MacChromeFilter = MacChromeFilter


def _reapply_custom_title_bar() -> None:
    try:
        _, Gui = app_gui()
        _install_custom_title_bar(Gui.getMainWindow())
    except Exception:
        pass


def _install_filter(mw) -> None:
    global _FILTER
    if _FILTER is None:
        _FILTER = _MacChromeFilter(mw)
    mw.installEventFilter(_FILTER)


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
        "lib": lib,
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
        widget.createWinId()
    except Exception:
        pass
    return int(widget.winId())


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


def _restore_cocoa_titlebar(mw) -> bool:
    """Ask AppKit for a normal titled window with close / miniaturize / zoom."""
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


def _hide_cocoa_traffic_lights(mw) -> None:
    """Hide AppKit's own lights so we don't draw two sets after going frameless."""
    try:
        o = _objc()
        win = _nswindow(mw)
        if not win:
            return
        sel = o["sel"]
        o["void_b"](win, sel("setTitlebarAppearsTransparent:"), True)
        o["void_u"](win, sel("setTitleVisibility:"), 1)  # NSWindowTitleHidden
        for btn_id in (_NS_CLOSE, _NS_MINIATURIZE, _NS_ZOOM):
            btn = o["id_id_u"](win, sel("standardWindowButton:"), btn_id)
            if btn:
                o["void_b"](btn, sel("setHidden:"), True)
    except Exception:
        pass


def _native_lights_visible(mw) -> bool:
    try:
        o = _objc()
        win = _nswindow(mw)
        if not win:
            return False
        sel = o["sel"]
        mask = o["u_id"](win, sel("styleMask"))
        if not (mask & _NS_TITLED):
            return False
        btn = o["id_id_u"](win, sel("standardWindowButton:"), _NS_CLOSE)
        if not btn:
            return False
        return not o["b_id"](btn, sel("isHidden"))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Custom title bar — only if native lights never appeared
# ---------------------------------------------------------------------------


def _install_custom_title_bar(mw) -> None:
    global _TITLE_BAR, _TITLE_TOOLBAR
    QtCore, QtGui, QtWidgets = qt()
    if _TITLE_BAR is not None:
        _TITLE_BAR.show()
        if _TITLE_TOOLBAR is not None:
            _TITLE_TOOLBAR.show()
        return

    # Drop Qt's Fusion-drawn min/max/close on the right. Frameless is OK here
    # because we immediately put stoplights on the left ourselves.
    try:
        if int(mw.windowFlags() & QtCore.Qt.FramelessWindowHint) == 0:
            visible = mw.isVisible()
            mw.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)
            if visible:
                mw.show()
                mw.raise_()
                mw.activateWindow()
    except Exception:
        pass

    _hide_cocoa_traffic_lights(mw)
    try:
        sb = mw.statusBar()
        if sb is not None:
            sb.setSizeGripEnabled(True)
    except Exception:
        pass

    bar = _TrafficTitleBar(mw)
    tb = QtWidgets.QToolBar("BtStudioTitleBar", mw)
    tb.setObjectName("BtStudioTitleBar")
    tb.setMovable(False)
    tb.setFloatable(False)
    tb.setContextMenuPolicy(QtCore.Qt.PreventContextMenu)
    tb.setIconSize(QtCore.QSize(1, 1))
    tb.setFixedHeight(TRAFFIC_LIGHT_BAR_HEIGHT + 4)
    tb.setStyleSheet(
        "QToolBar#BtStudioTitleBar { border: none; padding: 0px; spacing: 0px; }"
    )
    bar.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
    tb.addWidget(bar)

    existing = [
        t
        for t in mw.findChildren(QtWidgets.QToolBar)
        if t is not tb and mw.toolBarArea(t) == QtCore.Qt.TopToolBarArea
    ]
    if existing:
        mw.insertToolBar(existing[0], tb)
    else:
        mw.addToolBar(QtCore.Qt.TopToolBarArea, tb)

    _TITLE_BAR = bar
    _TITLE_TOOLBAR = tb
    try:
        import FreeCAD as App

        App.Console.PrintMessage(
            "BtStudio: macOS traffic lights drawn top-left "
            "(native NSWindow chrome was not available).\n"
        )
    except Exception:
        pass


def _remove_custom_title_bar(mw) -> None:
    global _TITLE_BAR, _TITLE_TOOLBAR
    if _TITLE_TOOLBAR is None:
        return
    try:
        mw.removeToolBar(_TITLE_TOOLBAR)
    except Exception:
        pass
    _TITLE_TOOLBAR.deleteLater()
    _TITLE_BAR = None
    _TITLE_TOOLBAR = None
