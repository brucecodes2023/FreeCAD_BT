# SPDX-License-Identifier: LGPL-2.1-or-later

"""OpenFOAM case layout — no subprocess calls yet."""

from __future__ import annotations

CASE_DIRS = ("0", "constant", "system")

STANDARD_FILES = {
    "system/controlDict": "time control, application, writeInterval, functions",
    "system/fvSchemes": "div/grad/laplacian schemes",
    "system/fvSolution": "linear solvers, SIMPLE/PIMPLE",
    "system/snappyHexMeshDict": "CAD → hex mesh",
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


def case_tree() -> dict:
    """Directory protocol a future FoamCase object must write."""
    return {
        "dirs": list(CASE_DIRS),
        "files": dict(STANDARD_FILES),
        "solvers": list(FIRST_SOLVERS),
    }
