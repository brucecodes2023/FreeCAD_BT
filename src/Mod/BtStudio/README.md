# BtStudio — fork-only overlay (Tier 4)

Python module loaded with `FreeCAD -M src/Mod/BtStudio`. It does **not**
edit `src/Gui` or `src/Mod/Fem`. See `OVERVIEW.md` conflict tiers.

## What it does on launch

- Reorders the workbench selector once: Sketch → Part → Part Design → Assembly → FEM
- Enables Sketcher snaps / auto-constraints and PartDesign transparent preview
- Splits Combo View so Tasks sit as a **right tabbed sidebar** (Model tree stays on the left)
- New sketches: origin planes show a **grid in the 3D view**; click a plane in the view or Origin in the Model tree (no Choose Orientation dialog)
- Closed sketches switch to **Flat Lines** (filled face) when you leave the editor or click Extrude/Pad
- macOS: native red/yellow/green traffic lights in the **top-left** (Ribbon's right-side min/max/close stripped)
- Trackpad overlay: two-finger pan, Shift+scroll zoom, Cmd/Ctrl+scroll rotate, pinch zoom
- Commands (also inserted next to stock New Sketch / FEM Analysis):
  - **New Sketch** — isometric origin planes; click in the 3D view or Model tree
  - **Insert DXF / DWG** — into the open sketch, or a new sketch on the selected plane. Simple ASCII DXF (LINE/CIRCLE/ARC) is written into the sketch so inner slots are kept; DWG and complex DXF still use Draft.
  - **FEM analysis wizard** — right-sidebar, ANSYS Mechanical-style:
    pick **Static Structural**, **Modal**, **Steady-State Thermal**,
    **Thermal-Stress**, or **Linear Buckling**. Pipeline is geometry →
    analysis (CalculiX `AnalysisType` set) → material → BCs → mesh →
    solve → results. Only the next step’s Run is enabled.
    **Transient** / **Harmonic** are listed as coming.
  - **Auto mesh** — Gmsh `h = bbox_diagonal / 20`, MeshRegion on selected faces
  - **Feature history** — PartDesign Tip slider (Fusion-style rollback); large button on Helpers
  - **Zoom all / Zoom to…** — fit everything, the selection, the active Body, or a picked part/body
  - **Construction plane** — PartDesign datum plane on the active Body. Large button on Sketcher (Sketch panel) and Part Design Helpers.
  - **Component data table** — selected-object properties
  - **FEM theory guide** — opens `docs/FEM_THEORY_GUIDE.md`
  - **Fluid Flow (later)** — OpenFOAM will get its own tab; the Fluids
    placeholder still writes a simpleFoam tree (mesh/solve Coming)

## Docs

| File | Notes item |
|---|---|
| `docs/FEM_THEORY_GUIDE.md` | Full FEM theory |
| `docs/FIRST_PRINCIPLES.md` | Fluids / propulsion / robotics / electronics |
| `docs/ANSYS_MESHING_MAP.md` | Concentrations already in Gmsh objects |
| `docs/ANSYS_ANALYSIS_MAP.md` | Mechanical analysis systems → CalculiX |
| `docs/studio-design.html` | Product spec + staged roadmap (Sketch, Part Design, Simulation; not implemented) |
| `docs/simulation-schematic.html` | Redirect stub → `studio-design.html#simulation` |
| `docs/OPENFOAM_ARCHITECTURE.md` | Future Fluids tab; case writer |

## Tests

Headless (OVERVIEW.md §9 path 1) — wizard step gating is pure Python in
`btstudio/core.py` (`geometry_ready`, `evaluate_wizard`, `fem_wizard_steps`);
no FreeCAD import:

```
cd src/Mod/BtStudio && python3 -m btstudio.tests
```

## Human GUI check (OVERVIEW.md §9 path 3)

1. `./run-freecad.sh` from the repo root.
2. Workbench tabs should start Start / Sketcher / Part / PartDesign / …
3. Part Design → **New Sketch** → iso view with a grid on the origin planes; click XY in the 3D view or Origin in the tree; no Choose Orientation dialog.
4. Close a loop, leave the sketch, Extrude/Pad: the profile should show as a shaded face, pad preview shaded.
4b. **Insert DXF / DWG** (Sketch or Part Design toolbar, next to Validate Sketch): open a sketch → insert a DXF → pad still works. Inner slots (header pin rails, hole rectangles) should appear, not just the outer outline. Idle: select XY → Insert DXF → a new sketch appears.
4c. Part Design tab: large **Feature history** on the Helpers panel (next to Create sketch). Click it → right dock Tip slider. Also under Part Design menu, next to Clone. New Sketch / Pad / Fillet still run.
4d. **Zoom all** and **Zoom to…** on the ribbon top (quick access icons) and a Zoom panel on Part Design (after Helpers). Zoom all fits everything. Zoom to… lists Selection, Active body, and each Body/Part in the file.
4e. **Construction plane** on the Sketcher Sketch panel and Part Design Helpers. Select a face or XY/XZ/YZ, click it, set offset in Tasks. Then New Sketch on that plane.
5. **Analysis** menu or **BtStudio** toolbar → **FEM analysis wizard**.
   Default system = Static Structural. Click **Create sample cube**, then
   **Create analysis** — FEM workbench opens with CalculiX `static`.
   Switch the combo to **Modal** / **Thermal** / **Buckling** and the
   BC step text changes. Transient and Harmonic stay Coming.
6. **Fluids (later)** tab still writes a simpleFoam tree; mesh/solve Coming.
7. Select a feature → **Component data table** shows properties.
8. Model tree stays on the **left**; Tasks pops out on the **right** wide enough for the Attachment box.
9. On a Mac, red/yellow/green lights are top-left; there should be no min/max/close on the top-right.
