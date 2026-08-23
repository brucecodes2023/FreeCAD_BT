# Modern CAD design plan

GitHub does not render LaTeX. **This page is the copy to keep open in a browser tab** while we work. Refresh after each push.

| Edition | Open |
|---|---|
| **This page** (always readable on GitHub) | you are here |
| **PDF** (GitHub’s built-in viewer) | [modern-cad-design.pdf](modern-cad-design.pdf) |
| **LaTeX source** (typeset edition) | [modern-cad-design.tex](modern-cad-design.tex) |
| **Robotics notes** (R1 first principles) | [robotics-first-principles-notes.tex](robotics-first-principles-notes.tex) |
| **PR** | [FreeCAD_BT#2](https://github.com/brucecodes2023/FreeCAD_BT/pull/2) |

PDF rebuilds: the **Design PDF** GitHub Action runs when the `.tex` file changes. Open the Action run → **Artifacts** → `modern-cad-design`. The committed PDF above is also updated whenever we rebuild during a coding pass.

IDs are stable. When work lands, flip the status here **and** in the `.tex`, then add a work-log line.

---

## Product thesis

SolidWorks is the target *feel* (FeatureManager, CommandManager-like strip, familiar mouse, guided simulation). Fusion is the target *shell* (ribbon while modeling, dashboard on launch). FreeCAD is the *foundation* (OCCT kernel, Body/Tip history, workbenches, CalculiX + Elmer). **Stay on OCCT** — STEP is must-have; do not plan kernel migration.

Close the gap in this order:

1. **Shell** — Home dashboard + Fusion-style ribbon over existing commands.
2. **Look** — YAML tokens, QSS, icons. Not a C++ widget rewrite.
3. **Modeling UX** — Body/Tip, naming, rollback, sketch-in-tree; **assembly-early** (H1 mates + F4 edit-in-place).
4. **Mac smoothness** — Qt/OpenGL mitigation now; Metal later.
5. **Simulation** — guided CalculiX plus Elmer first-principles as WIP (still waits behind assembly-early).

Keep the native macOS menu bar. The ribbon is the command strip, not a replacement for File / Edit / View.

Constraints: source-only until a Mac checkout launches the GUI; work from FreeCAD extension points; effort ratings are technical scope, not calendar time.

**Current phase: 5** (modeling UX / assembly-early). **H1 mates + F4 edit-in-place are P0** together — not “mates first, F4 later.” Robotics runs **parallel with mates**. Drawings and Sims still wait. Fusion naming + wheel-pan are active UX. Phase 3 shell/look is in daily use on Mac. Phase 4 polish is in (D3 sketch health, denser tree). Do not start F2 topological naming, C5 Metal, B3, E4, or G4 yet.

---

## Status tracker

### Shipped and native Mac

| ID | Item | Status | Notes |
|---|---|---|---|
| A1 | SolidWorks nav default | **Done** | New profiles only; existing `User.cfg` unchanged. Scroll/wheel → pan; Shift → zoom; Cmd → orbit. |
| A2 | Modern CAD behavior pack | **Done** | Nav, cube, combo view, ribbon flag. |
| A3 | View cube defaults | **Done** | Top-right, size 132. |
| A4 | First-start onboarding | **Done** | Applies Modern CAD pack once. |
| A5 | Fusion 360 nav class | **Done** | Additive; MMB pan / Shift+MMB orbit. Default stays SolidWorks. |
| A6 | Fusion-style ribbon | **Done** | Workbench tabs, large/small groups, overflow », native Mac menus. |
| B0 | Traffic lights already native | **Done** | Finding; no code move. |
| B1 | Unified title + toolbar | **Done** | `setUnifiedTitleAndToolBarOnMac(true)`. |
| B2 | Native dock/toolbar chrome | **Done** | Cocoa chrome; `macos-native-chrome.qss`. |
| B3 | NSWindow full-size content | Later | New `.mm` shim. |
| B4 | Bundle id + dark mode | **Done** | `org.freecad.FreeCAD`; Aqua appearance off. |
| C1 | arm64 + macOS 11 pin | **Done** | CMake helpers + conda-macos preset. |
| C2 | Optional LTO / apple-m1 | **Done** | Off by default. |
| C3 | Enable TBB | **Done** | `HAVE_TBB` + ImportOCAF. |
| C4 | Defer InitGui.py | Later | Startup ordering risk. |
| C5 | Metal / Qt RHI viewport | Later | Real M5 fix. Near-term: vsync + software GL. |

### Shell, look, modeling, simulation

| ID | Item | Status | Notes |
|---|---|---|---|
| D1 | Home dashboard | **Partial** | Search, Start a design, pinned folders, recents, metrics. |
| D2 | Project folders | **Done** | Create, pin, unpin, open a file from the folder. |
| D3 | Dashboard health widgets | **Done** | Recompute errors + sketch DoF/open-contour on the Model health card. |
| E1 | Modern CAD Light/Dark tokens | **Partial** | Cool gray + SW blue; iterate on Mac. |
| E2 | Denser Feature tree / icons | **Done** | Pack: 32px toolbars, tree icon 20 / indent 8; QSS item padding. |
| E3 | Viewport / PD preview colors | **Partial** | Gradient off; dress-up preview is blue-gray not magenta. |
| E4 | Custom sketch/feature icons | Later | Optional icon set. |
| F1 | Rollback bar | **Partial** | Tip slider + after-Tip italic/grey icons. Not full SW suppress of after-Tip features. |
| F2 | Topological naming UX | Later | Kernel work, not chrome. |
| F3 | Sketch-in-tree FeatureManager | Later | Single tree like SW. |
| **F4** | **Edit-in-place / in-context** | **P0 / Partial** | Dbl-click Edit Part + Return; `HoldIsolate`. Not full SW in-place. |
| **H1** | **Assembly mates UX** | **P0 / Partial** | Guided Insert Mate… + Ref1/Ref2 hints + solve/ground messages. Ships with F4. |
| **R1** | **Robotics from Assembly** | **Partial** | Serial: `Robot_FromAssembly` → trajectory (+ DH CSV). Drone: `Robot_ExportJoints` → joint inventory JSON/CSV (no multi-branch IK yet). WB renamed Robotics. |
| G1 | First Principles study stub | **WIP** | Elmer PDE picker via `physics_modules` registry; addons register factories. |
| G2 | Guided equation wizard | **Partial** | Checklist + module catalog + drone/robot CalculiX quick-starts (no CFD). |
| G3 | CalculiX study presets | **Partial** | Static + thermal wrappers; no auto-mesh. |
| G4 | Assembly contact FEA | Later | Large gap vs SW Simulation. |

---

## Sequencing

| Phase | Focus | Items |
|---|---|---|
| 1 | Familiar defaults | A1, A3, A2, A4 **Done** |
| 2 | Native Mac chrome + arm64 | B1, B2, B4, C1, C2, C3 **Done** |
| 3 | Shell + look v0 | A6 **Done**; D1/E1 Partial; D2 **Done**; G1 WIP |
| 4 | Shell/look polish | D3 **Done**; E2 **Done**; E3 Partial; E4 later |
| **5** | **Modeling UX (current)** | F1 **Partial**; **H1 + F4 P0** (assembly-early); F2/F3 later |
| **5b** | **Assemblies + robotics** | H1 mates; F4 edit-in-place; Robotics **parallel**; Drawings/Sims wait |
| 6 | Simulation depth + Metal | G1 physics registry WIP; G2/G3 Partial; G4, C5, B3, C4 later |

---

## Workstream notes

### A — CAD-familiar defaults

- **A1–A4 Done.** SolidWorks nav, turntable, object-center, Modern CAD behavior pack, cube top-right, first-start applies the pack once.
- **A5 Done.** Optional Fusion 360 style: MMB pan, Shift+MMB orbit, scroll zoom. New profiles still default to SolidWorks. Pick it in Preferences → Display → Navigation.
- **A6 Done.** Ribbon replaces classic toolbars while a document is open; hidden on Home. Workbench tabs with icons; large/small command groups (Helpers, Modeling, Dress-Up, …); overflow `»`; File/Edit stay in the native Mac menu. Combo View floats over the 3D view (left overlay), Fusion-style.

### D — Home dashboard

Landing page must not show the ribbon.

- **D1 Partial.** Home: search, Start a design cards, pinned folders, recents, then metric cards.
- **D2 Done.** Project = folder + `.freecad-project` marker. Pin Folder keeps any directory on Home; right-click unpins. Not a SolidWorks assembly project.
- **D3 Done.** Drawing (TechDraw) + Continue last file; Model health card (recompute errors + underconstrained / open-contour sketches); live GL renderer + Metal 90.x warning; units/nav card; dismissible tips; command search.

### E — SolidWorks-like facelift

YAML tokens + `FreeCAD.qss`, not a C++ skin.

- **E1 Partial.** Modern CAD Light (`#F5F5F7` / `#0066B3`) and Dark (`#2D2D30`). QA on Mac.
- **E2 Done.** Behavior + theme packs set toolbar icons to 32px and denser tree (icon 20, indent 8, no extra item padding). QSS tightens `QTreeWidget` rows. Re-apply the pack if an existing profile still has the old sizes.
- **E3 Partial.** Packs keep a flat viewport (no purple gradient). PartDesign dress-up preview is blue-gray instead of magenta.
- **E4 Later.** Custom SW-like sketch/feature glyphs.

### F — Modeling kernel UX

The real SolidWorks gap. Chrome cannot fake it.

- **F1 Partial.** History slider under Combo View walks solid features and sets `Tip`. Drag is one undo. Features after the Tip are italic + greyed in the tree (visual only; not `Suppressed`). F2/F3 stay later.
- **H1 P0 / Partial (with F4).** Guided `Assembly_CreateMate` picker (SW/Fusion names + grounded banner). Joint task shows Reference 1/2 pick progress; solver codes (−6 ungrounded, conflicts, …) print clear messages. Ground-first insert dialog uses Fix/Ground wording. Prefs: Solve while creating mates.
- **F4 P0 / Partial.** Double-click component (3D or tree Link) or `Assembly_EditPart` / `Assembly_ReturnFromEdit`: isolate (`HoldIsolate`), activate Body for PartDesign, Return clears isolate, reactivates assembly, recomputes + solves. Not full SW in-place.

### G — Simulation / first principles

CalculiX = structural workhorse. Elmer = continuum PDEs. Custom modules register via `femtools.physics_modules`.

- **G1 WIP.** `FEM_FirstPrinciplesStudy` opens a module picker (defaults: Elmer elasticity + heat) through `femtools.physics_modules`; addons register more factories.
- **G2 Partial.** `FEM_StudyGuidedWizard` checklist + registered-module catalog + drone/robot quick-starts (CalculiX static/thermal only; no CFD).
- **G3 Partial.** `FEM_CalculiXStaticStudy` / `FEM_CalculiXThermalStudy` create analysis + solver + empty material. No auto-mesh, no contact.
- **G4 Later.** Assembly-wide contact.

### B — macOS-native chrome

B0–B2, B4 done. B3 (NSWindow full-size content) later. Ribbon is *not* inside the unified 22 px title bar.

### C — Apple Silicon and M5

The 3D view is OpenGL via Coin3D, translated to Metal on macOS. That translation path is the M4/M5 lag. C1–C3 done. C5 Metal/Qt RHI is the real fix; near-term is vsync + software OpenGL. C4 (defer InitGui.py) later.

---

## Work log

Newest first.
- **22 Aug 2026 — R1 drone joint inventory.** `Robot_ExportJoints` (**Export Assembly Joints**) writes generic JSON+CSV joint inventory (Revolute/Slider/Cylindrical/Fixed/Grounded) for multi-rotor/drone layouts — separate from serial **Trajectory from Assembly**. No non-serial kinematics solver yet.
- **22 Aug 2026 — Pinch zoom-only + Fusion invert + tree names + STEP→Body.** Pinch zooms only (scroll/wheel still pan; Shift+scroll zooms; Cmd+scroll orbits). `InvertZoom` default + Modern CAD pack match Fusion. PartDesign tree Labels use Fusion vocabulary (Extrude / Extrude Cut / …) while TypeId stays Pad/Pocket/…. STEP import defaults to wrapping solids in PartDesign::Body (`ImportAsBody`). Drawings/Sims still wait.
- **22 Aug 2026 — R1 Robotics bridge.** `Robot_FromAssembly` exports Assembly Revolute/Slider/Cylindrical joints to a Robot trajectory (and approximate DH CSV for the legacy 6-axis solver). Workbench menu label **Robotics**; Modern CAD packs stop disabling RobotWorkbench. Drawings/Sims still wait.


- **22 Aug 2026 — F4 double-click Edit Part.** Double-click a component in the 3D view (assembly active) or tree Link → `Assembly_EditPart`. Tree path redirects Link Transform via `signalInEdit`. Return recomputes + solves mates. Still Partial (not mate-driven in-place).
- **22 Aug 2026 — F4 Partial edit-in-context.** `Assembly_EditPart` / `Assembly_ReturnFromEdit` (toolbar, context menu, task watcher). Isolates the component with `HoldIsolate` so selection/transactions do not clear fade; activates Body/PartDesign; Return restores assembly edit. Not full SW in-place — F4 remains P0/Partial.
- **22 Aug 2026 — Product sequencing (research).** F4 edit-in-place elevated to **P0 with H1** (assembly-early; not “later after mates-only”). Stay on OCCT (STEP must-have; no kernel migration). Robotics parallel with mates; Drawings/Sims still wait. Fusion naming + wheel-pan remain active UX.
- **22 Aug 2026 — Mac scroll = pan (trackpad + wheel).** Unmodified two-finger / mouse-wheel pans; Shift+scroll zooms; Cmd/Option+scroll orbits. Classic zoom-on-scroll is Preferences → Display → Navigation → “Zoom with scroll / mouse wheel” (`TrackpadScrollZooms`). SolidWorks + Fusion 360 hint strings updated. PartDesign ribbon/menus use Fusion vocabulary (Extrude, Extrude Cut, Sketch, Shell, Sweep, Coil, …); Create/Modify/Construct panel titles; Hole/Revolve/etc. large ribbon buttons.
- **22 Aug 2026 — TechDraw first-ship ease.** Default template → ISO A3 landscape (relative pack paths OK); Modern CAD pack sets third-angle + ASME dims; `TechDraw_QuickDrawing` creates page + Front/Top/Right; ribbon/toolbars surface Multiview / Quick Drawing with clearer labels.
- **22 Aug 2026 — G1/G2 physics extensibility.** `physics_modules` register API + catalog; First Principles equation picker; Guided Wizard lists modules and drone/robot CalculiX static/thermal quick-starts (no CFD).
- **22 Aug 2026 — H1 mate panel deepen.** Insert Mate… uses a guided picker (type list + grounded banner). Joint task shows Reference 1/2 slots and pick-progress hints; solver status codes map to clear Report/status messages; ground-first dialog uses SW/Fusion wording; prefs expose “Solve while creating mates”.
- **22 Aug 2026 — First-ship priorities + Phase 5/H1.** User thesis: blend SW+Fusion; Assemblies mates must ship; Parts/Assemblies/Drawings/Robotics for drones/robots; keep Python/workbenches. F1 after-Tip tree greying; Pad/Pocket reject open-contour sketches; `Assembly_CreateMate` SW→Ondsel map; `femtools.physics_modules` registry for first-principles addons. F2/F4/C5/G4 still later.
- **14 Aug 2026 — Tasks pin + Sketch tab + click-in-view plane.** Right overlay stays flush to the window edge (400px open, ~28px tab closed). Clicking the tab pins it open. Create Sketch shows a Sketch tab and a Sketch plane field; click XY/XZ/YZ or a face in the 3D view (no attachment dropdown).
- **14 Aug 2026 — Tasks tab from the right edge.** Idle Tasks is a ~28px tab on the window’s right edge and grows left into the view. Body origin planes stay shaded (XY/XZ/YZ) after leaving a sketch.
- **14 Aug 2026 — Control+trackpad orbit.** Hold Control and two-finger swipe to orbit (Option+swipe still orbits; Shift/Command+swipe pans).
- **14 Aug 2026 — Idle Tasks is a tab.** Empty Tasks overlay collapses to an inner-edge tab inside the 400px panel; sketch/Pad dialogs expand that opaque panel and rename the tab to the feature (e.g. Sketch).
- **13 Aug 2026 — Shell contrast + task sidebar.** Darker ribbon with group dividers; sketch/tool dialogs stay in a 360px right overlay; left Feature tree has a drag edge and collapse chrome; sketch grid stays after leaving edit.
- **13 Aug 2026 — Phase 4 polish + F1 rollback.** Home Model health includes sketch DoF and open contours. Feature tree denser (icon 20 / indent 8). History slider under Combo View rolls Body Tip. F2–F4, C5 Metal still later.
- **13 Aug 2026 — Floating browser + Home restack.** Combo View overlays the 3D view (Fusion-style). Home leads with search and Start a design, then pinned folders.
- **13 Aug 2026 — A6 ribbon accepted; D2 pin folders.** Workbench-tab ribbon with large/small commands. Home can pin/unpin folders.
- **13 Aug 2026 — Remaining IDs (source).** A5 Fusion nav; A6 QAT/overflow/contextual tabs; D3 dashboard widgets; E2/E3 density + PD previews; G2 wizard; G3 CalculiX presets. Mac compile walkthrough added. F1–F4, C5 Metal, B3, C4, E4, G4 still later.
- **13 Aug 2026 — GitHub-readable edition.** This README is the tab to keep open; Design PDF workflow rebuilds the typeset PDF.
- **13 Aug 2026 — Documents/ revived.** Living LaTeX plan replaces missing `docs/macos-native-ui-scope.tex`.
- **13 Aug 2026 — Phase 3 v0.** Ribbon (A6), Home + projects (D1/D2), Modern CAD Light/Dark (E1), FEM First Principles WIP (G1), macOS vsync (C5 near-term). PR #2.
- **13 Aug 2026 — Phase 2.** B1 unified toolbar, B2 native chrome, B4 bundle id, C1 arm64, C2 optional LTO/mcpu, C3 TBB.
- **13 Aug 2026 — Phase 1.** A1 SolidWorks nav, A2/A3 pack + cube, A4 first-start.
- **Earlier — env-setup branch.** Original A/B/C scoping LaTeX. Not on this branch.

---

## Compile and launch on a Mac (tonight)

This fork is meant to be **built from source on Apple Silicon** with pixi (the same path CI uses). Do not treat a Linux VM as a visual preview.

### 1. Prerequisites

```bash
xcode-select --install          # skip if already installed
curl -fsSL https://pixi.sh/install.sh | bash
# restart the terminal, or: export PATH="$HOME/.pixi/bin:$PATH"
```

You need Xcode Command Line Tools, pixi, and a network connection for conda-forge. Homebrew Qt is **not** used; pixi pins Qt 6.8.3 and OCCT 7.8.

**Disk (Apple Silicon release, this fork).** There is no prebuilt `.app` on the branch — size is what `pixi` + Ninja will create on your Mac:

| What | Typical on disk | Notes |
|---|---|---|
| Git clone (source + history) | **~6–9 GB** | This tree is ~6 GB files + ~3 GB `.git`. |
| `pixi install` (`.pixi/` + cache) | **~2–5 GB** | osx-arm64 lock is ~0.64 GB compressed; unpacked Qt/OCCT/VTK/LLVM is several GB. APFS reflinks keep cache + env from fully doubling. |
| `pixi run build-release` (`build/release/`) | **~6–12 GB** | `.o` files + linked binaries. Debug is much larger — do not use `configure-debug` tonight. |
| `pixi run install-release` | **~0.5–1.5 GB extra** | Copies into `.pixi/envs/default`. Optional for a first launch; `pixi run freecad-release` runs `build/release/bin/FreeCAD`. |
| ccache | **up to ~1 GB** | Speeds rebuilds. |

Plan on **~20 GB free** at peak (clone + env + objects while linking). **30 GB free** is comfortable. After a successful launch you can delete `build/release` only if you do not need to rebuild; keeping it makes the next compile incremental.

Known-good launch target for this drop: **M-series + pixi `conda-macos-release`**. **macOS 27 beta** is newer than the Qt 6.8.3 pin; compile or GUI crashes on the beta SDK are possible. If configure/build fails, save the last 50 lines of the log. If it launches but the 3D view is bad, software OpenGL (below) is the first switch — not a Metal rewrite.

### 2. Clone this branch

```bash
git clone https://github.com/brucecodes2023/FreeCAD_BT.git
cd FreeCAD_BT
git checkout cursor/modern-cad-phase1-953c
```

If you already cloned, `git fetch origin && git checkout cursor/modern-cad-phase1-953c && git pull`.

### 3. Configure, build, install

```bash
pixi install
pixi run initialize             # git submodules
pixi run configure-release      # CMake preset conda-macos-release (arm64, macOS 11)
pixi run build-release          # first build is long (often 20–60 min on M5 Pro)
# pixi run install-release      # optional; launch uses build/release/bin/FreeCAD
```

Optional (off by default): after configure, you can re-run CMake with `-DFREECAD_USE_LTO=ON -DFREECAD_APPLE_SILICON_TUNING=ON`. Skip these on the first successful launch.

### 4. Launch with a fresh user profile

Existing `User.cfg` is **not** migrated (A1). Use a throwaway home so you see the new defaults:

```bash
export FREECAD_USER_HOME="$HOME/freecad-modern-cad-fresh"
mkdir -p "$FREECAD_USER_HOME"
pixi run freecad-release
```

That runs `build/release/bin/FreeCAD`. Config lands in `$FREECAD_USER_HOME/user.cfg` instead of `~/Library/Preferences/FreeCAD/`.

**This does not put FreeCAD in `/Applications`.** After the binary exists:

```bash
pixi run macos-app
open ~/Applications/FreeCAD_BT.app
```

That `.app` is a **launcher** (Dock / Launchpad). It still needs this git checkout and `build/release`. Optional: `./Documents/macos-app.sh --system` also copies to `/Applications` (sudo).

**Standalone app (then you can delete the repo).** After the GUI from `pixi run freecad-release` looks right:

```bash
pixi run install-release
./Documents/macos-standalone.sh
open ~/Applications/FreeCAD_BT.app
```

That copies Qt/OCCT/the install into `~/Applications/FreeCAD_BT.app` (typically **~2–4 GB**). If *that* copy launches, you can remove the checkout:

```bash
rm -rf /path/to/FreeCAD_BT    # git clone + build/ + .pixi  (~15–20 GB)
```

Keep the `.app`. User prefs stay in `~/Library/Preferences/FreeCAD` (or `FREECAD_USER_HOME`). To change source later, clone again.

### After a successful first launch (shrink local disk)

```bash
pixi run macos-cleanup                 # ccache + debug tree; keeps the release binary
# ./Documents/macos-cleanup.sh --objects   # drop .o files; must rebuild to relink
```

Do **not** delete `.pixi` or `build/release/bin` while using the thin `.app`.

### Full FreeCAD, Apple Silicon toolchain only

Tonight’s build is a **full** FreeCAD: Part, PartDesign, Sketcher, Assembly, FEM, TechDraw, Draft, CAM, BIM, Mesh, and the rest. Do not pass `-DBUILD_CAM=OFF` or similar.

What this fork slims is the **non-Mac toolchain**, not the CAD:

- `pixi.toml` platforms is **`osx-arm64` only** (no Windows, Linux, or Intel Mac package sets). On your M5, `pixi install` never fetched those anyway; this just stops the lockfile from carrying them.
- Windows/Linux **C++ stays**. That is the same PartDesign/CAM/FEM code that runs on Mac. Deleting it would not shrink the clone in a useful way and would block upstream merges.
- `package/WindowsInstaller` is ~1 MB. Removing it does not change your 20 GB build.

After a successful launch, `pixi run macos-cleanup` reclaims ccache and a debug tree. Keep `build/release` if you want incremental rebuilds.

### 5. What to confirm on first launch

1. First-start wizard, then **Home** (no ribbon). Metric cards, tips, command search, New Project, Drawing, Continue.
2. Open or create a Part Design body → Fusion-style ribbon with QAT (New / Save / Undo / Redo) above the tabs. Home still has no ribbon.
3. Preferences → General → **Use Fusion-style ribbon**; off restores classic toolbars.
4. Preference Packs: **Modern CAD** (behavior) plus **Modern CAD Light** or **Dark**.
5. Preferences → Display → Navigation: **SolidWorks** (default) and **Fusion 360** (MMB pan, Shift+MMB orbit).
6. FEM workbench: First Principles Study (WIP), CalculiX Static / Thermal Study, Guided Study Wizard.
7. If the 3D view lags on M4/M5: Preferences → Display → 3D View → **Use software OpenGL**, then **quit and relaunch**.

### 6. After you look at it

Tell us: Mac chip (M1–M5), macOS version, whether the ribbon height fights the traffic lights, whether overflow `»` appears at laptop width, whether Home / ribbon / theme feel SW-or-Fusion-like, and whether the viewport is usable with vsync or needs software OpenGL.

Do **not** start a Metal rewrite from that first launch. C5 stays later until Phase 3 looks right.

To throw away the test profile: `rm -rf "$HOME/freecad-modern-cad-fresh"`.

---

## Rebuild the PDF locally

```bash
cd Documents
./build.sh
```

The repo root gitignores `Makefile`, so `./build.sh` is the compile entry point.
