# SPDX-License-Identifier: LGPL-2.1-or-later

"""Pure helpers for BtStudio — no FreeCAD import, so tests can run with python3."""

from __future__ import annotations

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

FEM_WIZARD_STEPS = [
    {
        "id": "geometry",
        "title": "Select solid geometry",
        "hint": "Pick the Part or PartDesign body that will be meshed.",
        "command": None,
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
        "command": None,
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
