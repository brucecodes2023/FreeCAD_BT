# SPDX-License-Identifier: LGPL-2.1-or-later

# ***************************************************************************
# *   Copyright (c) 2026 FreeCAD contributors                              *
# *                                                                         *
# *   This file is part of FreeCAD.                                         *
# *                                                                         *
# *   FreeCAD is free software: you can redistribute it and/or modify it    *
# *   under the terms of the GNU Lesser General Public License as           *
# *   published by the Free Software Foundation, either version 2.1 of the  *
# *   License, or (at your option) any later version.                       *
# *                                                                         *
# *   FreeCAD is distributed in the hope that it will be useful, but        *
# *   WITHOUT ANY WARRANTY; without even the implied warranty of            *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU      *
# *   Lesser General Public License for more details.                       *
# *                                                                         *
# *   You should have received a copy of the GNU Lesser General Public      *
# *   License along with FreeCAD. If not, see                               *
# *   <https://www.gnu.org/licenses/>.                                      *
# *                                                                         *
# ***************************************************************************

__title__ = "FEM study presets and guided-study checklist"
__author__ = "FreeCAD contributors"
__url__ = "https://www.freecad.org"

## @package study_presets
#  \ingroup FEM
#  \brief CalculiX static/thermal study presets and analysis readiness checks

from dataclasses import dataclass

import ObjectsFem

from . import membertools


@dataclass(frozen=True)
class GuidedScenario:
    """Named CalculiX (or similar) setup for common product cases.

    These are *not* CFD. They wrap static structural or pure-heat thermal
    presets for drone frames, robot arms, and electronics heat - cases FreeCAD
    FEM can already run.
    """

    id: str
    title: str
    description: str
    setup: str  # name of setup_* function in this module
    tags: tuple[str, ...] = ()
    next_steps: str = ""


_GUIDED_SCENARIOS: tuple[GuidedScenario, ...] = (
    GuidedScenario(
        id="drone_frame_static",
        title="Drone / robot frame (static structural)",
        description=(
            "CalculiX static analysis for airframe spars, landing gear, "
            "or robot linkages under gravity / payload loads."
        ),
        setup="setup_calculix_static_study",
        tags=("drone", "robot", "structural", "calculix"),
        next_steps=(
            "Mesh the part, set solid material (E, nu), add Fixed + Force/Pressure "
            "(or SelfWeight), then Guided Study Wizard -> Run."
        ),
    ),
    GuidedScenario(
        id="robot_mount_static",
        title="Mount / bracket (static structural)",
        description=(
            "CalculiX static analysis for motor mounts, servo brackets, "
            "and fastener pads - same solver path as drone frame."
        ),
        setup="setup_calculix_static_study",
        tags=("robot", "drone", "structural", "calculix"),
        next_steps=(
            "Mesh the bracket, assign material, restrain bolt holes (Fixed), "
            "apply Force on the load face, then run the solver."
        ),
    ),
    GuidedScenario(
        id="electronics_thermal",
        title="Electronics / motor thermal",
        description=(
            "CalculiX pure heat transfer for ESCs, battery packs, or motor "
            "housings. Not coupled CFD cooling."
        ),
        setup="setup_calculix_thermal_study",
        tags=("drone", "robot", "thermal", "calculix"),
        next_steps=(
            "Mesh the solid, set thermal material properties, add Temperature / "
            "HeatFlux / Convective heat flux constraints, then run."
        ),
    ),
)


def list_guided_scenarios(tag: str | None = None) -> list[GuidedScenario]:
    """Return built-in guided scenarios, optionally filtered by tag."""
    scenarios = list(_GUIDED_SCENARIOS)
    if tag:
        scenarios = [s for s in scenarios if tag in s.tags]
    return scenarios


def get_guided_scenario(scenario_id: str) -> GuidedScenario | None:
    for scenario in _GUIDED_SCENARIOS:
        if scenario.id == scenario_id:
            return scenario
    return None


def setup_guided_scenario(
    doc,
    scenario_id: str,
    analysis=None,
    add_material: bool = True,
):
    """Run the CalculiX preset behind *scenario_id*.

    Returns ``(analysis, solver, material, scenario)``.
    Raises ``KeyError`` for unknown ids.
    """
    scenario = get_guided_scenario(scenario_id)
    if scenario is None:
        raise KeyError(f"Unknown guided scenario: {scenario_id}")
    setup_fn = globals()[scenario.setup]
    analysis, solver, material = setup_fn(doc, analysis=analysis, add_material=add_material)
    return analysis, solver, material, scenario


def format_scenario_catalog(tag: str | None = None) -> str:
    lines = []
    for scenario in list_guided_scenarios(tag=tag):
        tags = ",".join(scenario.tags)
        lines.append(f"{scenario.id}: {scenario.title} - {scenario.description} [{tags}]")
    return "\n".join(lines) if lines else "(no guided scenarios)"


def _member_objects(items):
    """Unwrap AnalysisMember dicts to document objects."""
    objects = []
    for item in items:
        obj = item["Object"] if isinstance(item, dict) else item
        if obj not in objects:
            objects.append(obj)
    return objects


def get_study_checklist(analysis):
    """Return mesh / material / constraint / solver presence for *analysis*.

    Reuses :func:`femtools.membertools.get_member` and
    :class:`femtools.membertools.AnalysisMember`. Does not create a solver.
    """
    if analysis is None:
        raise ValueError("Analysis must not be None")

    member = membertools.AnalysisMember(analysis)
    meshes = membertools.get_member(analysis, "Fem::FemMeshObject")
    if not meshes:
        meshes = [
            obj
            for obj in analysis.Group
            if obj.isDerivedFrom("Fem::FemMeshObject")
            and not (obj.hasExtension("App::SuppressibleExtension") and obj.Suppressed)
        ]
    materials = _member_objects(member.mats_linear)
    if not materials:
        materials = membertools.get_member(analysis, "App::MaterialObjectPython")

    constraints = []
    for attr, value in vars(member).items():
        if attr.startswith("cons_") and value:
            for obj in _member_objects(value):
                if obj not in constraints:
                    constraints.append(obj)
    for obj in analysis.Group:
        type_id = getattr(obj, "TypeId", "")
        if "Constraint" in type_id and "Constant" not in type_id:
            if obj not in constraints:
                constraints.append(obj)

    solvers = membertools.get_member(analysis, "Fem::FemSolverObjectPython")
    if not solvers:
        solvers = [obj for obj in analysis.Group if obj.isDerivedFrom("Fem::FemSolverObject")]

    has_mesh = bool(meshes)
    has_material = bool(materials)
    has_constraint = bool(constraints)
    has_solver = bool(solvers)
    return {
        "meshes": meshes,
        "materials": materials,
        "constraints": constraints,
        "solvers": solvers,
        "has_mesh": has_mesh,
        "has_material": has_material,
        "has_constraint": has_constraint,
        "has_solver": has_solver,
        "ready": has_mesh and has_material and has_constraint,
    }


def setup_calculix_static_study(doc, analysis=None, add_material=True):
    """Create or reuse an analysis with a CalculiX static solver.

    Does not create a mesh. Optionally adds an empty solid material skeleton.
    """
    if analysis is None:
        analysis = ObjectsFem.makeAnalysis(doc, "CalculiXStaticStudy")
    solver = ObjectsFem.makeSolverCalculiX(doc, "SolverCalculiX")
    solver.AnalysisType = "static"
    analysis.addObject(solver)
    material = None
    if add_material:
        material = ObjectsFem.makeMaterialSolid(doc, "MaterialSolid")
        analysis.addObject(material)
    return analysis, solver, material


def setup_calculix_thermal_study(doc, analysis=None, add_material=True):
    """Create or reuse an analysis with a CalculiX pure-heat thermal solver.

    Uses AnalysisType ``thermomech`` and ThermoMechType ``pure heat transfer``
    when that property exists. Does not create a mesh.
    """
    if analysis is None:
        analysis = ObjectsFem.makeAnalysis(doc, "CalculiXThermalStudy")
    solver = ObjectsFem.makeSolverCalculiX(doc, "SolverCalculiX")
    solver.AnalysisType = "thermomech"
    if hasattr(solver, "ThermoMechType"):
        solver.ThermoMechType = "pure heat transfer"
    analysis.addObject(solver)
    material = None
    if add_material:
        material = ObjectsFem.makeMaterialSolid(doc, "MaterialSolid")
        analysis.addObject(material)
    return analysis, solver, material
