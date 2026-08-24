# SPDX-License-Identifier: LGPL-2.1-or-later
# BtStudio — additive GUI overlay (fork-only). Loaded via FreeCAD -M.

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
    import FreeCAD

    FreeCAD.__unit_test__ += ["btstudio.tests"]
except Exception:
    pass
