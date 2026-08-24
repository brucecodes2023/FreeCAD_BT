# SPDX-License-Identifier: LGPL-2.1-or-later
# Vendored from theosib/FreeCAD-MCP-Server (LGPL-2.1-or-later).
# Part of FcBridge, a fork-only dev/test module. See ATTRIBUTION.md.
"""Script execution handler.

Runs arbitrary Python code inside FreeCAD's interpreter context.
This is the escape hatch for operations not covered by specific tools.
"""

import io
import contextlib
import traceback

import FreeCAD

try:
    import FreeCADGui
except ImportError:
    FreeCADGui = None


def execute_script(script: str) -> dict:
    """Execute a Python script in FreeCAD's interpreter context.

    The script has access to FreeCAD, FreeCADGui, App, and Gui globals.
    Stdout/stderr are captured and returned.

    Returns:
        dict with keys: success, stdout, stderr, error
    """
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    namespace = {
        "FreeCAD": FreeCAD,
        "App": FreeCAD,
        "Gui": FreeCADGui,
        "FreeCADGui": FreeCADGui,
        "__builtins__": __builtins__,
    }

    # If there's an active document, add it as a convenience
    if FreeCAD.ActiveDocument:
        namespace["doc"] = FreeCAD.ActiveDocument

    try:
        with contextlib.redirect_stdout(stdout_capture), \
             contextlib.redirect_stderr(stderr_capture):
            exec(script, namespace)

        return {
            "success": True,
            "stdout": stdout_capture.getvalue(),
            "stderr": stderr_capture.getvalue(),
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": stdout_capture.getvalue(),
            "stderr": stderr_capture.getvalue(),
            "error": f"{type(e).__name__}: {e}\n{traceback.format_exc()}",
        }
