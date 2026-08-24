# SPDX-License-Identifier: LGPL-2.1-or-later

"""Headless tests for BtStudio (no GUI). Run: python3 -m btstudio.tests
or via FreeCADCmd unit-test hook.
"""

from __future__ import annotations

import os
import sys
import unittest

# Allow `python3 -m btstudio.tests` from src/Mod/BtStudio
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from btstudio.core import (  # noqa: E402
    DESIGN_WORKBENCH_ORDER,
    FEM_WIZARD_STEPS,
    characteristic_length,
    merge_workbench_order,
)
from solvers.registry import PHYSICS, by_domain, planned_backends  # noqa: E402
from solvers.openfoam import case_tree  # noqa: E402


class TestCore(unittest.TestCase):
    def test_characteristic_length(self):
        self.assertEqual(characteristic_length(100.0, 20.0), 5.0)
        self.assertGreater(characteristic_length(1e-12), 0.0)
        with self.assertRaises(ValueError):
            characteristic_length(0)

    def test_workbench_order_puts_design_first(self):
        known = ["FemWorkbench", "MeshWorkbench", "SketcherWorkbench", "StartWorkbench"]
        out = merge_workbench_order(known)
        self.assertEqual(out[0], "StartWorkbench")
        self.assertLess(out.index("SketcherWorkbench"), out.index("FemWorkbench"))
        self.assertIn("MeshWorkbench", out)
        self.assertEqual(len(out), len(set(out)))

    def test_preferred_list_is_stable(self):
        self.assertIn("PartDesignWorkbench", DESIGN_WORKBENCH_ORDER)
        self.assertEqual(DESIGN_WORKBENCH_ORDER[1], "SketcherWorkbench")

    def test_mac_pad_skips_file_and_menu_toolbars(self):
        from btstudio.core import skip_mac_pad_toolbar

        self.assertTrue(skip_mac_pad_toolbar("File"))
        self.assertTrue(skip_mac_pad_toolbar("Menu"))
        self.assertTrue(skip_mac_pad_toolbar("File toolbar", "MenuBarLeftArea"))
        self.assertFalse(skip_mac_pad_toolbar("Structure"))

    def test_traffic_lights_are_top_left_mac_order(self):
        from btstudio.core import traffic_light_layout

        rects = traffic_light_layout(800, 28)
        self.assertEqual(list(rects), ["close", "min", "zoom"])
        close, mini, zoom = rects["close"], rects["min"], rects["zoom"]
        self.assertLess(close[0], mini[0])
        self.assertLess(mini[0], zoom[0])
        self.assertLess(close[0], 20)
        self.assertEqual(close[2], mini[2])
        # Stay on the left half of a typical title bar.
        self.assertLess(zoom[0] + zoom[2], 400)

    def test_wizard_has_mesh_and_solve(self):
        ids = [s["id"] for s in FEM_WIZARD_STEPS]
        self.assertEqual(ids[0], "geometry")
        self.assertIn("mesh", ids)
        self.assertIn("solve", ids)
        mesh = next(s for s in FEM_WIZARD_STEPS if s["id"] == "mesh")
        self.assertEqual(mesh["command"], "BtStudio_FemAutoMesh")


class TestSolvers(unittest.TestCase):
    def test_openfoam_is_planned(self):
        self.assertIn("openfoam", planned_backends())
        fluids = by_domain("fluids")
        self.assertTrue(any(p["id"] == "openfoam_incompressible" for p in fluids))

    def test_existing_backends_still_listed(self):
        ids = {p["id"] for p in PHYSICS}
        self.assertIn("elasticity", ids)
        self.assertIn("mbd", ids)

    def test_openfoam_case_protocol(self):
        tree = case_tree()
        self.assertIn("0", tree["dirs"])
        self.assertIn("system/controlDict", tree["files"])
        self.assertIn("simpleFoam", tree["solvers"])


class TestDocsPresent(unittest.TestCase):
    def test_guides_exist(self):
        docs = os.path.join(_ROOT, "docs")
        for name in (
            "FEM_THEORY_GUIDE.md",
            "FIRST_PRINCIPLES.md",
            "ANSYS_MESHING_MAP.md",
            "OPENFOAM_ARCHITECTURE.md",
        ):
            path = os.path.join(docs, name)
            self.assertTrue(os.path.isfile(path), path)
            with open(path, encoding="utf-8") as fh:
                self.assertGreater(len(fh.read()), 400)


def test():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromModule(sys.modules[__name__]))
    runner = unittest.TextTestRunner()
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    sys.exit(0 if test() else 1)
