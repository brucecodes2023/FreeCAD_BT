# SPDX-License-Identifier: LGPL-2.1-or-later
# /**************************************************************************
#                                                                           *
#    Copyright (c) 2026 FreeCAD_BT contributors                             *
#                                                                           *
#    This file is part of FreeCAD.                                          *
#                                                                           *
#    FreeCAD is free software: you can redistribute it and/or modify it     *
#    under the terms of the GNU Lesser General Public License as            *
#    published by the Free Software Foundation, either version 2.1 of the   *
#    License, or (at your option) any later version.                        *
#                                                                           *
#    FreeCAD is distributed in the hope that it will be useful, but         *
#    WITHOUT ANY WARRANTY; without even the implied warranty of             *
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the           *
#    GNU Lesser General Public License for more details.                    *
#                                                                           *
#    You should have received a copy of the GNU Lesser General Public       *
#    License along with FreeCAD. If not, see                                *
#    <https://www.gnu.org/licenses/>.                                       *
#                                                                           *
# **************************************************************************/

"""Incremental edit-in-context for Assembly (F4 partial).

Opens / activates a selected assembly component for PartDesign editing with
optional isolation of other components, and restores the assembly afterward.

This is not full SolidWorks-style in-place (mates do not drive feature geometry
while editing). It is the practical path: Edit Part → isolate → edit → Return.
"""

import FreeCAD as App

from PySide.QtCore import QT_TRANSLATE_NOOP

if App.GuiUp:
    import FreeCADGui as Gui
    from PySide import QtWidgets

import UtilsAssembly

translate = App.Qt.translate

__title__ = "Assembly Commands to Edit Parts In Context"
__url__ = "https://www.freecad.org"

# Module-level session: survives leaving assembly edit (e.g. to edit a sketch).
_edit_session = None

# IsolateMode::Transparent
_ISOLATE_TRANSPARENT = 0


def getEditSession():
    return _edit_session


def clearEditSession():
    global _edit_session
    _edit_session = None


def findEditableBody(obj):
    """Return a PartDesign::Body under obj, or obj itself if it is a Body."""
    if obj is None:
        return None
    if obj.TypeId == "PartDesign::Body":
        return obj
    if obj.TypeId == "App::Part" and hasattr(obj, "Group"):
        for child in obj.Group:
            if child.TypeId == "PartDesign::Body":
                return child
    return None


def resolveLinkedTarget(component):
    """Resolve the document object that should be edited for an assembly component."""
    if component is None:
        return None

    if component.isDerivedFrom("Assembly::AssemblyLink"):
        linked = component.getLinkedAssembly()
        return linked

    if UtilsAssembly.isLink(component) or component.isDerivedFrom("App::Link"):
        linked = component.getLinkedObject(True)
        return linked if linked else component

    return component


def resolveSelectedComponent(assembly=None):
    """
    From the current selection, return (assembly, component) for an assembly
    component suitable for Edit Part. Returns (None, None) if unresolved.
    """
    if not App.GuiUp:
        return None, None

    if assembly is None:
        assembly = UtilsAssembly.activeAssembly()

    selection = Gui.Selection.getSelectionEx("*", 0)
    if not selection:
        return None, None

    for sel in selection:
        if not sel.SubElementNames:
            # Direct selection of a link under the assembly
            obj = sel.Object
            if assembly and assembly.hasObject(obj, True):
                if obj.isDerivedFrom("App::Link") or obj.isDerivedFrom("Assembly::AssemblyLink"):
                    return assembly, obj
            continue

        for sub in sel.SubElementNames:
            asm = assembly
            if asm is None:
                # Walk selection path for an AssemblyObject
                names = [sel.Object.Name] + [n for n in sub.split(".") if n]
                doc = sel.Object.Document
                for name in names:
                    candidate = doc.getObject(name)
                    if candidate and candidate.isDerivedFrom("Assembly::AssemblyObject"):
                        asm = candidate
                        break
            if asm is None:
                continue

            component, _rel = UtilsAssembly.getComponentReference(asm, sel.Object, sub)
            if component:
                return asm, component

    return None, None


def _status(msg, timeout_ms=6000):
    App.Console.PrintMessage(msg + "\n")
    if App.GuiUp:
        Gui.getMainWindow().showMessage(msg, timeout_ms)


def _activateDocument(doc):
    if not doc:
        return
    App.setActiveDocument(doc.Name)
    gui_doc = Gui.getDocument(doc)
    if gui_doc:
        gui_doc.ActiveView


def enterEditPart(assembly, component, isolate_mode=_ISOLATE_TRANSPARENT):
    """
    Isolate the component (when possible), open/activate its linked target,
    and record a return session. Returns True on success.
    """
    global _edit_session

    if not assembly or not component:
        return False

    linked = resolveLinkedTarget(component)
    if not linked:
        _status(
            translate(
                "Assembly_EditPart",
                "Cannot resolve the linked object for the selected component.",
            )
        )
        return False

    # Flexible sub-assembly: send user to the linked assembly instead.
    if component.isDerivedFrom("Assembly::AssemblyLink"):
        Gui.runCommand("Assembly_LinkSelectLinked", 0)
        return True

    vpa = assembly.ViewObject
    prev_movement = True
    if hasattr(vpa, "EnableMovement"):
        prev_movement = bool(vpa.EnableMovement)
        vpa.EnableMovement = False

    # Isolate other components; hold across selection / transactions.
    try:
        vpa.isolateComponents([component], isolate_mode)
        if hasattr(vpa, "HoldIsolate"):
            vpa.HoldIsolate = True
    except Exception as exc:
        App.Console.PrintWarning(f"Edit Part isolation skipped: {exc}\n")

    prev_wb = Gui.activeWorkbench().name() if Gui.activeWorkbench() else ""

    _edit_session = {
        "assembly_doc": assembly.Document.Name,
        "assembly_name": assembly.Name,
        "component_name": component.Name,
        "linked_doc": linked.Document.Name,
        "linked_name": linked.Name,
        "prev_movement": prev_movement,
        "prev_workbench": prev_wb,
        "same_document": linked.Document == assembly.Document,
    }

    body = findEditableBody(linked)

    if linked.Document != assembly.Document:
        # External part file: switch document and activate Body/Part.
        if getattr(linked.Document, "Partial", False):
            try:
                # Fully load a partially opened linked document.
                Gui.getDocument(linked.Document.Name)
                reopen = getattr(Gui, "reopen", None) or getattr(
                    getattr(Gui, "Application", None), "reopen", None
                )
                if callable(reopen):
                    reopen(linked.Document)
            except Exception as exc:
                App.Console.PrintWarning(f"Could not fully open linked document: {exc}\n")
            linked = App.getDocument(_edit_session["linked_doc"]).getObject(
                _edit_session["linked_name"]
            )
            body = findEditableBody(linked)

        _activateDocument(linked.Document)
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(linked)
        if body:
            view = Gui.getDocument(linked.Document).ActiveView
            if view:
                view.setActiveObject("pdbody", body)
            Gui.activateWorkbench("PartDesignWorkbench")
        elif linked.TypeId == "App::Part":
            view = Gui.getDocument(linked.Document).ActiveView
            if view:
                view.setActiveObject("part", linked)
    else:
        # Same document: keep assembly visible; activate Body for PartDesign.
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(component)
        if body:
            view = Gui.getDocument(assembly.Document).ActiveView
            if view:
                view.setActiveObject("pdbody", body)
            Gui.activateWorkbench("PartDesignWorkbench")
        elif linked.TypeId == "App::Part":
            view = Gui.getDocument(assembly.Document).ActiveView
            if view:
                view.setActiveObject("part", linked)

    label = component.Label if getattr(component, "Label", None) else component.Name
    _status(
        translate(
            "Assembly_EditPart",
            "Editing “%1” in context — use Return to Assembly when finished.",
        ).replace("%1", label)
    )
    return True


def returnFromEditPart():
    """Clear isolation and reactivate the assembly from the edit session."""
    global _edit_session

    session = _edit_session
    if not session:
        return False

    asm_doc = App.getDocument(session["assembly_doc"])
    if not asm_doc:
        clearEditSession()
        _status(
            translate(
                "Assembly_ReturnFromEdit",
                "Assembly document is no longer open; edit session cleared.",
            )
        )
        return False

    assembly = asm_doc.getObject(session["assembly_name"])
    _activateDocument(asm_doc)

    if assembly and hasattr(assembly, "ViewObject") and assembly.ViewObject:
        vpa = assembly.ViewObject
        try:
            if hasattr(vpa, "HoldIsolate"):
                vpa.HoldIsolate = False
            vpa.clearIsolate()
        except Exception:
            pass
        if hasattr(vpa, "EnableMovement"):
            vpa.EnableMovement = session.get("prev_movement", True)

        # Re-enter assembly edit so mates/drag work again.
        try:
            if not vpa.isInEditMode():
                Gui.getDocument(asm_doc).setEdit(assembly)
        except Exception as exc:
            App.Console.PrintWarning(f"Could not re-activate assembly: {exc}\n")

    # Clear PartDesign active body override in the assembly view.
    try:
        view = Gui.getDocument(asm_doc).ActiveView
        if view:
            view.setActiveObject("pdbody", None)
    except Exception:
        pass

    Gui.activateWorkbench("AssemblyWorkbench")
    Gui.Selection.clearSelection()
    if assembly:
        Gui.Selection.addSelection(assembly)

    # Light touch: recompute + solve so mates pick up geometry changed while editing.
    if assembly:
        try:
            assembly.recompute(True)
        except Exception as exc:
            App.Console.PrintWarning(f"Assembly recompute after edit: {exc}\n")
        try:
            import JointObject

            JointObject.solveIfAllowed(assembly, storePrev=False, quiet_success=True)
        except Exception as exc:
            App.Console.PrintWarning(f"Assembly solve after edit: {exc}\n")

    clearEditSession()
    _status(translate("Assembly_ReturnFromEdit", "Returned to assembly."))
    return True


class CommandEditPart:
    def GetResources(self):
        return {
            "Pixmap": "Geofeaturegroup",
            "MenuText": QT_TRANSLATE_NOOP("Assembly_EditPart", "Edit Part"),
            "Accel": "E, P",
            "ToolTip": QT_TRANSLATE_NOOP(
                "Assembly_EditPart",
                "<p>Edit the selected assembly component in context.</p>"
                "<p>Double-click a part in the 3D view (or tree) while the assembly "
                "is active, or run this command. Isolates the part, activates its Body "
                "for PartDesign, and keeps other components faded. Use Return to Assembly "
                "when done.</p>"
                "<p>Not full SolidWorks in-place: geometry is edited on the linked "
                "object; mates are reapplied after return.</p>",
            ),
            "CmdType": "ForEdit",
        }

    def IsActive(self):
        if getEditSession() is not None:
            return False  # prefer Return while a session is open
        assembly, component = resolveSelectedComponent()
        return assembly is not None and component is not None

    def Activated(self):
        if getEditSession() is not None:
            _status(
                translate(
                    "Assembly_EditPart",
                    "Already editing a part — use Return to Assembly first.",
                )
            )
            return

        assembly, component = resolveSelectedComponent()
        if not assembly or not component:
            _status(
                translate(
                    "Assembly_EditPart",
                    "Select an assembly component (part link) to edit.",
                )
            )
            return

        # Ensure assembly is active/in edit so isolation applies.
        if UtilsAssembly.activeAssembly() is None:
            try:
                Gui.getDocument(assembly.Document).setEdit(assembly)
            except Exception:
                pass

        enterEditPart(assembly, component)


class CommandReturnFromEdit:
    def GetResources(self):
        return {
            "Pixmap": "Assembly_ActivateAssembly",
            "MenuText": QT_TRANSLATE_NOOP(
                "Assembly_ReturnFromEdit", "Return to Assembly"
            ),
            "Accel": "E, A",
            "ToolTip": QT_TRANSLATE_NOOP(
                "Assembly_ReturnFromEdit",
                "Exit edit-part-in-context: clear isolation and reactivate the assembly.",
            ),
            "CmdType": "ForEdit",
        }

    def IsActive(self):
        return getEditSession() is not None

    def Activated(self):
        returnFromEditPart()


if App.GuiUp:
    Gui.addCommand("Assembly_EditPart", CommandEditPart())
    Gui.addCommand("Assembly_ReturnFromEdit", CommandReturnFromEdit())
