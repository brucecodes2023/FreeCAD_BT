# SPDX-License-Identifier: LGPL-2.1-or-later

"""First-principles physics registry (data only)."""

from __future__ import annotations

PHYSICS = [
    {
        "id": "elasticity",
        "domain": "structures",
        "title": "Linear / nonlinear elasticity",
        "backend": "calculix",
        "status": "available",
        "balance_laws": "linear momentum (Cauchy)",
        "discretization": "FEM (Galerkin)",
    },
    {
        "id": "heat",
        "domain": "structures",
        "title": "Heat conduction",
        "backend": "calculix",
        "status": "available",
        "balance_laws": "energy",
        "discretization": "FEM",
    },
    {
        "id": "electrostatics",
        "domain": "electronics",
        "title": "Electrostatics / magnetodynamics",
        "backend": "elmer",
        "status": "available",
        "balance_laws": "Maxwell (quasi-static)",
        "discretization": "FEM",
    },
    {
        "id": "elmer_flow",
        "domain": "fluids",
        "title": "FEM Navier–Stokes (slow internals)",
        "backend": "elmer",
        "status": "available",
        "balance_laws": "mass + momentum",
        "discretization": "FEM",
    },
    {
        "id": "openfoam_incompressible",
        "domain": "fluids",
        "title": "Incompressible CFD",
        "backend": "openfoam",
        "status": "planned",
        "balance_laws": "mass + momentum (FVM)",
        "discretization": "FVM / OpenFOAM",
    },
    {
        "id": "propulsion_cht",
        "domain": "propulsion",
        "title": "Conjugate heat + thermoelastic wall",
        "backend": "openfoam+calculix",
        "status": "planned",
        "balance_laws": "NS + energy + elasticity",
        "discretization": "FVM + FEM, sequential couple",
    },
    {
        "id": "mbd",
        "domain": "robotics",
        "title": "Multibody dynamics",
        "backend": "ondsel",
        "status": "available",
        "balance_laws": "Lagrange DAE / maximal coordinates",
        "discretization": "finite-dimensional MBD",
    },
]


def by_domain(domain: str) -> list[dict]:
    return [p for p in PHYSICS if p["domain"] == domain]


def planned_backends() -> list[str]:
    return sorted({p["backend"] for p in PHYSICS if p["status"] == "planned"})
