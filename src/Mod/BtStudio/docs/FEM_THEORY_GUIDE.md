# SPDX-License-Identifier: LGPL-2.1-or-later
# FreeCAD_BT — FEM Theory Guide (fork-only)

# FEM Theory Guide

This is the first-principles map for the FEM workbench in this fork. It is
written so a designer can go from “I have a solid” to “I trust this stress
number,” and so later solver work (fluids, propulsion, electronics) can reuse
the same discretization story.

FreeCAD’s FEM workbench is already a **pre/post processor**: geometry and
mesh live in the FreeCAD document; the actual PDE solve is delegated to
CalculiX, Elmer, Mystran, or Z88. That split is intentional and is the same
architecture ANSYS Workbench uses (model in the CAD/CAE host, physics in a
solver backend).

---

## 1. What we are actually solving

A continuum body occupies a region \(\Omega\) with boundary \(\partial\Omega\).
At every point we want fields such as displacement \(\mathbf{u}\), temperature
\(T\), or electric potential \(\phi\).

Those fields obey **balance laws** (first principles) plus **constitutive
laws** (material models):

| Physics | Balance law | Unknown | Typical FreeCAD solver |
|---|---|---|---|
| Linear elasticity | \(\nabla\cdot\boldsymbol{\sigma} + \mathbf{b} = \rho\ddot{\mathbf{u}}\) | \(\mathbf{u}\) | CalculiX, Elmer elasticity |
| Heat conduction | \(\rho c \dot{T} = \nabla\cdot(k\nabla T) + Q\) | \(T\) | CalculiX, Elmer heat |
| Electrostatics | \(\nabla\cdot(\varepsilon\nabla\phi) = -\rho_e\) | \(\phi\) | Elmer electrostatic, CalculiX |
| Incompressible flow | \(\nabla\cdot\mathbf{v}=0\), NS momentum | \(\mathbf{v},p\) | Elmer flow *(OpenFOAM later)* |
| Magnetodynamics | Maxwell + constitutive \(\mathbf{B}=\mu\mathbf{H}\) | \(\mathbf{A},\phi\) | Elmer magnetodynamic |

The **strong form** is the PDE + boundary conditions written at every point.
FEM never solves that form directly.

---

## 2. Strong form → weak form → discrete system

Take linear static elasticity as the prototype.

**Strong form** (inside \(\Omega\)):

\[
\nabla\cdot\boldsymbol{\sigma}(\mathbf{u}) + \mathbf{b} = \mathbf{0},
\quad
\boldsymbol{\sigma} = \mathbb{C}:\boldsymbol{\varepsilon},
\quad
\boldsymbol{\varepsilon} = \tfrac{1}{2}(\nabla\mathbf{u}+\nabla\mathbf{u}^T)
\]

with Dirichlet data \(\mathbf{u}=\mathbf{u}_D\) on \(\Gamma_D\) and traction
\(\boldsymbol{\sigma}\cdot\mathbf{n}=\mathbf{t}\) on \(\Gamma_t\).

Multiply by a test function \(\mathbf{v}\) that vanishes on \(\Gamma_D\),
integrate, and integrate by parts. The **weak form** is: find \(\mathbf{u}\)
such that for all admissible \(\mathbf{v}\)

\[
\int_\Omega \boldsymbol{\varepsilon}(\mathbf{v}):\mathbb{C}:\boldsymbol{\varepsilon}(\mathbf{u})\,d\Omega
=
\int_\Omega \mathbf{v}\cdot\mathbf{b}\,d\Omega
+
\int_{\Gamma_t} \mathbf{v}\cdot\mathbf{t}\,d\Gamma.
\]

That is the **principle of virtual work**. Every mechanical constraint in
the FEM workbench is a term on the right-hand side or a restriction on the
trial space:

| FreeCAD object | Weak-form role |
|---|---|
| `Fem::ConstraintFixed` | \(\mathbf{u}=\mathbf{0}\) on \(\Gamma_D\) (essential BC) |
| `Fem::ConstraintDisplacement` | prescribed essential BC |
| `Fem::ConstraintForce` | traction integral on \(\Gamma_t\) |
| `Fem::ConstraintPressure` | \(\mathbf{t} = -p\mathbf{n}\) |
| `Fem::ConstraintSelfWeight` | body force \(\mathbf{b}=\rho\mathbf{g}\) |
| `Fem::ConstraintCentrif` | body force \(\mathbf{b}=\rho\boldsymbol{\omega}\times(\boldsymbol{\omega}\times\mathbf{r})\) |
| `Fem::ConstraintHeatflux` | Neumann term in the heat weak form |
| `Fem::ConstraintTemperature` | essential BC on \(T\) |
| `Fem::ConstraintSpring` | extra stiffness on the boundary |

**Galerkin discretization.** Mesh \(\Omega\) into elements. On each element
approximate \(\mathbf{u}^h = \mathbf{N}\,\mathbf{d}\) with shape functions
\(\mathbf{N}\) and nodal degrees of freedom \(\mathbf{d}\). Substituting
produces the linear system

\[
\mathbf{K}\,\mathbf{d} = \mathbf{f}.
\]

\(\mathbf{K}\) is assembled from element stiffness matrices
\(\mathbf{k}^e = \int_{\Omega^e} \mathbf{B}^T\mathbb{C}\mathbf{B}\,d\Omega\).
That assembly is what CalculiX / Elmer do. FreeCAD’s job is to **build a
mesh, tag sets, write the solver input, and read the results back**.

---

## 3. Element types (why the mesh object matters)

| Element | Shape functions | Use |
|---|---|---|
| Tet4 / Tria3 | linear | fast, stiff (constant strain) |
| Tet10 / Tria6 | quadratic | default structural quality |
| Hex20 / Quad8 | quadratic | structured regions, thinner walls |
| Beam / shell sections | reduced 3D | `Fem::ElementGeometry1D/2D` |

Rule of thumb: **quadratic tets (Tet10)** are the FreeCAD default for a
reason. Linear tets under-predict bending. If a result looks “too stiff,”
check element order before changing the material.

Gmsh and Netgen both emit Tet4 or Tet10 from a solid. `Fem::MeshGmsh`
exposes second-order via `SecondOrderLinear` / element dimension settings.
`Fem::MeshNetgen` does the same through Netgen parameters.

---

## 4. Meshing — auto, concentrations, and the ANSYS map

**Yes: FreeCAD already has auto mesh, local refinement, and attractors.**
They are just named after Gmsh/Netgen objects rather than ANSYS “sizing”
and “sphere of influence.” See `ANSYS_MESHING_MAP.md` for the object-by-object
table. The BtStudio **Auto Mesh** command is a one-click wrapper around
those objects, not a new mesher.

### 4.1 Global size (ANSYS: Body sizing)

From the shape bounding-box diagonal \(D\):

\[
h_{\max} \approx D / 20
\]

is a sane first pass (the Auto Mesh command uses this). Drop to \(D/40\) if
the first stress plot is noisy at fillets.

FreeCAD: `Fem::MeshGmsh.CharacteristicLengthMax` and
`CharacteristicLengthMin`.

### 4.2 Local concentration (ANSYS: Face/Edge sizing, sphere of influence)

FreeCAD: **`Fem::MeshRegion`** — a characteristic length on referenced
faces, edges, or vertices. This **is** the concentration tool. Put a
MeshRegion on a fillet, bolt hole, or crack-like notch.

Gmsh also has:

- `Fem::MeshDistance` — size as a function of distance to a shape
- `Fem::MeshAdvanced` with `Type = AttractorAnisoCurve | Distance | MathEval | Result`
- `Fem::MeshBoundaryLayer` — inflation layers (CFD / thermal skins)
- Transfinite curve/surface/volume — mapped hex/quad meshes

`MeshAdvanced.Type = Result` plus `femmesh/adaptivetools.py` is **solution-based
adaptive remeshing** (ANSYS: refinement loops on equivalent stress). The
example `femexamples/gmsh_adaptive.py` exercises it.

### 4.3 Why concentrations exist (theory)

FEM error on a linear element scales as \(O(h)\) in \(H^1\) (energy) and
worse near singularities (reentrant corners, point loads, cracks). Locally
reducing \(h\) is how you spend DOFs where the residual is large. That is
exactly what MeshRegion / attractors do.

A point load or a sharp reentrant corner has a **singular** stress in the
continuum solution. Refining forever will grow \(\sigma_\max\). For those
features, report a **converged energy quantity** (reaction, J-integral,
average stress over a small volume) rather than a single nodal peak.

### 4.4 Quality checks

Before trusting \(\mathbf{K}\mathbf{d}=\mathbf{f}\):

1. Jacobian / tet quality (Gmsh `Mesh.Optimize` is on by default).
2. Second-order elements on solids.
3. At least 2 quadratic elements through a thickness you care about.
4. Mesh convergence: rerun at \(h\) and \(h/2\); the quantity of interest
   should change less than your tolerance (5–10 % for a first design pass).

---

## 5. Materials and constitutive models

Linear isotropic elasticity needs only \(E\) and \(\nu\) (and \(\rho\) if
you have gravity, centrif, or dynamics):

\[
\mathbb{C} = \lambda\mathbf{I}\otimes\mathbf{I} + 2\mu\,\mathbb{I},
\quad
\mu = \frac{E}{2(1+\nu)},
\quad
\lambda = \frac{E\nu}{(1+\nu)(1-2\nu)}.
\]

FreeCAD objects:

- `Fem::MaterialSolid` / `Fem::MaterialFluid` — cards from the material
  framework
- `Fem::MaterialMechanicalNonlinear` — plasticity / hyperelastic cards for
  CalculiX
- `Fem::MaterialReinforced` — rebar-smeared concrete

Units: FreeCAD is unit-aware. CalculiX is not. The writer converts to a
consistent set (usually mm/N/s or SI). If a stress is off by \(10^3\) or
\(10^9\), check the unit system in the solver object first.

---

## 6. Analysis containers and the solver hand-off

A valid model is an `Fem::Analysis` group containing:

1. A mesh (`Fem::MeshGmsh` or `Fem::MeshNetgen`, or an imported INP mesh)
2. One or more materials, referenced to solids
3. Constraints (BCs and loads)
4. A solver object (`Fem::SolverCalculix`, `Fem::SolverElmer`, …)
5. After a run: a results object + optional VTK pipeline

The writer (`femsolver/calculix/writer.py`, Elmer equation writers) walks
that group, maps faces to element sets, and emits `*.inp` / Elmer `.sif`.

**CalculiX** is the default structural solver (Abaqus-like INP). **Elmer**
is the multiphysics solver (heat, flow, EM, elasticity as coupled
equations). Use CalculiX for mechanical design work; use Elmer when you
need coupled physics FreeCAD already exposes as equation objects.

---

## 7. Verification (when a pretty plot is a lie)

Before changing design on a FEM number:

1. **Rigid modes.** A static model with no constraints is singular. CalculiX
   will fail or emit huge rigid motion. Check that every body has enough
   `ConstraintFixed` / `ConstraintDisplacement` to kill 6 rigid modes.
2. **Reaction balance.** Sum of reactions should equal sum of applied loads
   (within mesh error).
3. **Patch test / known solution.** A tensile bar \(\sigma = F/A\) should
   recover \(\sigma\) to a few percent on a coarse Tet10 mesh.
4. **Mesh convergence** on the *quantity you will use* (max principal at a
   fillet, not a point-load node).
5. **Element order.** Linear tets in bending are the most common false-stiff
   result in this workbench.

The BtStudio FEM wizard encodes this as a checklist so the model cannot be
“solved” until mesh + material + at least one BC exist.

---

## 8. Walkthrough that matches the wizard

1. Solid geometry in Part / Part Design (one body per part you will mesh).
2. FEM workbench → **New Analysis** (creates solver by preference).
3. Material on the solid.
4. Constraints on faces (fixed, force, pressure, …).
5. Mesh: Auto Mesh, then MeshRegion on fillets / holes.
6. Run solver.
7. Results: `FEM_ResultShow` or the VTK pipeline (`FEM_PostPipelineFromResult`).
8. If peaks sit on a singularity, average or refine a region — do not chase
   the single hottest node.

---

## 9. What this fork adds vs what upstream already had

| Need | Upstream | BtStudio |
|---|---|---|
| Auto mesh from bbox | manual Gmsh/Netgen parameters | `BtStudio_FemAutoMesh` |
| Concentrations | `MeshRegion`, `MeshAdvanced`, `MeshDistance` | documented + wizard step |
| Adaptive remesh | `gmsh_adaptive` example + `adaptivetools.py` | pointed from this guide |
| Step-by-step UI | scattered toolbars | right-sidebar wizard |
| Theory write-up | wiki fragments | this file |

OpenFOAM CFD is **not** in the FEM workbench. That is a separate first-principles
backend (`OPENFOAM_ARCHITECTURE.md`) so we do not pretend Elmer flow is a
Fluent replacement.
