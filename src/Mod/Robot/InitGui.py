# Robot gui init module
# SPDX-License-Identifier: LGPL-2.1-or-later

# (c) 2009 Juergen Riegel
# FreeCAD_BT: clearer Robotics entry + Assembly→trajectory command (2026)

# Gathering all the information to start FreeCAD
# This is the second one of three init scripts, the third one
# runs when the gui is up

# ***************************************************************************
# *   Copyright (c) 2009 Juergen Riegel <juergen.riegel@web.de>             *
# *                                                                         *
# *   This file is part of the FreeCAD CAx development system.              *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   FreeCAD is distributed in the hope that it will be useful,            *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Lesser General Public License for more details.                   *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with FreeCAD; if not, write to the Free Software        *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# ***************************************************************************/


class RobotWorkbench(Workbench):
    """Robotics workbench — trajectories and 6-axis kinematics."""

    def __init__(self):
        self.__class__.Icon = (
            FreeCAD.getResourceDir() + "Mod/Robot/Resources/icons/RobotWorkbench.svg"
        )
        self.__class__.MenuText = "Robotics"
        self.__class__.ToolTip = (
            "Robotics: serial arm trajectory from Assembly, drone joint "
            "inventory export, 6-axis kinematics, simulate"
        )

    def Initialize(self):
        # load the module
        import RobotGui
        import Robot

        try:
            from RobotTools.CommandFromAssembly import register_commands

            register_commands()
        except Exception as exc:
            FreeCAD.Console.PrintWarning(
                "Robotics: could not register From Assembly command: {}\n".format(exc)
            )

        try:
            from RobotTools.CommandExportJoints import register_commands as register_export

            register_export()
        except Exception as exc:
            FreeCAD.Console.PrintWarning(
                "Robotics: could not register Export Assembly Joints: {}\n".format(exc)
            )

        try:
            from RobotTools.assembly_chain import ensure_robot_workbench_enabled

            if ensure_robot_workbench_enabled():
                FreeCAD.Console.PrintLog(
                    "Robotics: enabled RobotWorkbench in Preferences → Workbenches.\n"
                )
        except Exception:
            pass

    def GetClassName(self):
        return "RobotGui::Workbench"


Gui.addWorkbench(RobotWorkbench())
