# SPDX-License-Identifier: LGPL-2.1-or-later

"""Write a simpleFoam-family OpenFOAM case tree. Does not run solvers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .foam_dict import dump_dictionary, foam_file_header
from .openfoam import INCOMPRESSIBLE_SOLVERS

# FreeCAD lengths are millimetres by default; OpenFOAM is SI metres.
MM_TO_M = 0.001

HEX_FACES = {
    "xmin": (0, 4, 7, 3),
    "xmax": (1, 2, 6, 5),
    "ymin": (0, 1, 5, 4),
    "ymax": (3, 7, 6, 2),
    "zmin": (0, 3, 2, 1),
    "zmax": (4, 5, 6, 7),
}

DEFAULT_PATCHES = (
    ("inlet", "patch", ("xmin",)),
    ("outlet", "patch", ("xmax",)),
    ("walls", "wall", ("ymin", "ymax", "zmin", "zmax")),
)


@dataclass
class FoamCaseSpec:
    """Incompressible case graph that can emit a directory protocol."""

    application: str = "simpleFoam"
    start_time: float = 0.0
    end_time: float = 100.0
    delta_t: float = 1.0
    write_interval: int = 20
    nu: float = 1.0e-5
    turbulence: str = "laminar"
    # Bounding box in FreeCAD millimetres: xmin, xmax, ymin, ymax, zmin, zmax
    bbox_mm: tuple[float, float, float, float, float, float] = (0.0, 100.0, 0.0, 100.0, 0.0, 10.0)
    cells: tuple[int, int, int] = (20, 20, 1)
    inlet_velocity: tuple[float, float, float] = (1.0, 0.0, 0.0)
    unit_scale: float = MM_TO_M
    patches: tuple[tuple[str, str, tuple[str, ...]], ...] = DEFAULT_PATCHES

    def __post_init__(self) -> None:
        if self.application not in INCOMPRESSIBLE_SOLVERS:
            raise ValueError(f"unsupported solver {self.application!r}")
        if self.turbulence not in {"laminar", "kOmegaSST", "kEpsilon"}:
            raise ValueError(f"unsupported turbulence {self.turbulence!r}")
        xmin, xmax, ymin, ymax, zmin, zmax = self.bbox_mm
        if not (xmax > xmin and ymax > ymin and zmax > zmin):
            raise ValueError("bbox_mm must have positive volume")
        if any(n < 1 for n in self.cells):
            raise ValueError("cells must be positive")
        if self.nu <= 0:
            raise ValueError("nu must be positive")
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        names = [p[0] for p in self.patches]
        if len(names) != len(set(names)):
            raise ValueError("patch names must be unique")
        used: set[str] = set()
        for _name, _kind, faces in self.patches:
            for face in faces:
                if face not in HEX_FACES:
                    raise ValueError(f"unknown hex face {face!r}")
                if face in used:
                    raise ValueError(f"hex face {face!r} assigned twice")
                used.add(face)
        missing = set(HEX_FACES) - used
        if missing:
            raise ValueError(f"unassigned hex faces: {sorted(missing)}")


def bbox_mm_from_boundbox(boundbox: object, pad: float = 0.0) -> tuple[float, float, float, float, float, float]:
    """Pack a FreeCAD BoundBox (mm) into the spec tuple."""
    xmin = float(boundbox.XMin) - pad
    xmax = float(boundbox.XMax) + pad
    ymin = float(boundbox.YMin) - pad
    ymax = float(boundbox.YMax) + pad
    zmin = float(boundbox.ZMin) - pad
    zmax = float(boundbox.ZMax) + pad
    return (xmin, xmax, ymin, ymax, zmin, zmax)


def write_case(root: str | Path, spec: FoamCaseSpec) -> list[str]:
    """Write the case tree. Returns relative paths written."""
    dest = Path(root)
    files = case_files(spec)
    written: list[str] = []
    for rel, text in files.items():
        path = dest / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        written.append(rel)
    return written


def case_files(spec: FoamCaseSpec) -> dict[str, str]:
    files = {
        "system/controlDict": _control_dict(spec),
        "system/fvSchemes": _fv_schemes(spec),
        "system/fvSolution": _fv_solution(spec),
        "system/blockMeshDict": _block_mesh(spec),
        "constant/transportProperties": _transport(spec),
        "constant/turbulenceProperties": _turbulence(spec),
        "0/U": _field_u(spec),
        "0/p": _field_p(spec),
    }
    if spec.turbulence != "laminar":
        files["0/k"] = _field_k(spec)
        if spec.turbulence == "kOmegaSST":
            files["0/omega"] = _field_omega(spec)
        else:
            files["0/epsilon"] = _field_epsilon(spec)
    return files


def _control_dict(spec: FoamCaseSpec) -> str:
    header = foam_file_header(cls="dictionary", obj="controlDict", location="system")
    return dump_dictionary(
        header,
        {
            "application": spec.application,
            "startFrom": "startTime",
            "startTime": spec.start_time,
            "stopAt": "endTime",
            "endTime": spec.end_time,
            "deltaT": spec.delta_t,
            "writeControl": "timeStep",
            "writeInterval": spec.write_interval,
            "purgeWrite": 0,
            "writeFormat": "ascii",
            "writePrecision": 8,
            "writeCompression": "off",
            "timeFormat": "general",
            "timePrecision": 6,
            "runTimeModifiable": True,
        },
    )


def _fv_schemes(spec: FoamCaseSpec) -> str:
    header = foam_file_header(cls="dictionary", obj="fvSchemes", location="system")
    ddt = "Euler" if spec.application.startswith("pimple") else "steadyState"
    return dump_dictionary(
        header,
        {
            "ddtSchemes": {"default": ddt},
            "gradSchemes": {"default": "Gauss linear"},
            "divSchemes": {
                "default": "none",
                "div(phi,U)": "bounded Gauss linearUpwind grad(U)",
                "div((nuEff*dev2(T(grad(U)))))": "Gauss linear",
            },
            "laplacianSchemes": {"default": "Gauss linear corrected"},
            "interpolationSchemes": {"default": "linear"},
            "snGradSchemes": {"default": "corrected"},
        },
    )


def _fv_solution(spec: FoamCaseSpec) -> str:
    del spec
    header = foam_file_header(cls="dictionary", obj="fvSolution", location="system")
    solver = {
        "solver": "smoothSolver",
        "smoother": "symGaussSeidel",
        "tolerance": 1e-6,
        "relTol": 0.1,
    }
    return dump_dictionary(
        header,
        {
            "solvers": {
                "p": {
                    "solver": "GAMG",
                    "smoother": "GaussSeidel",
                    "tolerance": 1e-6,
                    "relTol": 0.1,
                },
                "U": dict(solver),
                "k": dict(solver),
                "omega": dict(solver),
                "epsilon": dict(solver),
            },
            "SIMPLE": {
                "nNonOrthogonalCorrectors": 0,
                "consistent": True,
                "residualControl": {"p": 1e-4, "U": 1e-4, "k": 1e-4, "omega": 1e-4, "epsilon": 1e-4},
            },
            "relaxationFactors": {
                "equations": {"U": 0.9, "k": 0.7, "omega": 0.7, "epsilon": 0.7},
            },
        },
    )


def _block_mesh(spec: FoamCaseSpec) -> str:
    xmin, xmax, ymin, ymax, zmin, zmax = (c * spec.unit_scale for c in spec.bbox_mm)
    vertices = [
        [xmin, ymin, zmin],
        [xmax, ymin, zmin],
        [xmax, ymax, zmin],
        [xmin, ymax, zmin],
        [xmin, ymin, zmax],
        [xmax, ymin, zmax],
        [xmax, ymax, zmax],
        [xmin, ymax, zmax],
    ]
    nx, ny, nz = spec.cells
    header = foam_file_header(cls="dictionary", obj="blockMeshDict", location="system")
    lines = [
        header.rstrip(),
        "",
        "convertToMeters    1;",
        "",
        "vertices",
        "(",
    ]
    for pt in vertices:
        lines.append(f"    ( {pt[0]:.8g} {pt[1]:.8g} {pt[2]:.8g} )")
    lines.extend(
        [
            ");",
            "",
            "blocks",
            "(",
            f"    hex (0 1 2 3 4 5 6 7) ({nx} {ny} {nz}) simpleGrading (1 1 1)",
            ");",
            "",
            "edges",
            "(",
            ");",
            "",
            "boundary",
            "(",
        ]
    )
    for name, kind, faces in spec.patches:
        lines.append(f"    {name}")
        lines.append("    {")
        lines.append(f"        type            {kind};")
        lines.append("        faces")
        lines.append("        (")
        for face in faces:
            idx = HEX_FACES[face]
            lines.append(f"            ( {idx[0]} {idx[1]} {idx[2]} {idx[3]} )")
        lines.append("        );")
        lines.append("    }")
    lines.extend([");", "", "mergePatchPairs", "(", ");", ""])
    return "\n".join(lines)


def _transport(spec: FoamCaseSpec) -> str:
    header = foam_file_header(cls="dictionary", obj="transportProperties", location="constant")
    return dump_dictionary(
        header,
        {
            "transportModel": "Newtonian",
            "nu": f"[0 2 -1 0 0 0 0] {spec.nu:.8g}",
        },
    )


def _turbulence(spec: FoamCaseSpec) -> str:
    header = foam_file_header(cls="dictionary", obj="turbulenceProperties", location="constant")
    if spec.turbulence == "laminar":
        entries = {"simulationType": "laminar"}
    else:
        entries = {
            "simulationType": "RAS",
            "RAS": {
                "RASModel": spec.turbulence,
                "turbulence": True,
                "printCoeffs": True,
            },
        }
    return dump_dictionary(header, entries)


def _boundary_field(patches: Iterable[tuple[str, str, tuple[str, ...]]], kinds: dict[str, dict]) -> dict:
    out: dict = {}
    for name, _kind, _faces in patches:
        if name not in kinds:
            raise ValueError(f"missing BC for patch {name!r}")
        out[name] = kinds[name]
    return out


def _field_u(spec: FoamCaseSpec) -> str:
    header = foam_file_header(cls="volVectorField", obj="U", location="0")
    ux, uy, uz = spec.inlet_velocity
    bcs = {
        "inlet": {"type": "fixedValue", "value": f"uniform ({ux:.8g} {uy:.8g} {uz:.8g})"},
        "outlet": {"type": "zeroGradient"},
        "walls": {"type": "noSlip"},
    }
    return dump_dictionary(
        header,
        {
            "dimensions": "[0 1 -1 0 0 0 0]",
            "internalField": "uniform (0 0 0)",
            "boundaryField": _boundary_field(spec.patches, bcs),
        },
    )


def _field_p(spec: FoamCaseSpec) -> str:
    header = foam_file_header(cls="volScalarField", obj="p", location="0")
    bcs = {
        "inlet": {"type": "zeroGradient"},
        "outlet": {"type": "fixedValue", "value": "uniform 0"},
        "walls": {"type": "zeroGradient"},
    }
    return dump_dictionary(
        header,
        {
            "dimensions": "[0 2 -2 0 0 0 0]",
            "internalField": "uniform 0",
            "boundaryField": _boundary_field(spec.patches, bcs),
        },
    )


def _field_k(spec: FoamCaseSpec) -> str:
    header = foam_file_header(cls="volScalarField", obj="k", location="0")
    bcs = {
        "inlet": {"type": "fixedValue", "value": "uniform 0.1"},
        "outlet": {"type": "zeroGradient"},
        "walls": {"type": "kqRWallFunction", "value": "uniform 0.1"},
    }
    return dump_dictionary(
        header,
        {
            "dimensions": "[0 2 -2 0 0 0 0]",
            "internalField": "uniform 0.1",
            "boundaryField": _boundary_field(spec.patches, bcs),
        },
    )


def _field_omega(spec: FoamCaseSpec) -> str:
    header = foam_file_header(cls="volScalarField", obj="omega", location="0")
    bcs = {
        "inlet": {"type": "fixedValue", "value": "uniform 10"},
        "outlet": {"type": "zeroGradient"},
        "walls": {"type": "omegaWallFunction", "value": "uniform 10"},
    }
    return dump_dictionary(
        header,
        {
            "dimensions": "[0 0 -1 0 0 0 0]",
            "internalField": "uniform 10",
            "boundaryField": _boundary_field(spec.patches, bcs),
        },
    )


def _field_epsilon(spec: FoamCaseSpec) -> str:
    header = foam_file_header(cls="volScalarField", obj="epsilon", location="0")
    bcs = {
        "inlet": {"type": "fixedValue", "value": "uniform 0.1"},
        "outlet": {"type": "zeroGradient"},
        "walls": {"type": "epsilonWallFunction", "value": "uniform 0.1"},
    }
    return dump_dictionary(
        header,
        {
            "dimensions": "[0 2 -3 0 0 0 0]",
            "internalField": "uniform 0.1",
            "boundaryField": _boundary_field(spec.patches, bcs),
        },
    )
