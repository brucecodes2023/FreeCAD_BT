# SPDX-License-Identifier: LGPL-2.1-or-later
# ***************************************************************************
# *   Copyright (c) 2026 FreeCAD_BT contributors                            *
# ***************************************************************************
"""Assembly motional joints → Robot trajectory / kinematic CSV.

Legacy Robot::RobotObject is fixed at six revolute DH axes. This bridge does
not rewrite that solver. It orders Assembly Revolute/Slider/Cylindrical
joints, builds a Robot::TrajectoryObject, and optionally writes a 6-axis CSV.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from typing import Any, List, Optional

try:
    from .chain_graph import order_serial_chain, write_kinematic_csv
except ImportError:
    from RobotTools.chain_graph import order_serial_chain, write_kinematic_csv

# Include both spellings while Assembly naming settles (Revolute vs Revolute).
MOTION_JOINT_TYPES = (
    "Revolute",
    "Revolute",
    "Slider",
    "Cylindrical",
    "Cylindrical",
)


@dataclass
class ChainJoint:
    name: str
    label: str
    joint_type: str
    part1_name: str
    part2_name: str
    placement: Any = None
    tip_placement: Any = None
    angle_min: float = -180.0
    angle_max: float = 180.0
    length_min: float = -1000.0
    length_max: float = 1000.0
    velocity: float = 90.0


@dataclass
class ChainResult:
    joints: List[ChainJoint] = field(default_factory=list)
    topology: str = "empty"
    messages: List[str] = field(default_factory=list)

    @property
    def revolute_count(self) -> int:
        return sum(
            1 for j in self.joints if j.joint_type in ("Revolute", "Revolute")
        )

    @property
    def motional_count(self) -> int:
        return len(self.joints)


def _part_key(part) -> str:
    if part is None:
        return ""
    return getattr(part, "Name", str(part))


def approximate_dh_row(
    prev_plc, curr_plc, joint_type, angle_min, angle_max, velocity=90.0
):
    """Approximate one DH CSV row from consecutive joint placements."""
    if prev_plc is None or curr_plc is None:
        return (100.0, 0.0, 0.0, 0.0, 1.0, angle_max, angle_min, velocity)

    rel = prev_plc.inverse().multiply(curr_plc)
    base = rel.Base
    a = math.hypot(base.x, base.y)
    d = float(base.z)
    try:
        z_axis = rel.Rotation.multVec(type(base)(0, 0, 1))
        if abs(z_axis.z) + abs(z_axis.y) > 1e-9:
            alpha = math.degrees(math.atan2(z_axis.y, z_axis.z))
        else:
            alpha = 0.0
    except Exception:
        alpha = 0.0
    if joint_type == "Slider":
        angle_min, angle_max = -180.0, 180.0
    if a < 1e-6 and abs(d) < 1e-6:
        a = 100.0
    return (a, alpha, d, 0.0, 1.0, angle_max, angle_min, velocity)


def _joint_limits(joint):
    amin, amax = -180.0, 180.0
    lmin, lmax = -1000.0, 1000.0
    if getattr(joint, "EnableAngleMin", False):
        amin = float(joint.AngleMin)
    if getattr(joint, "EnableAngleMax", False):
        amax = float(joint.AngleMax)
    if getattr(joint, "EnableLengthMin", False):
        lmin = float(joint.LengthMin)
    if getattr(joint, "EnableLengthMax", False):
        lmax = float(joint.LengthMax)
    return amin, amax, lmin, lmax


def analyze_assembly(assembly) -> ChainResult:
    """Build a ChainResult from an Assembly object."""
    import UtilsAssembly

    result = ChainResult()
    if assembly is None:
        result.messages.append("No active assembly.")
        return result

    raw = UtilsAssembly.getJointsOfType(assembly, list(MOTION_JOINT_TYPES))
    if not raw:
        result.messages.append(
            "No Revolute, Slider, or Cylindrical joints. Add motional mates first."
        )
        return result

    edges = []
    for joint in raw:
        p1 = UtilsAssembly.getMovingPart(joint.Reference1)
        p2 = UtilsAssembly.getMovingPart(joint.Reference2)
        k1, k2 = _part_key(p1), _part_key(p2)
        if k1 and k2 and k1 != k2:
            edges.append((k1, k2, joint))

    ordered, topology, msgs = order_serial_chain(edges)
    result.topology = topology
    result.messages.extend(msgs)
    joint_list = ordered if ordered else list(raw)

    for joint in joint_list:
        p1 = UtilsAssembly.getMovingPart(joint.Reference1)
        p2 = UtilsAssembly.getMovingPart(joint.Reference2)
        try:
            plc1 = UtilsAssembly.getJcsGlobalPlc(joint.Placement1, joint.Reference1)
            plc2 = UtilsAssembly.getJcsGlobalPlc(joint.Placement2, joint.Reference2)
        except Exception:
            plc1 = getattr(joint, "Placement1", None)
            plc2 = getattr(joint, "Placement2", None)

        amin, amax, lmin, lmax = _joint_limits(joint)
        result.joints.append(
            ChainJoint(
                name=joint.Name,
                label=getattr(joint, "Label", joint.Name),
                joint_type=joint.JointType,
                part1_name=_part_key(p1),
                part2_name=_part_key(p2),
                placement=plc1,
                tip_placement=plc2,
                angle_min=amin,
                angle_max=amax,
                length_min=lmin,
                length_max=lmax,
            )
        )

    result.messages.append(
        "Chain: {} motional joint(s) ({} revolute), topology={}.".format(
            result.motional_count, result.revolute_count, result.topology
        )
    )
    return result


def dh_rows_from_chain(chain: ChainResult):
    rows = []
    prev = None
    for joint in chain.joints:
        rows.append(
            approximate_dh_row(
                prev,
                joint.placement,
                joint.joint_type,
                joint.angle_min,
                joint.angle_max,
                joint.velocity,
            )
        )
        prev = joint.tip_placement or joint.placement
    return rows


def create_trajectory_from_chain(doc, chain: ChainResult, name="AsmTrajectory"):
    """Create Robot::TrajectoryObject with LIN waypoints. Returns (obj, count)."""
    import Robot as RobotMod

    if doc is None:
        raise RuntimeError("No active document")

    traj_obj = doc.addObject("Robot::TrajectoryObject", name)
    traj = traj_obj.Trajectory
    count = 0
    for i, joint in enumerate(chain.joints):
        base = joint.placement
        tip = joint.tip_placement or joint.placement
        if base is not None:
            wp = "J{}_{}_A".format(i + 1, joint.label.replace(" ", "_")[:20])
            traj = traj.insertWaypoints(RobotMod.Waypoint(base, "LIN", wp))
            count += 1
        if tip is not None and tip is not base:
            wp = "J{}_{}_B".format(i + 1, joint.label.replace(" ", "_")[:20])
            traj = traj.insertWaypoints(RobotMod.Waypoint(tip, "LIN", wp))
            count += 1
    traj_obj.Trajectory = traj
    return traj_obj, count


def create_robot_from_chain(
    doc, chain: ChainResult, csv_path: str, name="AsmRobot", vrml_path: Optional[str] = None
):
    """Create Robot::RobotObject wired to kinematic CSV (+ optional VRML)."""
    if doc is None:
        raise RuntimeError("No active document")

    write_kinematic_csv(csv_path, dh_rows_from_chain(chain))
    robot = doc.addObject("Robot::RobotObject", name)
    robot.RobotKinematicFile = csv_path
    if vrml_path and os.path.isfile(vrml_path):
        robot.RobotVrmlFile = vrml_path
    return robot


def find_default_vrml():
    import FreeCAD as App

    for rel in (
        os.path.join("Mod", "Robot", "Lib", "Kuka", "kr500_1.wrl"),
        os.path.join("Mod", "Robot", "Lib", "Kuka", "kr16.wrl"),
    ):
        path = os.path.join(App.getResourceDir(), rel)
        if os.path.isfile(path):
            return path
    return None


def ensure_robot_workbench_enabled() -> bool:
    """Remove RobotWorkbench from Disabled workbenches preference."""
    import FreeCAD as App

    grp = App.ParamGet("User parameter:BaseApp/Preferences/Workbenches")
    default = (
        "NoneWorkbench,TestWorkbench,InspectionWorkbench,"
        "RobotWorkbench,OpenSCADWorkbench"
    )
    disabled = grp.GetString("Disabled", default)
    parts = [p.strip() for p in disabled.split(",") if p.strip()]
    if "RobotWorkbench" not in parts:
        return False
    grp.SetString("Disabled", ",".join(p for p in parts if p != "RobotWorkbench"))
    return True
