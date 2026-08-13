# Modern CAD foundation (FreeCAD_BT)

The living design plan and work tracker is now:

**`Documents/modern-cad-design.tex`** (compile with `cd Documents && ./build.sh`).

This markdown note is a short companion. Status, IDs (A1–G4), sequencing, and the work log live in the LaTeX document.

## 1. Smoother running on Apple M5 (and M4)

The 3D view is still **OpenGL via Coin3D + `QOpenGLWidget`**. On macOS that
OpenGL is Apple’s **Metal translation layer** (`OpenGL 2.1 Metal - 90.x`).
M5 GPUs are Metal-4 oriented; the translation path is the known lag/crash
source (upstream reports on M5 MacBook Air + macOS Tahoe, and slow Sketcher
recompute on M4). Safe mode does not fix it. FreeCAD 1.0 is often more
stable than 1.1/1.2dev because of Qt 6.8 + Tahoe interaction
(`QMacAccessibilityElement` UAF, Qt #30720-class bugs).

What actually helps, in order:

1. **Near term (done / do this on the Mac build):** vsync
   (`QSurfaceFormat::setSwapInterval(1)` on macOS), keep TBB import,
   Apple Silicon `arm64` + optional `-mcpu=apple-m1` tuning, and the
   existing **Preferences → Display → 3D View → Use software OpenGL**
   fallback if the viewport is unstable. Restart after changing it.
2. **Qt:** prefer a Qt newer than 6.8.3 on Tahoe when you build.
3. **Real fix (not started):** C5 Metal / Qt RHI viewport. More OpenGL
   tweaks will not close the M5 gap.

Do not treat extra OpenGL contexts, the nav cube, or stylesheet chrome as
the root cause.

## 2. Fusion-style ribbon + Home dashboard

Classic stacked `QToolBar`s are the default FreeCAD command strip. This
fork replaces them with a **Fusion-style ribbon** that consumes the same
workbench `ToolBarItem` tree (so every existing command still appears).

- Preference: **Edit → Preferences → General → Use Fusion-style ribbon**
  (`BaseApp/Preferences/MainWindow/UseRibbon`, default on).
- The ribbon is **hidden on the Start/Home dashboard**. Opening a document
  (or leaving Home) shows it.
- Classic toolbars are hidden while the ribbon is on (toggle actions are
  hidden so their visibility is not saved as “off”).
- Mac unified title-bar chrome (traffic lights) stays; the ribbon lives
  above the MDI area, not inside the 22 px title bar.

Home is a **dashboard**, not a ribbon landing page:

- Metric placeholders (recent files, project count, graphics backend) for
  later health / solver / license widgets.
- **Projects:** create a folder + `.freecad-project` marker, list them,
  open a file from that folder.
- Existing new-file cards, recent files, examples, custom folder.

Recommended dashboard additions later (not built yet):

- Templates (Part, Assembly, Drawing) and “continue last Body”
- Document health (recompute errors, sketch solver status)
- Pinned folders and in-page command search
- Units / navigation style status
- What’s new / first-run tips
- Mac GPU warning when the OpenGL renderer string looks like Metal 90.x
- License / rebuild timestamp for this fork

## 3. SolidWorks-like facelift (recommendation + first tokens)

FreeCAD theming is **YAML tokens + `FreeCAD.qss`**, not a C++ skin. A SW
facelift is a preference pack, not a widget rewrite.

Shipped packs:

- **Modern CAD Light** — cool gray chrome `#F5F5F7`, accent `#0066B3`,
  flat toolbar padding, light-gray 3D background, blue selection.
- **Modern CAD Dark** — graphite `#2D2D30`, brighter blue accent.

Apply from Preferences → General → Preference Packs, on top of the
**Modern CAD** behavior pack (nav + ribbon + combo view).

Further look work, when you are on the Mac:

- Larger icons (24/32) and denser Feature tree
- Viewport: light gray, no purple classic gradient
- PartDesign preview colors in `StyleParameters.h`
- Optional custom icon set (SW-like sketch/feature glyphs)
- Ribbon: large icon + caption, not icon-only

## 4. Modeling / simulation — first principles

**PartDesign today:** `Body` + `Tip` + history (`Pad`/`Pocket`/`Fillet` via
`ProfileBased` / `DressUp`). Recompute is `App::Document::recompute()`
topo-sort. Gaps vs SolidWorks: no real rollback bar, topological naming
still fragile, sketch is a separate object, no single FeatureManager.

**Assembly:** `AssemblyObject` + OndselSolver joints (kinematic), not SW
mates / in-context FEA.

**FEM:** `FemAnalysis` plus external solvers. CalculiX is the structural
workhorse. **Elmer** is the continuum-PDE path (elasticity, heat, flow,
EM equation objects).

This drop adds **FEM → First Principles Study (WIP)**: an Elmer analysis
with elasticity + heat equations, labeled as work in progress. It does
**not** replace CalculiX, add assembly-wide contact, or invent a SW
Simulation study tree. Next steps: guided equation wizard, mesh/material
checklist, then contact.

## 5. Closing the SolidWorks gap from the FreeCAD foundation

Order that matches this codebase (do not start with Metal or a ribbon-only
skin):

1. **Shell** — Home dashboard + ribbon over existing commands (this drop).
2. **Look** — YAML/QSS/icon packs (tokens started; iterate on Mac).
3. **Modeling kernel UX** — Body/Tip, naming, rollback, sketch-in-tree.
4. **Mac smoothness** — Qt/OpenGL mitigation now; Metal later.
5. **Simulation** — guided CalculiX + Elmer first-principles WIP (stub in).
6. Keep menu-bar File/Edit/View; ribbon is the command strip, not a
   replacement for native macOS menus.

Existing users: navigation defaults apply to **new** profiles. Ribbon
defaults **on** (`UseRibbon` true). Turn it off in General preferences
if you want classic toolbars back.
