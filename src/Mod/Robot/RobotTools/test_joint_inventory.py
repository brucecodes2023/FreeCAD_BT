# SPDX-License-Identifier: LGPL-2.1-or-later
"""Unit tests for RobotTools.joint_inventory (no FreeCAD required)."""

import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROBOT_MOD = os.path.dirname(HERE)
if ROBOT_MOD not in sys.path:
    sys.path.insert(0, ROBOT_MOD)

from RobotTools.joint_inventory import (
    JointRecord,
    build_inventory_from_records,
    inventory_to_csv_rows,
    inventory_to_json,
    placement_axis_and_position,
    write_joint_inventory,
)


class _Vec:
    def __init__(self, x, y, z):
        self.x, self.y, self.z = x, y, z

    def __getitem__(self, i):
        return (self.x, self.y, self.z)[i]


class _Rot:
    def multVec(self, v):
        return _Vec(0.0, 0.0, 1.0)


class _Plc:
    def __init__(self):
        self.Base = _Vec(1.5, 2.5, 3.5)
        self.Rotation = _Rot()


class TestPlacementSummary(unittest.TestCase):
    def test_axis_and_position(self):
        axis, pos, summary = placement_axis_and_position(_Plc())
        self.assertEqual(pos, [1.5, 2.5, 3.5])
        self.assertEqual(axis, [0.0, 0.0, 1.0])
        self.assertIn("pos=", summary)
        self.assertIn("axis=", summary)

    def test_none(self):
        axis, pos, summary = placement_axis_and_position(None)
        self.assertIsNone(axis)
        self.assertIsNone(pos)
        self.assertEqual(summary, "")


class TestJointInventoryExport(unittest.TestCase):
    def _sample(self):
        records = [
            JointRecord(
                name="GroundedJoint",
                label="Grounded",
                type="Grounded",
                part1="Base",
                grounded=True,
            ),
            JointRecord(
                name="Rev001",
                label="RotorHub",
                type="Revolute",
                part1="Base",
                part2="Arm",
                grounded=True,
                axis=[0.0, 0.0, 1.0],
                position=[10.0, 0.0, 5.0],
                placement_summary="pos=(10,0,5) axis=(0,0,1)",
                angle_min=-180.0,
                angle_max=180.0,
                angle_limits_enabled=True,
            ),
            JointRecord(
                name="Slide001",
                label="Rail",
                type="Slider",
                part1="Arm",
                part2="Carriage",
                axis=[1.0, 0.0, 0.0],
                position=[20.0, 0.0, 5.0],
                length_min=0.0,
                length_max=100.0,
                length_limits_enabled=True,
            ),
        ]
        return build_inventory_from_records(
            records, assembly="DroneAsm", document="Doc", notes=["unit test"]
        )

    def test_json_schema(self):
        inv = self._sample()
        data = json.loads(inventory_to_json(inv))
        self.assertEqual(data["schema"], "freecad.robot.joint_inventory")
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["joint_count"], 3)
        self.assertEqual(data["grounded_count"], 2)
        self.assertEqual(len(data["joints"]), 3)
        types = {j["type"] for j in data["joints"]}
        self.assertEqual(types, {"Grounded", "Revolute", "Slider"})
        rev = next(j for j in data["joints"] if j["name"] == "Rev001")
        self.assertEqual(rev["axis"], [0.0, 0.0, 1.0])
        self.assertEqual(rev["part1"], "Base")
        self.assertEqual(rev["part2"], "Arm")
        self.assertIn("drone", data["purpose"].lower())

    def test_csv_and_write(self):
        inv = self._sample()
        rows = inventory_to_csv_rows(inv)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[1]["type"], "Revolute")
        self.assertEqual(rows[1]["axis_z"], 1.0)
        with tempfile.TemporaryDirectory() as tmp:
            json_path = os.path.join(tmp, "joints.json")
            paths = write_joint_inventory(inv, json_path)
            self.assertTrue(os.path.isfile(paths["json"]))
            self.assertTrue(os.path.isfile(paths["csv"]))
            with open(paths["csv"]) as fh:
                header = fh.readline()
            self.assertIn("name", header)
            self.assertIn("grounded", header)
            self.assertIn("axis_x", header)


if __name__ == "__main__":
    unittest.main()
