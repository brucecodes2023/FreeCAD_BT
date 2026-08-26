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
    ACTION_CREATE_SAMPLE_CUBE,
    DESIGN_WORKBENCH_ORDER,
    FEM_WIZARD_STEPS,
    FOAM_WIZARD_STEPS,
    PHYSICS_FLUIDS,
    PHYSICS_STRUCTURES,
    STATE_COMING,
    STATE_CURRENT,
    STATE_LOCKED,
    STATE_PASSED,
    WizardFacts,
    characteristic_length,
    evaluate_wizard,
    foam_case_tree_ready,
    geometry_hint,
    geometry_ready,
    merge_workbench_order,
    steps_for_physics,
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
        geo = next(s for s in FEM_WIZARD_STEPS if s["id"] == "geometry")
        self.assertEqual(geo["action"], ACTION_CREATE_SAMPLE_CUBE)

    def test_foam_wizard_writes_before_solve(self):
        ids = [s["id"] for s in FOAM_WIZARD_STEPS]
        self.assertEqual(ids[0], "geometry")
        self.assertIn("write", ids)
        self.assertLess(ids.index("write"), ids.index("solve"))
        write = next(s for s in FOAM_WIZARD_STEPS if s["id"] == "write")
        self.assertEqual(write["command"], "BtStudio_FoamWriteCase")
        geo = next(s for s in FOAM_WIZARD_STEPS if s["id"] == "geometry")
        self.assertEqual(geo["action"], ACTION_CREATE_SAMPLE_CUBE)
        mesh = next(s for s in FOAM_WIZARD_STEPS if s["id"] == "mesh")
        self.assertTrue(mesh.get("coming"))


class TestWizardGating(unittest.TestCase):
    def test_geometry_ready_requires_named_solid(self):
        self.assertFalse(geometry_ready([], False))
        self.assertFalse(geometry_ready(["Box"], False))
        self.assertFalse(geometry_ready([], True))
        self.assertTrue(geometry_ready(["Box"], True))

    def test_geometry_ready_with_foam_link(self):
        self.assertTrue(geometry_ready([], False, geometry_link_set=True))
        self.assertTrue(geometry_ready((), False, True))

    def test_geometry_hint_tells_you_to_create_or_pick(self):
        hint = geometry_hint([], False)
        self.assertIn("Create sample cube", hint)
        self.assertIn("No solid selected", hint)
        self.assertIn("Cube", geometry_hint(["Cube"], True))

    def test_empty_fluids_starts_at_geometry_with_run(self):
        view = evaluate_wizard(WizardFacts(physics=PHYSICS_FLUIDS))
        self.assertEqual([s.id for s in view.steps], [s["id"] for s in FOAM_WIZARD_STEPS])
        geo = view.steps[0]
        self.assertEqual(geo.state, STATE_CURRENT)
        self.assertTrue(geo.run_enabled)
        self.assertEqual(geo.run_label, "Create sample cube")
        self.assertEqual(geo.action, ACTION_CREATE_SAMPLE_CUBE)
        self.assertEqual(view.current_id, "geometry")
        self.assertEqual(view.steps[1].state, STATE_LOCKED)
        self.assertFalse(view.steps[1].run_enabled)
        self.assertEqual(view.steps[-2].state, STATE_COMING)
        self.assertEqual(view.steps[-1].state, STATE_COMING)
        self.assertFalse(view.steps[-2].run_enabled)
        self.assertFalse(view.foam_settings_enabled)
        self.assertEqual(view.output_path, "")

    def test_geometry_unlocks_case_only(self):
        view = evaluate_wizard(
            WizardFacts(selection_names=("Cube",), has_shape=True)
        )
        by_id = {s.id: s for s in view.steps}
        self.assertEqual(by_id["geometry"].state, STATE_PASSED)
        self.assertFalse(by_id["geometry"].run_enabled)
        self.assertEqual(by_id["case"].state, STATE_CURRENT)
        self.assertTrue(by_id["case"].run_enabled)
        self.assertEqual(by_id["write"].state, STATE_LOCKED)
        self.assertFalse(by_id["write"].run_enabled)

    def test_foam_geometry_link_counts_without_selection(self):
        view = evaluate_wizard(WizardFacts(geometry_link_set=True))
        self.assertEqual(view.current_id, "case")
        self.assertEqual(view.steps[0].state, STATE_PASSED)

    def test_case_unlocks_write(self):
        view = evaluate_wizard(
            WizardFacts(
                selection_names=("Cube",),
                has_shape=True,
                has_foam_case=True,
            )
        )
        by_id = {s.id: s for s in view.steps}
        self.assertEqual(by_id["case"].state, STATE_PASSED)
        self.assertEqual(by_id["write"].state, STATE_CURRENT)
        self.assertTrue(by_id["write"].run_enabled)
        self.assertTrue(view.foam_settings_enabled)
        self.assertEqual(view.output_path, "")

    def test_write_requires_control_dict_and_u(self):
        incomplete = evaluate_wizard(
            WizardFacts(
                selection_names=("Cube",),
                has_shape=True,
                has_foam_case=True,
                case_path="/tmp/FoamCase",
                case_files=("system/controlDict",),
            )
        )
        self.assertEqual(incomplete.current_id, "write")
        self.assertEqual(incomplete.output_path, "")

        done = evaluate_wizard(
            WizardFacts(
                selection_names=("Cube",),
                has_shape=True,
                has_foam_case=True,
                case_path="/tmp/FoamCase",
                case_files=("system/controlDict", "0/U"),
            )
        )
        by_id = {s.id: s for s in done.steps}
        self.assertEqual(by_id["write"].state, STATE_PASSED)
        self.assertFalse(by_id["write"].run_enabled)
        self.assertEqual(by_id["mesh"].state, STATE_COMING)
        self.assertEqual(by_id["solve"].state, STATE_COMING)
        self.assertIsNone(done.current_id)
        self.assertEqual(done.output_path, "/tmp/FoamCase")
        self.assertIn("/tmp/FoamCase", by_id["write"].hint)

    def test_foam_case_tree_ready_filesystem(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(foam_case_tree_ready(tmp))
            os.makedirs(os.path.join(tmp, "system"))
            os.makedirs(os.path.join(tmp, "0"))
            with open(os.path.join(tmp, "system", "controlDict"), "w", encoding="utf-8") as fh:
                fh.write("application simpleFoam;\n")
            self.assertFalse(foam_case_tree_ready(tmp))
            with open(os.path.join(tmp, "0", "U"), "w", encoding="utf-8") as fh:
                fh.write("internalField uniform (1 0 0);\n")
            self.assertTrue(foam_case_tree_ready(tmp))
        self.assertFalse(foam_case_tree_ready(""))
        self.assertTrue(
            foam_case_tree_ready("/unused", ("system/controlDict", "0/U"))
        )

    def test_only_current_run_is_enabled(self):
        snapshots = [
            WizardFacts(),
            WizardFacts(selection_names=("Cube",), has_shape=True),
            WizardFacts(selection_names=("Cube",), has_shape=True, has_foam_case=True),
            WizardFacts(
                selection_names=("Cube",),
                has_shape=True,
                has_foam_case=True,
                case_path="/tmp/x",
                case_files=("system/controlDict", "0/U"),
            ),
            WizardFacts(physics=PHYSICS_STRUCTURES),
            WizardFacts(
                physics=PHYSICS_STRUCTURES,
                selection_names=("Cube",),
                has_shape=True,
                has_analysis=True,
            ),
            WizardFacts(
                physics=PHYSICS_STRUCTURES,
                selection_names=("Cube",),
                has_shape=True,
                has_analysis=True,
                has_material=True,
                has_constraint=True,
                has_mesh=True,
                has_solver_run=True,
                has_results=True,
            ),
        ]
        for facts in snapshots:
            view = evaluate_wizard(facts)
            enabled = [s.id for s in view.steps if s.run_enabled]
            self.assertLessEqual(len(enabled), 1, facts)
            if view.current_id:
                self.assertEqual(enabled, [view.current_id])
            for step in view.steps:
                if step.coming or step.state in (STATE_LOCKED, STATE_PASSED, STATE_COMING):
                    self.assertFalse(step.run_enabled, step)
                if step.state == STATE_CURRENT:
                    self.assertTrue(step.run_enabled, step)
                    self.assertFalse(step.coming)

    def test_switching_physics_rebuilds_step_ids(self):
        fem = evaluate_wizard(WizardFacts(physics=PHYSICS_STRUCTURES))
        foam = evaluate_wizard(WizardFacts(physics=PHYSICS_FLUIDS))
        self.assertEqual(steps_for_physics(PHYSICS_STRUCTURES), FEM_WIZARD_STEPS)
        self.assertNotEqual([s.id for s in fem.steps], [s.id for s in foam.steps])
        self.assertIn("analysis", [s.id for s in fem.steps])
        self.assertNotIn("write", [s.id for s in fem.steps])
        self.assertIn("write", [s.id for s in foam.steps])
        with self.assertRaises(ValueError):
            steps_for_physics("electromagnetics")

    def test_fem_gates_analysis_until_geometry(self):
        empty = evaluate_wizard(WizardFacts(physics=PHYSICS_STRUCTURES))
        self.assertEqual(empty.current_id, "geometry")
        self.assertTrue(empty.steps[0].run_enabled)
        self.assertEqual(empty.steps[0].run_label, "Create sample cube")
        self.assertEqual(empty.steps[1].state, STATE_LOCKED)
        ready = evaluate_wizard(
            WizardFacts(
                physics=PHYSICS_STRUCTURES,
                selection_names=("Cube",),
                has_shape=True,
            )
        )
        self.assertEqual(ready.current_id, "analysis")
        self.assertTrue(ready.steps[1].run_enabled)
        self.assertFalse(ready.foam_settings_enabled)

    def test_fem_mesh_is_not_coming(self):
        view = evaluate_wizard(
            WizardFacts(
                physics=PHYSICS_STRUCTURES,
                selection_names=("Cube",),
                has_shape=True,
                has_analysis=True,
                has_material=True,
                has_constraint=True,
            )
        )
        mesh = next(s for s in view.steps if s.id == "mesh")
        self.assertEqual(mesh.state, STATE_CURRENT)
        self.assertFalse(mesh.coming)
        self.assertEqual(mesh.command, "BtStudio_FemAutoMesh")

    def test_locked_hint_names_the_current_step(self):
        view = evaluate_wizard(WizardFacts())
        self.assertIn("Select solid geometry", view.steps[1].hint)
        self.assertIn("Locked", view.steps[1].hint)

    def test_core_module_does_not_import_freecad(self):
        import inspect
        import btstudio.core as core

        source = inspect.getsource(core)
        self.assertNotIn("import FreeCAD", source)
        self.assertNotIn("from FreeCAD", source)

    def test_wizard_modules_import_without_freecad(self):
        from btstudio.foam_wizard import show_wizard as foam_show
        from btstudio.fem_wizard import show_wizard as fem_show
        from btstudio.analysis_wizard import create_sample_cube

        self.assertTrue(callable(foam_show))
        self.assertTrue(callable(fem_show))
        self.assertTrue(callable(create_sample_cube))

    def test_closed_wizard_is_not_alive(self):
        from btstudio.analysis_wizard import _dock_alive

        self.assertFalse(_dock_alive(None))

        class Dead:
            widget = None

        self.assertFalse(_dock_alive(Dead()))


    def test_safe_named_attr_skips_pyqtribbon_getattr(self):
        from btstudio.core import safe_named_attr

        class Boom:
            def __getattr__(self, name):
                assert False, "Invalid method name"

            def rightToolBar(self):
                return "ok"

        boom = Boom()
        with self.assertRaises(AssertionError):
            hasattr(boom, "notARealMethod")
        self.assertTrue(callable(safe_named_attr(boom, "rightToolBar")))
        self.assertIsNone(safe_named_attr(boom, "notARealMethod"))


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
            view = evaluate_wizard(
                WizardFacts(
                    selection_names=("Cube",),
                    has_shape=True,
                    has_foam_case=True,
                    case_path=tmp,
                    case_files=None,
                )
            )
            by_id = {s.id: s for s in view.steps}
            self.assertEqual(by_id["write"].state, STATE_PASSED)
            self.assertEqual(view.output_path, tmp)
            self.assertEqual(by_id["mesh"].state, STATE_COMING)
            self.assertFalse(by_id["mesh"].run_enabled)

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
