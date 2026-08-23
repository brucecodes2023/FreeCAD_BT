# SPDX-License-Identifier: LGPL-2.1-or-later
"""Unit tests for RobotTools.chain_graph (no FreeCAD required)."""

import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROBOT_MOD = os.path.dirname(HERE)
if ROBOT_MOD not in sys.path:
    sys.path.insert(0, ROBOT_MOD)

from RobotTools.chain_graph import order_serial_chain, pad_dh_rows, write_kinematic_csv


class TestOrderSerialChain(unittest.TestCase):
    def test_empty(self):
        ordered, topo, msgs = order_serial_chain([])
        self.assertEqual(ordered, [])
        self.assertEqual(topo, "empty")
        self.assertTrue(msgs)

    def test_serial_three(self):
        edges = [("A", "B", "j1"), ("B", "C", "j2")]
        ordered, topo, msgs = order_serial_chain(edges)
        self.assertEqual(topo, "serial")
        self.assertEqual(set(ordered), {"j1", "j2"})
        self.assertEqual(len(ordered), 2)

    def test_branched(self):
        edges = [("A", "B", "j1"), ("B", "C", "j2"), ("B", "D", "j3")]
        ordered, topo, msgs = order_serial_chain(edges)
        self.assertEqual(topo, "branched")
        self.assertEqual(len(ordered), 2)
        self.assertTrue(any("Branched" in m or "branched" in m.lower() for m in msgs))

    def test_disconnected(self):
        edges = [("A", "B", "j1"), ("C", "D", "j2"), ("D", "E", "j3")]
        ordered, topo, msgs = order_serial_chain(edges)
        self.assertEqual(topo, "disconnected")
        self.assertEqual(set(ordered), {"j2", "j3"})


class TestKinematicCsv(unittest.TestCase):
    def test_pad_and_write(self):
        rows = [(100, -90, 0, 0, 1, 180, -180, 90)]
        padded = pad_dh_rows(rows, 6)
        self.assertEqual(len(padded), 6)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "kin.csv")
            write_kinematic_csv(path, rows)
            with open(path) as fh:
                lines = fh.read().strip().splitlines()
            self.assertEqual(len(lines), 7)
            self.assertTrue(lines[0].startswith("a,"))


if __name__ == "__main__":
    unittest.main()
