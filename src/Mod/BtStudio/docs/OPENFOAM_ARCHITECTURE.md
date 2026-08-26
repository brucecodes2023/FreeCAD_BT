# SPDX-License-Identifier: LGPL-2.1-or-later

# OpenFOAM GUI architecture

Goal: an ANSYS Fluent-like workbench that **owns an OpenFOAM case tree**,
not a pile of macros.

**This slice:** `solvers/foam_write.py` emits a valid incompressible case
(`simpleFoam` / `pimpleFoam` / `potentialFoam`) from a CAD bounding box.
`FoamCase` is a FeaturePython object; **BtStudio_FoamWriteCase** writes
`0/`, `constant/`, `system/` (including `blockMeshDict`). It still does
**not** spawn `blockMesh` or the solver — that is the next slice.

FEM/Elmer flow stays for slow internal FEM-NS. Production CFD goes here.

## Why a new module (Tier 4)

OpenFOAM cases are a **directory protocol** (`0/`, `constant/`, `system/`),
not an INP deck. Putting that writer into `src/Mod/Fem` would mix
preprocessors and fight upstream FEM churn. A Python-only
`src/Mod/BtStudio` (and later `src/Mod/Foam` if it grows) keeps the
merge surface at zero.

## Case object graph

```
FoamCase                     # App::DocumentObject group
├── Geometry                 # Part/Mesh → snappy or gmshToFoam
├── MeshSetup
│   ├── SurfaceRegions       # named patches from CAD faces
│   ├── RefinementRegions    # inside/outside/distance (snappy)
│   └── LayerControls        # addLayers
├── Physics
│   ├── SolverPicker         # simpleFoam, pimpleFoam, rhoPimpleFoam, …
│   ├── Transport            # Newtonian / non-Newtonian
│   ├── Thermophysical       # if compressible / heat
│   └── Turbulence           # laminar | kOmegaSST | kEpsilon | …
├── Fields / BCs             # one object per patch+field
├── Numerics
│   ├── TimeControl          # steady / transient, deltaT, writeInterval
│   ├── Schemes              # fvSchemes
│   └── LinearSolvers        # fvSolution (GAMG, PBiCGStab, …)
├── Monitors                 # residuals, probes, forces, y+
└── Run
    ├── decomposePar
    ├── solver
    └── reconstructPar / foamToVTK
```

Results re-enter FreeCAD through VTK (`vtkOpenFOAMReader` or `foamToVTK`)
and the existing FEM post pipeline (`FEM_PostPipelineFromResult` style),
or a Coin mesh with a scalar field. Do not invent a second post stack.

## Solver families we will expose first

| GUI name | Application | Equations |
|---|---|---|
| Steady incompressible | `simpleFoam` | NS, SIMPLE |
| Transient incompressible | `pimpleFoam` | NS, PIMPLE |
| Steady compressible | `rhoSimpleFoam` | NS + energy |
| Transient compressible | `rhoPimpleFoam` | NS + energy |
| Heat conjugate (later) | `chtMultiRegionFoam` | fluid + solid energy |
| Potential init | `potentialFoam` | \(\nabla^2\phi=0\) for \(\mathbf{v}\) seed |

Propulsion (reacting, high-Mach) is a second wave: `rhoCentralFoam`,
`reactingFoam`. Register them in `solvers/registry.py` with
`status="planned"` so the GUI can show “coming” rather than a dead button.

## Mesh path

1. CAD named faces → patch names (no fluent “zone” rename late).
2. Prefer **snappyHexMesh** for industrial CAD (ANSYS Fluent default feel).
3. Allow **gmshToFoam** for people already meshing in FEM Gmsh.
4. `checkMesh` must be a first-class “Run” step; fail the case if
   non-orthogonality / holes exceed a preference.

## GUI layout (Fluent-like, but FreeCAD)

- Left: case tree (the object graph above).
- Right: task sidebar tabs (same BtStudio Tasks-on-the-right rule):
  General, Models, Materials, Boundary Conditions, Mesh, Solution, Results.
- Ribbon (workbench toolbars): Mesh | Physics | BCs | Run | Post.
- A walkthrough wizard parallel to the FEM wizard (checklist in the
  right sidebar).

## Execution

Never shell out blindly from the GUI thread.

1. Write the case to a working directory under the document’s folder.
2. Run `blockMesh` / `snappyHexMesh` / solver via `QProcess` with logs
   in the Report view.
3. MPI: `decomposePar` + `mpirun -np N` gated by a preference.

OpenFOAM itself stays an **external dependency** (system install or
pref path). We do not vendor the OpenFOAM C++ tree in this repo.

## MCP / AI

FcBridge already executes Python in a running GUI. Future tools:

- `foam.write_case`
- `foam.run_solver`
- `foam.residual_summary`

Those tools should call the same Python API the wizard uses, so AI and
humans cannot diverge.

## Out of scope until the case graph exists

- Custom turbulence models
- Overset / AMI GUI
- Full chemically reacting GUI
- In-tree compilation of OpenFOAM
