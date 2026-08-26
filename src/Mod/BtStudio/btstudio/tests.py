# SPDX-License-Identifier: LGPL-2.1-or-later

"""Headless tests for BtStudio (no GUI). Run: python3 -m btstudio.tests
or via FreeCADCmd unit-test hook.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

# Allow `python3 -m btstudio.tests` from src/Mod/BtStudio
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from btstudio.core import (  # noqa: E402
    DESIGN_WORKBENCH_ORDER,
    FEM_WIZARD_STEPS,
    FOAM_WIZARD_STEPS,
    characteristic_length,
    merge_workbench_order,
)
from solvers.registry import PHYSICS, by_domain, planned_backends  # noqa: E402
from solvers.openfoam import case_tree  # noqa: E402
from solvers.foam_write import FoamCaseSpec, case_files, write_case  # noqa: E402


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

    def test_foam_wizard_writes_before_solve(self):
        ids = [s["id"] for s in FOAM_WIZARD_STEPS]
        self.assertEqual(ids[0], "geometry")
        self.assertIn("write", ids)
        self.assertLess(ids.index("write"), ids.index("solve"))
        write = next(s for s in FOAM_WIZARD_STEPS if s["id"] == "write")
        self.assertEqual(write["command"], "BtStudio_FoamWriteCase")


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
        self.assertIn("system/blockMeshDict", tree["files"])
        self.assertIn("simpleFoam", tree["solvers"])
        self.assertIn("simpleFoam", tree["incompressible"])
        self.assertNotIn("rhoSimpleFoam", tree["incompressible"])


class TestFoamWriter(unittest.TestCase):
    def test_default_case_has_protocol_files(self):
        files = case_files(FoamCaseSpec())
        for rel in (
            "system/controlDict",
            "system/fvSchemes",
            "system/fvSolution",
            "system/blockMeshDict",
            "constant/transportProperties",
            "constant/turbulenceProperties",
            "0/U",
            "0/p",
        ):
            self.assertIn(rel, files)
            self.assertGreater(len(files[rel]), 40)
        self.assertNotIn("0/k", files)

    def test_control_dict_names_simplefoam(self):
        text = case_files(FoamCaseSpec())["system/controlDict"]
        self.assertIn("application     simpleFoam;", text)
        self.assertIn("endTime         100;", text)

    def test_bbox_converts_millimetres_to_metres(self):
        spec = FoamCaseSpec(bbox_mm=(0.0, 100.0, 0.0, 50.0, 0.0, 10.0))
        mesh = case_files(spec)["system/blockMeshDict"]
        self.assertIn("( 0 0 0 )", mesh)
        self.assertIn("( 0.1 0.05 0.01 )", mesh)
        self.assertIn("hex (0 1 2 3 4 5 6 7) (20 20 1)", mesh)
        self.assertIn("inlet", mesh)
        self.assertIn("outlet", mesh)
        self.assertIn("walls", mesh)

    def test_inlet_velocity_and_walls(self):
        u = case_files(FoamCaseSpec(inlet_velocity=(2.5, 0.0, 0.0)))["0/U"]
        self.assertIn("uniform (2.5 0 0)", u)
        self.assertIn("noSlip", u)
        p = case_files(FoamCaseSpec())["0/p"]
        self.assertIn("fixedValue", p)

    def test_komega_adds_turbulence_fields(self):
        files = case_files(FoamCaseSpec(turbulence="kOmegaSST"))
        self.assertIn("0/k", files)
        self.assertIn("0/omega", files)
        self.assertNotIn("0/epsilon", files)
        self.assertIn("kOmegaSST", files["constant/turbulenceProperties"])

    def test_pimple_uses_euler(self):
        schemes = case_files(FoamCaseSpec(application="pimpleFoam"))["system/fvSchemes"]
        self.assertIn("Euler", schemes)

    def test_write_case_creates_tree(self):
        spec = FoamCaseSpec()
        with tempfile.TemporaryDirectory() as tmp:
            written = write_case(tmp, spec)
            self.assertIn("system/controlDict", written)
            self.assertTrue(os.path.isfile(os.path.join(tmp, "0", "U")))
            self.assertTrue(os.path.isfile(os.path.join(tmp, "constant", "transportProperties")))

    def test_rejects_bad_spec(self):
        with self.assertRaises(ValueError):
            FoamCaseSpec(application="rhoSimpleFoam")
        with self.assertRaises(ValueError):
            FoamCaseSpec(bbox_mm=(0, 0, 0, 1, 0, 1))
        with self.assertRaises(ValueError):
            FoamCaseSpec(nu=0)
        with self.assertRaises(ValueError):
            FoamCaseSpec(end_time=0, start_time=1)


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
