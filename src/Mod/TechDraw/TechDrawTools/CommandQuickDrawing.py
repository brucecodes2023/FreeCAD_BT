# ***************************************************************************
# *   Copyright (c) 2026 FreeCAD_BT contributors                            *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   This program is distributed in the hope that it will be useful,       *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Library General Public License for more details.                  *
# ***************************************************************************
"""One-click page + Front/Top/Right multiview for selected parts."""

__title__ = "TechDrawTools.CommandQuickDrawing"
__author__ = "FreeCAD_BT"
__url__ = "https://www.freecad.org"

from PySide.QtCore import QT_TRANSLATE_NOOP

import FreeCAD as App
import FreeCADGui as Gui
import os


def _defaultTemplatePath():
    """Resolve Mod/TechDraw Files/TemplateFile (absolute or relative to Templates/)."""
    templates = os.path.join(App.getResourceDir(), "Mod", "TechDraw", "Templates")
    primary = os.path.join(templates, "ISO", "A3_Landscape_ISO5457_minimal.svg")
    legacy = os.path.join(templates, "Default_Template_A4_Landscape.svg")
    try:
        grp = App.ParamGet("User parameter:BaseApp/Preferences/Mod/TechDraw/Files")
        pref = grp.GetString("TemplateFile", primary)
    except Exception:
        pref = primary
    if not pref:
        pref = primary
    if not os.path.isabs(pref):
        pref = os.path.join(templates, pref)
    if os.path.isfile(pref):
        return pref
    if os.path.isfile(primary):
        return primary
    return legacy


def _drawableSelection():
    """Bodies, parts, and other non-page objects suitable as view sources."""
    shapes = []
    for obj in Gui.Selection.getSelection():
        if obj.isDerivedFrom("TechDraw::DrawPage"):
            continue
        if obj.isDerivedFrom("TechDraw::DrawView"):
            continue
        if obj.isDerivedFrom("TechDraw::DrawSVGTemplate"):
            continue
        shapes.append(obj)
    return shapes


def _ensurePage(doc):
    pages = [o for o in doc.Objects if o.isDerivedFrom("TechDraw::DrawPage")]
    if pages:
        return pages[0]

    templatePath = _defaultTemplatePath()
    if not os.path.isfile(templatePath):
        raise RuntimeError("No TechDraw template found at {}".format(templatePath))

    page = doc.addObject("TechDraw::DrawPage", "Page")
    template = doc.addObject("TechDraw::DrawSVGTemplate", "Template")
    template.Template = templatePath
    page.Template = template
    return page


class CommandQuickDrawing:
    """Create a drawing page and Front/Top/Right views from the selection."""

    def GetResources(self):
        return {
            "Pixmap": "actions/TechDraw_ProjectionGroup",
            "Accel": "",
            "MenuText": QT_TRANSLATE_NOOP(
                "TechDraw_QuickDrawing", "Quick Drawing"
            ),
            "ToolTip": QT_TRANSLATE_NOOP(
                "TechDraw_QuickDrawing",
                "Creates a page (default template) and Front/Top/Right views of the selected parts",
            ),
        }

    def IsActive(self):
        return bool(App.ActiveDocument) and not Gui.Control.activeDialog()

    def Activated(self):
        doc = App.ActiveDocument
        if not doc:
            return

        shapes = _drawableSelection()
        if not shapes:
            from PySide import QtGui

            QtGui.QMessageBox.warning(
                Gui.getMainWindow(),
                QT_TRANSLATE_NOOP("TechDraw_QuickDrawing", "Quick Drawing"),
                QT_TRANSLATE_NOOP(
                    "TechDraw_QuickDrawing",
                    "Select one or more parts, bodies, or solids first.",
                ),
            )
            return

        doc.openTransaction("Quick Drawing")
        try:
            page = _ensurePage(doc)
            group = doc.addObject("TechDraw::DrawProjGroup", "ProjGroup")
            page.addView(group)
            group.Source = shapes
            group.addProjection("Front")
            # Default looking down +X for Front; Top/Right complete a standard triad.
            if group.Anchor:
                group.Anchor.Direction = App.Vector(0.0, -1.0, 0.0)
                group.Anchor.RotationVector = App.Vector(1.0, 0.0, 0.0)
                group.Anchor.XDirection = App.Vector(1.0, 0.0, 0.0)
                group.Anchor.recompute()
            group.addProjection("Top")
            group.addProjection("Right")
            doc.recompute()
            Gui.Selection.clearSelection()
            Gui.Selection.addSelection(page)
            # Open the page view if a view provider exists.
            try:
                Gui.activeDocument().getObject(page.Name).doubleClicked()
            except Exception:
                pass
        except Exception as exc:
            doc.abortTransaction()
            App.Console.PrintError("TechDraw Quick Drawing failed: {}\n".format(exc))
            return

        doc.commitTransaction()
        App.Console.PrintMessage(
            "TechDraw: Quick Drawing created page with Front/Top/Right views.\n"
        )


Gui.addCommand("TechDraw_QuickDrawing", CommandQuickDrawing())
