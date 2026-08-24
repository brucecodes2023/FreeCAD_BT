# SPDX-License-Identifier: LGPL-2.1-or-later
# Vendored from theosib/FreeCAD-MCP-Server (LGPL-2.1-or-later).
# Part of FcBridge, a fork-only dev/test module. See ATTRIBUTION.md.
"""Viewport screenshot handler."""

import base64
import os
import tempfile

import FreeCAD

try:
    import FreeCADGui
except ImportError:
    FreeCADGui = None


def get_screenshot(width: int = 1024, height: int = 768) -> dict:
    """Capture the current 3D viewport as a base64-encoded PNG image.

    Args:
        width: Image width in pixels.
        height: Image height in pixels.

    Returns:
        dict with base64_png (the image data) and dimensions.
    """
    if FreeCADGui is None:
        raise RuntimeError("FreeCADGui not available (headless mode?)")

    view = FreeCADGui.ActiveDocument
    if view is None:
        raise RuntimeError("No active document view")

    active_view = view.ActiveView
    if active_view is None:
        raise RuntimeError("No active 3D view")

    # Save to a temp file, read it back, then clean up.
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp_path = tmp.name
    tmp.close()

    try:
        active_view.saveImage(tmp_path, width, height, "Current")

        with open(tmp_path, "rb") as f:
            image_data = f.read()

        return {
            "base64_png": base64.b64encode(image_data).decode("ascii"),
            "width": width,
            "height": height,
            "format": "png",
        }
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
