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
  - **Analysis walkthrough** — right-sidebar **guided** wizard (not a checkbox list):
    pick **Structures (FEM)** or **Fluids (simpleFoam)**; only the next required
    step’s Run is enabled; later steps stay locked until prerequisites pass.
    Geometry can **Create sample cube** (`Part::Box`). Fluids: FoamCase → write
    `0/` `constant/` `system/` and show the output path. Mesh/solve stay *Coming*
    (no `blockMesh` / `simpleFoam` spawn).
  - **Auto mesh** — Gmsh `h = bbox_diagonal / 20`, MeshRegion on selected faces
  - **Feature history** — PartDesign Tip slider (Fusion-style rollback)
  - **Component data table** — selected-object properties
  - **FEM theory guide** — opens `docs/FEM_THEORY_GUIDE.md`
  - **New FoamCase / Write OpenFOAM case** — still on the always-visible **BtStudio** toolbar

## Docs

| File | Notes item |
|---|---|
| `docs/FEM_THEORY_GUIDE.md` | Full FEM theory |
| `docs/FIRST_PRINCIPLES.md` | Fluids / propulsion / robotics / electronics |
| `docs/ANSYS_MESHING_MAP.md` | Concentrations already in Gmsh objects |
| `docs/OPENFOAM_ARCHITECTURE.md` | Fluent-like module; guided wizard + case writer |

## Tests

Headless (OVERVIEW.md §9 path 1) — wizard step gating is pure Python in
`btstudio/core.py` (`geometry_ready`, `evaluate_wizard`); no FreeCAD import:

```
cd src/Mod/BtStudio && python3 -m btstudio.tests
```

## Human GUI check (OVERVIEW.md §9 path 3)

1. `./run-freecad.sh` from the repo root.
2. Workbench tabs should start Start / Sketcher / Part / PartDesign / …
3. Part Design → **New Sketch** → iso view with a grid on the origin planes; click XY in the 3D view or Origin in the tree; no Choose Orientation dialog.
4. Close a loop, leave the sketch, Extrude/Pad: the profile should show as a shaded face, pad preview shaded.
5. **BtStudio** toolbar or **Analysis** menu → **Analysis walkthrough**. Physics = Fluids.
   Later steps (Create FoamCase, Write, Mesh, Solve) are Locked/Coming.
   Click **Create sample cube** — a `Part::Box` appears and geometry goes Done.
   **Create FoamCase** unlocks; Run it. Solver/BC row enables. **Write case tree**
   unlocks; Run it. The dock shows the output directory; `0/U` and
   `system/controlDict` exist. Mesh/Solve stay Coming. No solver process starts.
6. Switch physics to **Structures (FEM)** — step list rebuilds (analysis /
   material / constraints / mesh). Geometry stays Done if the cube is still
   selected; analysis Run is the only enabled button.
7. Select a feature → **Component data table** shows properties.
8. Model tree stays on the **left**; Tasks pops out on the **right** wide enough for the Attachment box.
9. On a Mac, red/yellow/green lights are top-left; there should be no min/max/close on the top-right.
