# SPDX-License-Identifier: LGPL-2.1-or-later

"""Trackpad modifiers on the 3D view.

Default two-finger scroll pans. Shift+scroll zooms. Meta/Ctrl+scroll rotates.
Pinch (NativeGesture) zooms. Coin's native remap is Tier 1; this is an overlay.
"""

from __future__ import annotations

from .qtutil import app_gui, param_group, qt

_FILTER = None


class _NavFilter:
    def __init__(self):
        QtCore, QtGui, QtWidgets = qt()

        class Filter(QtCore.QObject):
            def eventFilter(self, obj, event):
                et = event.type()
                if et == QtCore.QEvent.NativeGesture:
                    return _handle_pinch(event)
                if et == QtCore.QEvent.Wheel:
                    return _handle_wheel(event)
                return False

        self._impl = Filter()

    def install(self, widget) -> None:
        widget.installEventFilter(self._impl)


def _active_view():
    _, Gui = app_gui()
    try:
        return Gui.ActiveDocument.ActiveView
    except Exception:
        return None


def _handle_pinch(event) -> bool:
    QtCore, QtGui, QtWidgets = qt()
    try:
        if event.gestureType() != QtCore.Qt.NativeGestureType.Zoom:
            return False
    except Exception:
        return False
    view = _active_view()
    if view is None:
        return False
    value = event.value()
    try:
        cam = view.getCameraNode()
        height = cam.height.getValue()
        cam.height.setValue(max(height * (1.0 - value), 1e-6))
        return True
    except Exception:
        return False


def _handle_wheel(event) -> bool:
    QtCore, QtGui, QtWidgets = qt()
    view = _active_view()
    if view is None:
        return False
    mods = event.modifiers()
    delta = event.angleDelta().y() if hasattr(event, "angleDelta") else event.delta()
    if delta == 0:
        pixel = event.pixelDelta() if hasattr(event, "pixelDelta") else None
        if pixel is not None:
            delta = pixel.y()
    if delta == 0:
        return False
    try:
        cam = view.getCameraNode()
    except Exception:
        return False
    shift = bool(mods & QtCore.Qt.ShiftModifier)
    meta = bool(mods & (QtCore.Qt.MetaModifier | QtCore.Qt.ControlModifier))
    try:
        if shift:
            h = cam.height.getValue()
            factor = 0.92 if delta > 0 else 1.08
            cam.height.setValue(max(h * factor, 1e-6))
            return True
        if meta:
            from pivy import coin

            rot = coin.SbRotation(coin.SbVec3f(0, 1, 0), 0.08 if delta > 0 else -0.08)
            cam.orientation.setValue(rot * cam.orientation.getValue())
            return True
        # pan: translate camera in its local xy
        from pivy import coin

        ori = cam.orientation.getValue()
        step = -delta * 0.15
        right = ori.multVec(coin.SbVec3f(1, 0, 0))
        up = ori.multVec(coin.SbVec3f(0, 1, 0))
        pos = cam.position.getValue()
        pan = right * 0.0 + up * step
        # mix x/y from pixel delta when present
        if hasattr(event, "pixelDelta"):
            px, py = event.pixelDelta().x(), event.pixelDelta().y()
            pan = right * (-px * 0.15) + up * (py * 0.15)
        cam.position.setValue(pos + pan)
        return True
    except Exception:
        return False


def install_navigation() -> None:
    global _FILTER
    studio = param_group()
    if not studio.GetBool("TrackpadNav", True):
        return
    _, Gui = app_gui()
    QtCore, QtGui, QtWidgets = qt()
    mw = Gui.getMainWindow()
    if _FILTER is None:
        _FILTER = _NavFilter()
    # Cover the MDI area so the filter sees trackpad events on the 3D view.
    mdi = mw.findChild(QtWidgets.QMdiArea)
    _FILTER.install(mdi if mdi is not None else mw)
