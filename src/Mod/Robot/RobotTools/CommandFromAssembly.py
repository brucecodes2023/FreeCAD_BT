# SPDX-License-Identifier: LGPL-2.1-or-later
# ***************************************************************************
# *   Copyright (c) 2026 FreeCAD_BT contributors                            *
# ***************************************************************************
"""Command: export Assembly motional joints to Robot trajectory (+ optional CSV)."""

import os

import FreeCAD as App

if App.GuiUp:
    import FreeCADGui as Gui
    from PySide.QtCore import QT_TRANSLATE_NOOP
else:
    Gui = None
    QT_TRANSLATE_NOOP = lambda context, text: text  # noqa: E731


class CommandRobotFromAssembly:
    """Create trajectory (and optional 6-axis robot) from Assembly joints."""

    def GetResources(self):
        return {
            "Pixmap": "Robot_CreateRobot",
            "MenuText": QT_TRANSLATE_NOOP(
                "Robot_FromAssembly", "Trajectory from Assembly (serial arm)"
            ),
            "Accel": "A, R",
            "ToolTip": QT_TRANSLATE_NOOP(
                "Robot_FromAssembly",
                "Serial arm/gimbal path: build a Robot trajectory from "
                "Revolute/Slider/Cylindrical joints, and optionally a 6-axis "
                "kinematic CSV for the legacy Robot solver. For drone/"
                "multi-rotor joint lists use Export Assembly Joints instead.",
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
        from RobotTools import assembly_chain as chain

        doc = App.ActiveDocument
        assembly = UtilsAssembly.activeAssembly()
        if not assembly:
            App.Console.PrintError(
                "Robot: activate an Assembly (edit mode) with motional joints.\n"
            )
            return

        result = chain.analyze_assembly(assembly)
        for msg in result.messages:
            App.Console.PrintMessage("Robot: {}\n".format(msg))

        if result.motional_count < 1:
            App.Console.PrintError(
                "Robot: no motional joints found. Add Revolute/Slider/"
                "Cylindrical mates, then retry.\n"
            )
            return

        if result.topology in ("branched", "disconnected"):
            App.Console.PrintWarning(
                "Robot: topology is {}; trajectory uses the longest path. "
                "For drone/multi-rotor layouts use Export Assembly Joints "
                "(joint inventory JSON/CSV), not this serial trajectory.\n".format(
                    result.topology
                )
            )

        doc.openTransaction("Trajectory from Assembly")
        try:
            traj_obj, n_wp = chain.create_trajectory_from_chain(
                doc, result, name="AsmTrajectory"
            )
            App.Console.PrintMessage(
                "Robot: created {} with {} waypoint(s).\n".format(
                    traj_obj.Label, n_wp
                )
            )

            robot_obj = None
            if result.revolute_count >= 1:
                # Write CSV beside the document (or temp) for Robot6Axis.
                if doc.FileName:
                    base_dir = os.path.dirname(doc.FileName)
                else:
                    base_dir = App.getUserAppDataDir()
                csv_path = os.path.join(
                    base_dir, "{}_AsmKinematic.csv".format(doc.Name)
                )
                vrml = chain.find_default_vrml()
                robot_obj = chain.create_robot_from_chain(
                    doc, result, csv_path, name="AsmRobot", vrml_path=vrml
                )
                App.Console.PrintMessage(
                    "Robot: created {} from approximate DH CSV:\n  {}\n".format(
                        robot_obj.Label, csv_path
                    )
                )
                if result.revolute_count != 6:
                    App.Console.PrintWarning(
                        "Robot: chain has {} revolute joint(s); Robot6Axis "
                        "always uses 6 DH rows (extra axes padded / extras "
                        "truncated). Verify axes before Simulate.\n".format(
                            result.revolute_count
                        )
                    )
                if not vrml:
                    App.Console.PrintWarning(
                        "Robot: no bundled VRML found; robot has kinematics "
                        "only (no visual model).\n"
                    )

            chain.ensure_robot_workbench_enabled()
            doc.recompute()
            doc.commitTransaction()
        except Exception as exc:
            doc.abortTransaction()
            App.Console.PrintError("Robot: export failed: {}\n".format(exc))
            raise

        try:
            Gui.activateWorkbench("RobotWorkbench")
        except Exception:
            App.Console.PrintWarning(
                "Robot: could not switch to Robot workbench "
                "(enable it under Preferences → Workbenches).\n"
            )

        # Select trajectory (+ robot) for Simulate
        try:
            Gui.Selection.clearSelection()
            Gui.Selection.addSelection(doc.Name, traj_obj.Name)
            if robot_obj is not None:
                Gui.Selection.addSelection(doc.Name, robot_obj.Name)
        except Exception:
            pass


def register_commands():
    if not hasattr(Gui, "addCommand"):
        return
    if "Robot_FromAssembly" not in Gui.listCommands():
        Gui.addCommand("Robot_FromAssembly", CommandRobotFromAssembly())
