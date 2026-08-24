# SPDX-License-Identifier: LGPL-2.1-or-later
# BtStudio GUI init — no workbench of its own; overlays stock workbenches.

import os
import sys

# FreeCAD execs -M-loaded init files without __file__ defined; fall back
# to the module's own -M path (AdditionalModulePaths) in that case.
try:
    _DIR = os.path.dirname(__file__)
except NameError:
    import FreeCAD as _FC
    _paths = _FC.ConfigGet('AdditionalModulePaths').split(';')
    _DIR = next((p for p in _paths if os.path.basename(p.rstrip('/')) == 'BtStudio'), os.getcwd())
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

try:
    from PySide6.QtCore import QTimer
except ImportError:
    try:
        from PySide2.QtCore import QTimer
    except ImportError:
        QTimer = None


def _start_chrome():
    try:
        from btstudio.mac_chrome import apply_mac_chrome

        apply_mac_chrome()
    except Exception:
        pass


def _start():
    from btstudio.boot import startup

    startup()


if QTimer is not None:
    # Traffic lights first so Fusion's right-side min/max/close don't linger.
    QTimer.singleShot(0, _start_chrome)
    QTimer.singleShot(1200, _start)
else:
    try:
        _start()
    except Exception:
        pass
