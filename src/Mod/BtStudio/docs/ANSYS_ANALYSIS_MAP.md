# SPDX-License-Identifier: LGPL-2.1-or-later

# ANSYS analysis systems → FreeCAD FEM (CalculiX)

ANSYS Workbench starts with an **analysis system** (Static Structural,
Modal, Steady-State Thermal, …). BtStudio’s FEM wizard does the same:
pick the system first, then a gated Mechanical-style pipeline
(geometry → engineering data → BCs → mesh → solve → results).

Fluids / OpenFOAM is a **later tab**, not a FEM analysis system. The
case writer stays; mesh and solve stay Coming until that tab exists.

| ANSYS system | Wizard choice | CalculiX `AnalysisType` | Status |
|---|---|---|---|
| Static Structural | Static Structural | `static` | available |
| Modal | Modal | `frequency` | available |
| Steady-State Thermal | Steady-State Thermal | `thermomech` | available |
| Static Structural + Thermal | Thermal-Stress | `thermomech` | available |
| Linear Buckling | Linear Buckling | `buckling` | available |
| Transient Structural | Transient Structural | — | coming |
| Harmonic Response | Harmonic Response | — | coming |
| Fluid Flow (Fluent) | Fluids tab | OpenFOAM | own tab later |

## Pipeline (matches Mechanical habits)

1. **Geometry** — Part / PartDesign solid (or Create sample cube).
2. **Create analysis** — `Fem::Analysis` + `SolverCcxTools` with the
   `AnalysisType` from the table. Switches to the FEM workbench.
3. **Engineering data** — `FEM_MaterialSolid` (thermal cards need k, α).
4. **Supports / loads / thermal BCs** — command and hint change with the
   system (Fixed + Force for static; Fixed only for modal; Initial
   temperature for thermal).
5. **Mesh** — Auto Mesh body sizing \(h = D/20\), then MeshRegion
   concentrations (see `ANSYS_MESHING_MAP.md`).
6. **Solve** — `FEM_SolverRun` (ccx).
7. **Results** — `FEM_ResultShow`. Check the quantity the system is for
   (displacement, eigenfrequency, temperature, buckling factor).

BtStudio does **not** replace the FEM workbench toolbars. Specialist
constraints stay there; the wizard is the default path.
