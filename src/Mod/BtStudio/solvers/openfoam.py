# SPDX-License-Identifier: LGPL-2.1-or-later

"""OpenFOAM case layout — writer exists; no solver subprocess yet."""

from __future__ import annotations

CASE_DIRS = ("0", "constant", "system")

STANDARD_FILES = {
    "system/controlDict": "time control, application, writeInterval, functions",
    "system/fvSchemes": "div/grad/laplacian schemes",
    "system/fvSolution": "linear solvers, SIMPLE/PIMPLE",
    "system/blockMeshDict": "hex mesh from CAD bounding box (metres)",
    "system/snappyHexMeshDict": "CAD → hex mesh (not written in this slice)",
    "constant/transportProperties": "nu / Newtonian",
    "constant/turbulenceProperties": "laminar | RAS | LES",
    "0/U": "velocity BCs",
    "0/p": "pressure BCs",
}

FIRST_SOLVERS = (
    "simpleFoam",
    "pimpleFoam",
    "rhoSimpleFoam",
    "rhoPimpleFoam",
    "potentialFoam",
)

# First writer slice: incompressible only (no thermophysical / 0/T yet).
INCOMPRESSIBLE_SOLVERS = ("simpleFoam", "pimpleFoam", "potentialFoam")


def case_tree() -> dict:
    """Directory protocol the FoamCase writer emits."""
    return {
        "dirs": list(CASE_DIRS),
        "files": dict(STANDARD_FILES),
        "solvers": list(FIRST_SOLVERS),
        "incompressible": list(INCOMPRESSIBLE_SOLVERS),
    }
