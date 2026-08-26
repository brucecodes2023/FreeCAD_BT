# SPDX-License-Identifier: LGPL-2.1-or-later

"""Pure helpers for BtStudio — no FreeCAD import, so tests can run with python3."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

DESIGN_WORKBENCH_ORDER = [
    "StartWorkbench",
    "SketcherWorkbench",
    "PartWorkbench",
    "PartDesignWorkbench",
    "AssemblyWorkbench",
    "FemWorkbench",
    "DraftWorkbench",
    "TechDrawWorkbench",
    "CAMWorkbench",
    "BIMWorkbench",
    "MaterialWorkbench",
    "MeshWorkbench",
    "SurfaceWorkbench",
    "SpreadsheetWorkbench",
]

PHYSICS_STRUCTURES = "structures"
PHYSICS_FLUIDS = "fluids"

STATE_LOCKED = "locked"
STATE_CURRENT = "current"
STATE_PASSED = "passed"
STATE_COMING = "coming"

ACTION_CREATE_SAMPLE_CUBE = "create_sample_cube"
REQUIRED_FOAM_FILES = ("system/controlDict", "0/U")

FEM_WIZARD_STEPS = [
    {
        "id": "geometry",
        "title": "Select solid geometry",
        "hint": "Pick the Part or PartDesign body that will be meshed.",
        "command": None,
        "action": ACTION_CREATE_SAMPLE_CUBE,
        "run_label": "Create sample cube",
    },
    {
        "id": "analysis",
        "title": "Create analysis container",
        "hint": "Adds Fem::Analysis and the default solver.",
        "command": "FEM_Analysis",
    },
    {
        "id": "material",
        "title": "Assign a solid material",
        "hint": "Card must reference the solid (E, nu, density as needed).",
        "command": "FEM_MaterialSolid",
    },
    {
        "id": "constraints",
        "title": "Apply restraints and loads",
        "hint": "At least one essential BC (fixed/displacement) plus loads.",
        "command": "FEM_ConstraintFixed",
    },
    {
        "id": "mesh",
        "title": "Auto mesh (then refine concentrations)",
        "hint": "Global h = bbox diagonal / 20. Add MeshRegion on fillets.",
        "command": "BtStudio_FemAutoMesh",
    },
    {
        "id": "solve",
        "title": "Run the solver",
        "hint": "Writes the input deck and launches CalculiX/Elmer.",
        "command": "FEM_SolverRun",
    },
    {
        "id": "results",
        "title": "Show results",
        "hint": "Check reactions and mesh convergence, not just the peak node.",
        "command": "FEM_ResultShow",
    },
]

FOAM_WIZARD_STEPS = [
    {
        "id": "geometry",
        "title": "Select solid geometry",
        "hint": "Pick the Part or PartDesign body. Its bounding box becomes blockMesh (mm → m).",
        "command": None,
        "action": ACTION_CREATE_SAMPLE_CUBE,
        "run_label": "Create sample cube",
    },
    {
        "id": "case",
        "title": "Create FoamCase",
        "hint": "Adds a FoamCase object. Solver defaults to simpleFoam, laminar, nu = 1e-5 m^2/s.",
        "command": "BtStudio_FoamNewCase",
    },
    {
        "id": "write",
        "title": "Write case tree",
        "hint": "Emits 0/, constant/, system/ next to the document. Does not run OpenFOAM.",
        "command": "BtStudio_FoamWriteCase",
    },
    {
        "id": "mesh",
        "title": "Mesh (later)",
        "hint": "blockMesh / snappyHexMesh stay off this slice. Install OpenFOAM and run them by hand to check the case.",
        "command": None,
        "coming": True,
    },
    {
        "id": "solve",
        "title": "Solve (later)",
        "hint": "simpleFoam via QProcess is the next slice. Residual logs will land in the Report view.",
        "command": None,
        "coming": True,
    },
]


def characteristic_length(diagonal: float, divisor: float = 20.0) -> float:
    """Global mesh size from a bounding-box diagonal (ANSYS body-sizing analogue)."""
    if diagonal <= 0 or divisor <= 0:
        raise ValueError("diagonal and divisor must be positive")
    return max(diagonal / divisor, 1e-6)


MAC_CHROME_SKIP_TOOLBARS = ("file", "menu", "edit", "workbench")

# macOS traffic-light geometry (close / minimize / zoom, left to right).
TRAFFIC_LIGHT_DIAMETER = 12
TRAFFIC_LIGHT_GAP = 8
TRAFFIC_LIGHT_LEFT = 10
TRAFFIC_LIGHT_BAR_HEIGHT = 28


def traffic_light_layout(
    width: int,
    height: int,
    *,
    diameter: int = TRAFFIC_LIGHT_DIAMETER,
    gap: int = TRAFFIC_LIGHT_GAP,
    left: int = TRAFFIC_LIGHT_LEFT,
) -> dict[str, tuple[int, int, int, int]]:
    """Return close/min/zoom rects (x, y, w, h) in the top-left of a title bar."""
    del width  # title-bar width is unused; lights are left-aligned
    y = max((height - diameter) // 2, 0)
    x = left
    out: dict[str, tuple[int, int, int, int]] = {}
    for name in ("close", "min", "zoom"):
        out[name] = (x, y, diameter, diameter)
        x += diameter + gap
    return out


def safe_named_attr(obj, name: str, default=None):
    """Read an attribute without triggering custom __getattr__.

    pyqtribbon widgets assert inside __getattr__ ('Invalid method name'),
    so hasattr()/getattr() crash FreeCAD on launch.
    """
    try:
        return object.__getattribute__(obj, name)
    except Exception:
        return default


def skip_mac_pad_toolbar(name: str, parent_name: str = "") -> bool:
    """True if injecting a spacer here would sit on File/Menu and pop the Menu overflow."""
    n = (name or "").lower()
    p = (parent_name or "").lower()
    if "menubar" in p:
        return True
    return any(token in n for token in MAC_CHROME_SKIP_TOOLBARS)


def merge_workbench_order(known: list[str], preferred: list[str] | None = None) -> list[str]:
    """Preferred first, then any remaining known workbenches in their original order."""
    pref = list(preferred or DESIGN_WORKBENCH_ORDER)
    seen = set()
    out: list[str] = []
    known_set = set(known)
    for name in pref:
        if name in known_set and name not in seen:
            out.append(name)
            seen.add(name)
    for name in known:
        if name not in seen and name != "NoneWorkbench":
            out.append(name)
            seen.add(name)
    return out


def geometry_ready(selection_names, has_shape, geometry_link_set: bool = False) -> bool:
    """True when a named selection has a solid Shape, or FoamCase.Geometry is set.

    ``has_shape`` is the GUI's Volume>0 check (tests pass a bool; no FreeCAD).
    """
    if geometry_link_set:
        return True
    names = [n for n in (selection_names or ()) if n]
    return bool(names) and bool(has_shape)


def foam_case_ready(has_foam_case: bool) -> bool:
    return bool(has_foam_case)


def foam_case_tree_ready(
    case_path: str,
    relative_files: Iterable[str] | None = None,
) -> bool:
    """Pass if CasePath has ``system/controlDict`` and ``0/U``.

    When ``relative_files`` is given, use that set (unit tests). Otherwise inspect
    the filesystem — still no FreeCAD import.
    """
    path = (case_path or "").strip()
    if not path:
        return False
    if relative_files is not None:
        have = set(relative_files)
        return all(name in have for name in REQUIRED_FOAM_FILES)
    root = Path(path)
    return (root / "system" / "controlDict").is_file() and (root / "0" / "U").is_file()


def steps_for_physics(physics: str) -> list[dict]:
    if physics == PHYSICS_STRUCTURES:
        return FEM_WIZARD_STEPS
    if physics == PHYSICS_FLUIDS:
        return FOAM_WIZARD_STEPS
    raise ValueError(f"unknown physics {physics!r}")


def step_is_coming(step: dict, physics: str) -> bool:
    if step.get("coming"):
        return True
    # Fluids mesh/solve stay locked until a later slice that can spawn OpenFOAM.
    return physics == PHYSICS_FLUIDS and step.get("id") in ("mesh", "solve") and not step.get(
        "command"
    )


@dataclass(frozen=True)
class WizardFacts:
    """Document facts the GUI collects. Gating stays FreeCAD-free."""

    physics: str = PHYSICS_FLUIDS
    selection_names: tuple[str, ...] = ()
    has_shape: bool = False
    geometry_link_set: bool = False
    has_foam_case: bool = False
    case_path: str = ""
    case_files: tuple[str, ...] | None = None
    has_analysis: bool = False
    has_material: bool = False
    has_constraint: bool = False
    has_mesh: bool = False
    has_solver_run: bool = False
    has_results: bool = False


@dataclass(frozen=True)
class StepView:
    id: str
    title: str
    hint: str
    command: str | None
    action: str | None
    state: str
    run_enabled: bool
    run_label: str
    coming: bool


@dataclass(frozen=True)
class WizardView:
    physics: str
    steps: tuple[StepView, ...]
    output_path: str
    current_id: str | None
    foam_settings_enabled: bool


def step_is_passed(step_id: str, facts: WizardFacts) -> bool:
    if step_id == "geometry":
        return geometry_ready(
            facts.selection_names,
            facts.has_shape,
            geometry_link_set=facts.geometry_link_set,
        )
    if step_id == "case":
        return foam_case_ready(facts.has_foam_case)
    if step_id == "write":
        return foam_case_tree_ready(facts.case_path, facts.case_files)
    if step_id == "analysis":
        return bool(facts.has_analysis)
    if step_id == "material":
        return bool(facts.has_material)
    if step_id == "constraints":
        return bool(facts.has_constraint)
    if step_id == "mesh":
        if facts.physics == PHYSICS_FLUIDS:
            return False
        return bool(facts.has_mesh)
    if step_id == "solve":
        if facts.physics == PHYSICS_FLUIDS:
            return False
        return bool(facts.has_solver_run)
    if step_id == "results":
        return bool(facts.has_results)
    return False


def geometry_hint(
    selection_names,
    has_shape,
    *,
    geometry_link_set: bool = False,
) -> str:
    if geometry_ready(selection_names, has_shape, geometry_link_set=geometry_link_set):
        names = [n for n in (selection_names or ()) if n]
        if names:
            return f"Solid '{names[0]}' is ready."
        if geometry_link_set:
            return "FoamCase.Geometry is set — solid is linked."
        return "Solid geometry is ready."
    names = [n for n in (selection_names or ()) if n]
    if not names:
        return "No solid selected — pick the cube or click Create sample cube."
    if not has_shape:
        return "Selection has no solid volume — pick a Part/PartDesign body or click Create sample cube."
    return "No solid selected — pick the cube or click Create sample cube."


def _contextual_hint(step: dict, facts: WizardFacts, state: str, current_title: str | None) -> str:
    sid = step["id"]
    if state == STATE_COMING:
        return step["hint"]
    if state == STATE_LOCKED:
        if current_title:
            return f"Locked — finish “{current_title}” first."
        return "Locked until the previous step is complete."
    if sid == "geometry":
        return geometry_hint(
            facts.selection_names,
            facts.has_shape,
            geometry_link_set=facts.geometry_link_set,
        )
    if state == STATE_PASSED:
        if sid == "case":
            return "FoamCase is in the document. Set solver / inlet velocity if needed, then write."
        if sid == "write" and facts.case_path:
            return f"Case tree written to {facts.case_path}."
        if sid == "analysis":
            return "Analysis container is in the document."
        if sid == "material":
            return "Solid material is assigned."
        if sid == "constraints":
            return "A restraint is on the analysis. Add loads if you have not already."
        if sid == "mesh":
            return "Mesh is present. Refine concentrations if needed, then solve."
        if sid == "solve":
            return "Solver has run. Continue to results."
        if sid == "results":
            return "Results are in the document."
        return step["hint"]
    # current
    if sid == "case" and not facts.has_foam_case:
        return "No FoamCase yet — click Run to add one (simpleFoam, laminar, nu = 1e-5 m^2/s)."
    if sid == "write":
        return "Ready to emit 0/, constant/, system/. Mesh and solve stay off this slice."
    return step["hint"]


def _run_label(step: dict) -> str:
    if step.get("run_label"):
        return str(step["run_label"])
    if step.get("action") == ACTION_CREATE_SAMPLE_CUBE:
        return "Create sample cube"
    if step.get("coming"):
        return "Coming"
    return "Run"


def evaluate_wizard(facts: WizardFacts, steps: list[dict] | None = None) -> WizardView:
    """Live status for each step. Only the current step has Run enabled."""
    physics = facts.physics
    catalog = list(steps if steps is not None else steps_for_physics(physics))
    current_id: str | None = None
    current_title: str | None = None
    for step in catalog:
        if step_is_coming(step, physics):
            continue
        if not step_is_passed(step["id"], facts):
            current_id = step["id"]
            current_title = step["title"]
            break

    views: list[StepView] = []
    for step in catalog:
        coming = step_is_coming(step, physics)
        sid = step["id"]
        if coming:
            state = STATE_COMING
        elif step_is_passed(sid, facts):
            state = STATE_PASSED
        elif sid == current_id:
            state = STATE_CURRENT
        else:
            state = STATE_LOCKED
        views.append(
            StepView(
                id=sid,
                title=step["title"],
                hint=_contextual_hint(step, facts, state, current_title),
                command=step.get("command"),
                action=step.get("action"),
                state=state,
                run_enabled=state == STATE_CURRENT,
                run_label=_run_label(step) if not coming else "Coming",
                coming=coming,
            )
        )

    output = ""
    if physics == PHYSICS_FLUIDS and foam_case_tree_ready(facts.case_path, facts.case_files):
        output = (facts.case_path or "").strip()

    return WizardView(
        physics=physics,
        steps=tuple(views),
        output_path=output,
        current_id=current_id,
        foam_settings_enabled=physics == PHYSICS_FLUIDS and foam_case_ready(facts.has_foam_case),
    )
