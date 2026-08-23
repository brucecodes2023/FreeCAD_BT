# SPDX-License-Identifier: LGPL-2.1-or-later
# ***************************************************************************
# *   Copyright (c) 2026 FreeCAD_BT contributors                            *
# ***************************************************************************
"""Assembly joint inventory for drone / multi-rotor export (not serial IK).

Scans Assembly joints into generic JSON (primary) + CSV. Does not build a
Robot trajectory or solve multi-branch kinematics — that is the separate
``Robot_FromAssembly`` serial-arm path.
"""

from __future__ import annotations

import csv
import json
import os
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Sequence

# Primary inventory types for drone / multi-rotor layouts.
INVENTORY_JOINT_TYPES = (
    "Revolute",
    "Slider",
    "Cylindrical",
    "Fixed",
)

SCHEMA_VERSION = 1

CSV_FIELDNAMES = (
    "name",
    "label",
    "type",
    "part1",
    "part2",
    "grounded",
    "axis_x",
    "axis_y",
    "axis_z",
    "pos_x",
    "pos_y",
    "pos_z",
    "angle_min",
    "angle_max",
    "length_min",
    "length_max",
    "angle_limits_enabled",
    "length_limits_enabled",
)


@dataclass
class JointRecord:
    """One joint row in the inventory (FreeCAD-independent)."""

    name: str
    label: str
    type: str
    part1: str = ""
    part2: str = ""
    grounded: bool = False
    axis: Optional[List[float]] = None
    position: Optional[List[float]] = None
    placement_summary: str = ""
    angle_min: Optional[float] = None
    angle_max: Optional[float] = None
    length_min: Optional[float] = None
    length_max: Optional[float] = None
    angle_limits_enabled: bool = False
    length_limits_enabled: bool = False
    object_ref: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class JointInventory:
    """Full inventory document."""

    schema: str = "freecad.robot.joint_inventory"
    schema_version: int = SCHEMA_VERSION
    purpose: str = (
        "Drone/multi-rotor joint inventory export — not serial-arm trajectory."
    )
    assembly: str = ""
    document: str = ""
    joint_count: int = 0
    grounded_count: int = 0
    joints: List[JointRecord] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": self.schema,
            "schema_version": self.schema_version,
            "purpose": self.purpose,
            "assembly": self.assembly,
            "document": self.document,
            "joint_count": self.joint_count,
            "grounded_count": self.grounded_count,
            "notes": list(self.notes),
            "joints": [j.to_dict() for j in self.joints],
        }


def _fmt6(value: float) -> float:
    return float("{:.6g}".format(value))


def _vec3(vec) -> Optional[List[float]]:
    if vec is None:
        return None
    try:
        return [_fmt6(float(vec.x)), _fmt6(float(vec.y)), _fmt6(float(vec.z))]
    except Exception:
        try:
            return [_fmt6(float(vec[0])), _fmt6(float(vec[1])), _fmt6(float(vec[2]))]
        except Exception:
            return None


def placement_axis_and_position(plc) -> tuple:
    """Return (axis_xyz, position_xyz, summary_str) from a Placement-like object."""
    if plc is None:
        return None, None, ""
    try:
        pos = plc.Base
        position = _vec3(pos)
        rot = plc.Rotation
        try:
            axis_vec = rot.multVec(type(pos)(0, 0, 1))
        except Exception:
            # Fallback: treat Z of identity if Rotation API differs in mocks.
            axis_vec = type(pos)(0, 0, 1) if pos is not None else None
        axis = _vec3(axis_vec)
        summary = "pos=({:.4g},{:.4g},{:.4g}) axis=({:.4g},{:.4g},{:.4g})".format(
            *(position or (0, 0, 0)),
            *(axis or (0, 0, 1)),
        )
        return axis, position, summary
    except Exception:
        return None, None, ""


def inventory_to_json(inventory: JointInventory, indent: int = 2) -> str:
    return json.dumps(inventory.to_dict(), indent=indent, sort_keys=False) + "\n"


def inventory_to_csv_rows(inventory: JointInventory) -> List[Dict[str, Any]]:
    rows = []
    for joint in inventory.joints:
        axis = joint.axis or [None, None, None]
        pos = joint.position or [None, None, None]
        rows.append(
            {
                "name": joint.name,
                "label": joint.label,
                "type": joint.type,
                "part1": joint.part1,
                "part2": joint.part2,
                "grounded": joint.grounded,
                "axis_x": axis[0],
                "axis_y": axis[1],
                "axis_z": axis[2],
                "pos_x": pos[0],
                "pos_y": pos[1],
                "pos_z": pos[2],
                "angle_min": joint.angle_min,
                "angle_max": joint.angle_max,
                "length_min": joint.length_min,
                "length_max": joint.length_max,
                "angle_limits_enabled": joint.angle_limits_enabled,
                "length_limits_enabled": joint.length_limits_enabled,
            }
        )
    return rows


def write_joint_inventory(
    inventory: JointInventory, json_path: str, csv_path: Optional[str] = None
) -> Dict[str, str]:
    """Write JSON (required) and CSV (default: same basename). Returns paths."""
    parent = os.path.dirname(json_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as fh:
        fh.write(inventory_to_json(inventory))

    if csv_path is None:
        root, _ext = os.path.splitext(json_path)
        csv_path = root + ".csv"
    csv_parent = os.path.dirname(csv_path)
    if csv_parent:
        os.makedirs(csv_parent, exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(CSV_FIELDNAMES))
        writer.writeheader()
        for row in inventory_to_csv_rows(inventory):
            writer.writerow(row)
    return {"json": json_path, "csv": csv_path}


def build_inventory_from_records(
    records: Sequence[JointRecord],
    assembly: str = "",
    document: str = "",
    notes: Optional[Sequence[str]] = None,
) -> JointInventory:
    inv = JointInventory(
        assembly=assembly,
        document=document,
        joints=list(records),
        joint_count=len(records),
        grounded_count=sum(1 for r in records if r.grounded),
        notes=list(notes or ()),
    )
    return inv


def _part_key(part) -> str:
    if part is None:
        return ""
    return getattr(part, "Name", str(part))


def _joint_limits(joint):
    angle_on = bool(getattr(joint, "EnableAngleMin", False)) or bool(
        getattr(joint, "EnableAngleMax", False)
    )
    length_on = bool(getattr(joint, "EnableLengthMin", False)) or bool(
        getattr(joint, "EnableLengthMax", False)
    )
    amin = float(joint.AngleMin) if getattr(joint, "EnableAngleMin", False) else None
    amax = float(joint.AngleMax) if getattr(joint, "EnableAngleMax", False) else None
    lmin = float(joint.LengthMin) if getattr(joint, "EnableLengthMin", False) else None
    lmax = float(joint.LengthMax) if getattr(joint, "EnableLengthMax", False) else None
    # Prefer reporting configured values when either bound is enabled.
    if getattr(joint, "EnableAngleMin", False) or getattr(joint, "EnableAngleMax", False):
        if amin is None and hasattr(joint, "AngleMin"):
            amin = float(joint.AngleMin)
        if amax is None and hasattr(joint, "AngleMax"):
            amax = float(joint.AngleMax)
    if getattr(joint, "EnableLengthMin", False) or getattr(joint, "EnableLengthMax", False):
        if lmin is None and hasattr(joint, "LengthMin"):
            lmin = float(joint.LengthMin)
        if lmax is None and hasattr(joint, "LengthMax"):
            lmax = float(joint.LengthMax)
    return amin, amax, lmin, lmax, angle_on, length_on


def inventory_from_assembly(assembly) -> JointInventory:
    """Scan an Assembly object for Fixed/Revolute/Slider/Cylindrical + Grounded."""
    import UtilsAssembly

    notes: List[str] = []
    if assembly is None:
        return build_inventory_from_records([], notes=["No active assembly."])

    doc_name = ""
    try:
        doc_name = assembly.Document.Name
    except Exception:
        pass

    grounded_parts = set()
    records: List[JointRecord] = []

    # Grounded joints live in the joint group with ObjectToGround (no JointType).
    try:
        joint_group = UtilsAssembly.getJointGroup(assembly)
        for obj in getattr(joint_group, "Group", []) or []:
            if hasattr(obj, "ObjectToGround") and obj.ObjectToGround:
                grounded = obj.ObjectToGround
                gkey = _part_key(grounded)
                grounded_parts.add(gkey)
                records.append(
                    JointRecord(
                        name=obj.Name,
                        label=getattr(obj, "Label", obj.Name),
                        type="Grounded",
                        part1=gkey,
                        part2="",
                        grounded=True,
                        object_ref=obj.Name,
                        placement_summary="grounded",
                    )
                )
    except Exception as exc:
        notes.append("Grounded scan skipped: {}".format(exc))

    # Motional / Fixed joints via Assembly.Joints when available.
    all_joints = []
    try:
        all_joints = list(assembly.Joints)
    except Exception:
        try:
            all_joints = UtilsAssembly.getJointsOfType(
                assembly, list(INVENTORY_JOINT_TYPES)
            )
        except Exception as exc:
            notes.append("Joint scan failed: {}".format(exc))
            return build_inventory_from_records(
                records,
                assembly=getattr(assembly, "Name", ""),
                document=doc_name,
                notes=notes,
            )

    type_filter = set(INVENTORY_JOINT_TYPES)
    for joint in all_joints:
        jtype = getattr(joint, "JointType", None)
        if jtype is None or jtype not in type_filter:
            continue

        p1 = p2 = None
        try:
            p1 = UtilsAssembly.getMovingPart(joint.Reference1)
            p2 = UtilsAssembly.getMovingPart(joint.Reference2)
        except Exception:
            pass
        k1, k2 = _part_key(p1), _part_key(p2)

        plc = None
        try:
            plc = UtilsAssembly.getJcsGlobalPlc(joint.Placement1, joint.Reference1)
        except Exception:
            plc = getattr(joint, "Placement1", None)

        axis, position, summary = placement_axis_and_position(plc)
        amin, amax, lmin, lmax, angle_on, length_on = _joint_limits(joint)

        is_grounded = (k1 in grounded_parts) or (k2 in grounded_parts)
        try:
            if p1 is not None and hasattr(assembly, "isPartGrounded"):
                is_grounded = is_grounded or bool(assembly.isPartGrounded(p1))
            if p2 is not None and hasattr(assembly, "isPartGrounded"):
                is_grounded = is_grounded or bool(assembly.isPartGrounded(p2))
        except Exception:
            pass

        records.append(
            JointRecord(
                name=joint.Name,
                label=getattr(joint, "Label", joint.Name),
                type=str(jtype),
                part1=k1,
                part2=k2,
                grounded=is_grounded,
                axis=axis,
                position=position,
                placement_summary=summary,
                angle_min=amin,
                angle_max=amax,
                length_min=lmin,
                length_max=lmax,
                angle_limits_enabled=angle_on,
                length_limits_enabled=length_on,
                object_ref=joint.Name,
            )
        )

    notes.append(
        "Inventory: {} joint(s) ({} grounded markers). "
        "Use Trajectory from Assembly for serial arms only.".format(
            len(records),
            sum(1 for r in records if r.type == "Grounded"),
        )
    )
    return build_inventory_from_records(
        records,
        assembly=getattr(assembly, "Label", getattr(assembly, "Name", "")),
        document=doc_name,
        notes=notes,
    )
