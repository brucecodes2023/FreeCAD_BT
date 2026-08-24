# BtStudio — fork-only overlay (Tier 4)

Python module loaded with `FreeCAD -M src/Mod/BtStudio`. It does **not**
edit `src/Gui` or `src/Mod/Fem`. See `OVERVIEW.md` conflict tiers.

## What it does on launch

- Reorders the workbench selector once: Sketch → Part → Part Design → Assembly → FEM
- Enables Sketcher snaps / auto-constraints and PartDesign transparent preview
- Splits Combo View so Tasks can sit as a **right tabbed sidebar** (or float)
- macOS: red/yellow/green traffic lights in the **top-left**, replacing Fusion's min/max/close on the right (no unified toolbar — that popped Menu)
- Trackpad overlay: two-finger pan, Shift+scroll zoom, Cmd/Ctrl+scroll rotate, pinch zoom
- Commands (also inserted next to stock New Sketch / FEM Analysis):
  - **New Sketch (iso planes)** — isometric + origin planes, no attachment dropdown
  - **FEM walkthrough** — right-sidebar checklist
  - **Auto mesh** — Gmsh `h = bbox_diagonal / 20`, MeshRegion on selected faces
  - **Feature history** — PartDesign Tip slider (Fusion-style rollback)
  - **Component data table** — selected-object properties
  - **FEM theory guide** — opens `docs/FEM_THEORY_GUIDE.md`

## Docs

| File | Notes item |
|---|---|
| `docs/FEM_THEORY_GUIDE.md` | Full FEM theory |
| `docs/FIRST_PRINCIPLES.md` | Fluids / propulsion / robotics / electronics |
| `docs/ANSYS_MESHING_MAP.md` | Concentrations already in Gmsh objects |
| `docs/OPENFOAM_ARCHITECTURE.md` | Future Fluent-like module |

## Tests

```
cd src/Mod/BtStudio && python3 -m btstudio.tests
```

## Human GUI check (OVERVIEW.md §9 path 3)

1. `./run-freecad.sh` from the repo root.
2. Workbench tabs should start Start / Sketcher / Part / PartDesign / …
3. Part Design → **New Sketch (iso planes)** → iso view, click XY or a face; no combo box.
4. Extrude a pad: transparent preview checkbox on, shaded preview visible.
5. FEM → **FEM walkthrough** dock on the right → **Auto mesh** on a solid.
6. Select a feature → **Component data table** shows properties.
7. On a Mac, red/yellow/green lights are top-left; there should be no min/max/close on the top-right.
