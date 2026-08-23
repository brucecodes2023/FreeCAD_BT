# SPDX-License-Identifier: LGPL-2.1-or-later
# ***************************************************************************
# *   Copyright (c) 2026 FreeCAD_BT contributors                            *
# ***************************************************************************
"""Command: export Assembly joint inventory (drone / multi-rotor path).

Distinct from ``Robot_FromAssembly`` (serial-arm trajectory + DH CSV).
"""

import os

import FreeCAD as App

if App.GuiUp:
    import FreeCADGui as Gui
    from PySide.QtCore import QT_TRANSLATE_NOOP
    from PySide import QtGui
else:
    Gui = None
    QT_TRANSLATE_NOOP = lambda context, text: text  # noqa: E731
    QtGui = None


class CommandExportAssemblyJoints:
    """Export Fixed/Revolute/Slider/Cylindrical + Grounded joints to JSON/CSV."""

    def GetResources(self):
        return {
            "Pixmap": "Robot_Export",
            "MenuText": QT_TRANSLATE_NOOP(
                "Robot_ExportJoints", "Export Assembly Joints"
            ),
            "Accel": "A, J",
            "ToolTip": QT_TRANSLATE_NOOP(
                "Robot_ExportJoints",
                "Joint inventory for drone / multi-rotor layouts: export "
                "Revolute, Slider, Cylindrical, Fixed, and Grounded joints "
                "to generic JSON (+ CSV). Not a serial trajectory — use "
                "Trajectory from Assembly for arms/gimbals.",
            ),
        }

    def IsActive(self):
        if App.ActiveDocument is None:
            return False
        try:
            import UtilsAssembly

            return UtilsAssembly.activeAssembly() is not None
        except Exception:
            return False

    def Activated(self):
        import UtilsAssembly
        from RobotTools import joint_inventory as inv

        doc = App.ActiveDocument
        assembly = UtilsAssembly.activeAssembly()
        if not assembly:
            App.Console.PrintError(
                "Robotics: activate an Assembly (edit mode) to export joints.\n"
            )
            return

        inventory = inv.inventory_from_assembly(assembly)
        for note in inventory.notes:
            App.Console.PrintMessage("Robotics: {}\n".format(note))

        if inventory.joint_count < 1:
            App.Console.PrintError(
                "Robotics: no Fixed/Revolute/Slider/Cylindrical/Grounded "
                "joints found to export.\n"
            )
            return

        if doc.FileName:
            base_dir = os.path.dirname(doc.FileName)
            default_name = "{}_JointInventory.json".format(doc.Name)
        else:
            base_dir = App.getUserAppDataDir()
            default_name = "JointInventory.json"
        default_path = os.path.join(base_dir, default_name)

        json_path = default_path
        if Gui is not None and QtGui is not None:
            try:
                path, _filter = QtGui.QFileDialog.getSaveFileName(
                    Gui.getMainWindow(),
                    "Export Assembly Joint Inventory (JSON)",
                    default_path,
                    "JSON (*.json);;All files (*)",
                )
                if not path:
                    App.Console.PrintMessage("Robotics: joint export cancelled.\n")
                    return
                json_path = path
            except Exception:
                json_path = default_path

        if not json_path.lower().endswith(".json"):
            json_path = json_path + ".json"

        try:
            paths = inv.write_joint_inventory(inventory, json_path)
        except Exception as exc:
            App.Console.PrintError(
                "Robotics: joint inventory export failed: {}\n".format(exc)
            )
            return

        App.Console.PrintMessage(
            "Robotics: wrote joint inventory ({} joints):\n  JSON: {}\n  CSV: {}\n".format(
                inventory.joint_count, paths["json"], paths["csv"]
            )
        )
        App.Console.PrintMessage(
            "Robotics: this is the drone/multi-rotor inventory path — not "
            "Trajectory from Assembly (serial arm).\n"
        )


def register_commands():
    if not hasattr(Gui, "addCommand"):
        return
    if "Robot_ExportJoints" not in Gui.listCommands():
        Gui.addCommand("Robot_ExportJoints", CommandExportAssemblyJoints())
