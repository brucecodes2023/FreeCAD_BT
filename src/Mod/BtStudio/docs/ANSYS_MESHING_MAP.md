# SPDX-License-Identifier: LGPL-2.1-or-later

# ANSYS meshing → FreeCAD FEM

ANSYS Mechanical/Workbench meshing is a **sizing + method + inflation +
refinement** stack. FreeCAD FEM already has the same stack, implemented
as Gmsh/Netgen document objects rather than a single “Mesh” ribbon.

BtStudio does **not** reimplement a mesher. It documents this map and
adds a one-click Auto Mesh that creates the global-size object ANSYS
would call “Body sizing.”

| ANSYS idea | FreeCAD object / command | Notes |
|---|---|---|
| Mesh on geometry | `FEM_MeshGmshFromShape`, `FEM_MeshNetgenFromShape` | Auto Mesh wraps Gmsh |
| Body sizing | `Fem::MeshGmsh.CharacteristicLengthMax/Min` | Auto Mesh: \(h = D/20\) |
| Face / edge / vertex sizing | `Fem::MeshRegion` (`FEM_MeshRegion`) | **This is concentration** |
| Sphere / box of influence | `Fem::MeshDistance` + region refs | Distance-based \(h\) |
| Body of influence / attractor | `Fem::MeshAdvanced` `AttractorAnisoCurve`, `Distance` | Anisotropic near curves |
| Sizing function | `Fem::MeshAdvanced` `MathEval` / `MathEvalAniso` | Gmsh math size field |
| Solution-adaptive | `Fem::MeshAdvanced` `Type=Result` + `adaptivetools.py` | See `gmsh_adaptive` example |
| Inflation / boundary layer | `Fem::MeshBoundaryLayer` | CFD / thermal skins |
| Multizone / hex mapped | `Fem::MeshTransfiniteCurve/Surface/Volume` | Structured Gmsh |
| Named selections | `Fem::MeshGroup` | Writer uses these as ELSET |
| Repair / remesh locally | `Fem::MeshManipulate` | |
| Extra Gmsh knobs | `Fem::MeshAdvanced` | |

## Recommended first-pass workflow (matches ANSYS Mechanical habits)

1. Auto Mesh (global \(h\)).
2. MeshRegion on fillets, holes, contact faces (\(h/3\) to \(h/8\)).
3. Boundary layer only if you are doing heat film or flow.
4. Generate. Look at tet quality and whether 2+ quadratic elements sit
   through thin walls.
5. Solve a coarse run. If a gradient is unresolved, add a MeshRegion or
   switch MeshAdvanced to `Result` and run the adaptive example path.

## Commands on the stock FEM Mesh toolbar (upstream)

`FEM_MeshNetgenFromShape`, `FEM_MeshGmshFromShape`, `FEM_MeshRegion`,
`FEM_MeshGroup`, `FEM_MeshGMSHRefinement` (group: distance, boundary
layer, shape, manipulate, advanced, transfinite), `FEM_FEMMesh2Mesh`.

BtStudio prepends **Auto Mesh** and the **FEM wizard**; it does not delete
these commands. Specialist groups stay on the toolbar but the wizard is
the default path.
