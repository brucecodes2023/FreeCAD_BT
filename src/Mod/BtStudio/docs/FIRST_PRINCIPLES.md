# SPDX-License-Identifier: LGPL-2.1-or-later

# First-principles solver architecture

Every CAE module in this fork should start from the same template:

1. **Name the conserved quantities** (mass, momentum, energy, charge, …).
2. **Write the strong-form PDEs** on a domain \(\Omega(t)\).
3. **State constitutive closures** (material / fluid / contact / circuit).
4. **Choose a discretization** (FEM, FVM, MBD, circuit stamps).
5. **Expose a FreeCAD document object graph** that can emit a solver case
   without the Python layer knowing the solver’s internals.
6. **Bring results back** as document objects + a VTK/Coin view.

That is the “ANSYS Workbench pattern”: the CAD host owns geometry,
named selections, and the case tree; the solver is a backend.

This file is the architecture. Implementations land as separate Python
packages under `src/Mod/BtStudio/solvers/` so they never touch
`src/Mod/Fem/` or `src/Gui/`.

---

## Shared FreeCAD object graph

```
AnalysisContainer          # Fem::Analysis today; BtStudio::Study later
├── GeometryLink           # Part/PartDesign/Mesh
├── PhysicsModels[]        # elasticity, NS, Maxwell, heat, rigid-body, …
├── Materials[]            # cards with units
├── BoundaryConditions[]   # named selections + BC type
├── Numerics               # mesh / time / nonlinear controls
├── SolverBackend          # CalculiX | Elmer | OpenFOAM | future
└── Results[]              # fields, probes, reports
```

A **Study** may host several physics models that share a mesh or couple
through interface BCs (CHT, FSI, EM-thermal). Coupling is an explicit
object, never a hidden side effect.

Python registry (`solvers/registry.py`) maps a physics id to:

- governing-equation docstring (this file)
- required material properties
- allowed BC types
- backend id (`calculix`, `elmer`, `openfoam`, `mbd`, `circuit`)
- writer + reader callables (optional until implemented)

---

## Fluids (incompressible / compressible NS)

**First principles.** Continuity and momentum (Cauchy), plus energy if
the flow is compressible or heat-generating:

\[
\partial_t\rho + \nabla\cdot(\rho\mathbf{v}) = 0
\]
\[
\partial_t(\rho\mathbf{v}) + \nabla\cdot(\rho\mathbf{v}\otimes\mathbf{v})
= \nabla\cdot\boldsymbol{\sigma} + \rho\mathbf{g}
\]
\[
\boldsymbol{\sigma} = -p\mathbf{I} + \boldsymbol{\tau}(\mu,\mathbf{v}),
\quad
\boldsymbol{\tau} = \mu(\nabla\mathbf{v}+\nabla\mathbf{v}^T) - \tfrac{2}{3}\mu(\nabla\cdot\mathbf{v})\mathbf{I}
\]

**Discretization of choice: finite volume (FVM), collocated, conservative
fluxes.** That is OpenFOAM’s reason to exist, and why we will not force
CFD through CalculiX.

**FreeCAD mapping (future OpenFOAM workbench):**

| Principle | GUI object | OpenFOAM file |
|---|---|---|
| Domain | `Foam::Case` + mesh | `constant/polyMesh` |
| Fluid card | `Foam::Material` | `constant/transportProperties`, `thermophysicalProperties` |
| \(\mathbf{v}=\mathbf{v}_D\) | wall / inlet BC | `0/U` |
| \(p\) / total pressure | inlet/outlet BC | `0/p` |
| Turbulence closure | `Foam::Turbulence` | `constant/turbulenceProperties` |
| Time / SIMPLE / PIMPLE | `Foam::Numerics` | `system/fvSolution`, `controlDict` |
| Residual monitors | function objects | `system/controlDict` functions |

Elmer’s `FEM_EquationFlow` is a **FEM Stokes/NS** path useful for slow
internal flow and teaching. It is not the production CFD architecture.
See `OPENFOAM_ARCHITECTURE.md`.

**References.** Batchelor *An Introduction to Fluid Dynamics*;
Ferziger & Perić *Computational Methods for Fluid Dynamics*;
Weller et al., OpenFOAM architecture papers; OpenFOAM User Guide.

---

## Propulsion (thermo-fluids + structure)

A propulsion “solver” is not one PDE. It is a **coupled study**:

1. **Chamber / duct flow** — compressible NS + species + energy
   (OpenFOAM `rhoCentralFoam` / `reactingFoam` family, or a reduced
   1-D thermo network for early sizing).
2. **Heat soak** — FEM heat on the solid (already in Elmer/CalculiX).
3. **Thermoelastic stress** — elasticity with \(\boldsymbol{\varepsilon}_T=\alpha\Delta T\)
   (CalculiX `*EXPANSION`, Elmer elasticity + heat).
4. **Rotating machinery** — body force \(\rho\boldsymbol{\omega}\times(\boldsymbol{\omega}\times\mathbf{r})\)
   (`Fem::ConstraintCentrif`) plus optional cyclic symmetry.

**First-principles breakdown for a rocket chamber (example):**

- Mass: species continuity \( \partial_t(\rho Y_k)+\nabla\cdot(\rho Y_k\mathbf{v})= \dot{\omega}_k \)
- Momentum: NS with high Mach convective flux
- Energy: total energy with heat release \(\sum h_k\dot{\omega}_k\)
- State: \( p = \rho R T \sum Y_k/W_k \) (ideal gas; replace with real-gas EOS later)
- Solid: heat equation in the wall, interface \( q = h(T_g-T_w) \) or conjugate
- Structure: elasticity on the wall with temperature field from step 2

The FreeCAD document should show **four physics nodes** under one Study,
not a single “Propulsion” black box. Early versions can run them
sequentially (loose coupling) before attempting two-way FSI.

**References.** Sutton & Biblarz *Rocket Propulsion Elements*;
Cengel & Boles *Thermodynamics*; the FEM heat/elasticity sections of
this guide; OpenFOAM reacting tutorials.

---

## Robotics (multibody + actuation)

Robotics is **finite-dimensional mechanics**, not a continuum PDE:

- Generalized coordinates \(\mathbf{q}\)
- Holonomic constraints \(\mathbf{c}(\mathbf{q})=\mathbf{0}\) (joints)
- Lagrange / maximal-coordinate DAE:

\[
\mathbf{M}(\mathbf{q})\ddot{\mathbf{q}} + \mathbf{C}(\mathbf{q},\dot{\mathbf{q}})
+ \mathbf{G}(\mathbf{q}) + \mathbf{J}^T\boldsymbol{\lambda} = \boldsymbol{\tau}
\]
\[
\mathbf{c}(\mathbf{q})=\mathbf{0}
\]

**Backend today:** Assembly workbench already vendors **OndselSolver**
(`src/3rdParty/OndselSolver`) for kinematic/dynamic assembly constraints.
That is the MBD kernel we should wrap, not rewrite.

**FreeCAD mapping:**

| Principle | Object |
|---|---|
| Rigid body | Assembly / PartDesign Body with inertia |
| Joint (hinge, slider, …) | Assembly constraint / joint |
| Actuator torque/force | future `Robot::Actuator` on a joint |
| Contact | future unilateral constraint |
| Sensors / control | future time-stepping loop around OndselSolver |

Continuum FEM still matters for **flexible links**: run elasticity (or
modal reduction) and co-simulate with the MBD model. That coupling is a
Study link, same as FSI.

**References.** Featherstone *Rigid Body Dynamics Algorithms*;
Haug *Computer Aided Kinematics and Dynamics*; OndselSolver docs in-tree.

---

## Electronics (circuits + EM fields)

Two scales, two discretizations:

**Lumped circuits** (Kirchhoff):

\[
\mathbf{A}\,\mathbf{i} = \mathbf{0},\quad
\mathbf{v} = \mathbf{A}^T\boldsymbol{\phi},\quad
\mathbf{i} = f(\mathbf{v},\dot{\mathbf{v}},t)
\]

Modified nodal analysis stamps. This is SPICE, not FEM. A future
`Eda::Circuit` module should emit netlists, not meshes.

**Distributed EM** (Maxwell), already partially in Elmer:

\[
\nabla\times\mathbf{E} = -\partial_t\mathbf{B},\quad
\nabla\times\mathbf{H} = \mathbf{J}+\partial_t\mathbf{D},\quad
\nabla\cdot\mathbf{B}=0,\quad
\nabla\cdot\mathbf{D}=\rho_e
\]

with \(\mathbf{B}=\mu\mathbf{H}\), \(\mathbf{D}=\varepsilon\mathbf{E}\),
\(\mathbf{J}=\sigma\mathbf{E}+\mathbf{J}_s\).

FreeCAD today: `FEM_EquationElectrostatic`, `FEM_EquationMagnetodynamic`,
`FEM_EquationMagnetodynamic2D`, `FEM_ConstraintCurrentDensity`,
`FEM_ConstraintMagnetization`, `FEM_ConstraintElectricChargeDensity`.

**Thermal coupling:** Joule heat \( \mathbf{J}\cdot\mathbf{E} \) becomes \(Q\)
in the heat equation — Elmer can couple these equations in one `.sif`.

**References.** Jackson *Classical Electrodynamics* (fields);
Ho, Ruehli, Brennan (MNA); Elmer Models Manual (electrostatics,
magnetodynamics, heat).

---

## How to add a new first-principles domain

1. Write the balance laws in this file (or a sibling) with constitutive
   closures and references.
2. Register a physics id in `solvers/registry.py`.
3. List the minimum document objects (material, BCs, numerics).
4. Pick a backend that **already conserves the right quantities**
   (do not stretch CalculiX into CFD).
5. Add a writer that emits a case directory / input deck from the
   document, and a reader that creates result objects.
6. Put GUI commands in BtStudio (or a future dedicated Mod), never in
   `src/Gui`.

The OpenFOAM case tree in `OPENFOAM_ARCHITECTURE.md` is the first
full worked example of steps 3–6 for a domain FEM does not own.
