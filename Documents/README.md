# Modern CAD design plan

GitHub does not render LaTeX. **This page is the copy to keep open in a browser tab** while we work. Refresh after each push.

| Edition | Open |
|---|---|
| **This page** (always readable on GitHub) | you are here |
| **PDF** (GitHub’s built-in viewer) | [modern-cad-design.pdf](modern-cad-design.pdf) |
| **LaTeX source** (typeset edition) | [modern-cad-design.tex](modern-cad-design.tex) |
| **PR** | [FreeCAD_BT#2](https://github.com/brucecodes2023/FreeCAD_BT/pull/2) |

PDF rebuilds: the **Design PDF** GitHub Action runs when the `.tex` file changes. Open the Action run → **Artifacts** → `modern-cad-design`. The committed PDF above is also updated whenever we rebuild during a coding pass.

IDs are stable. When work lands, flip the status here **and** in the `.tex`, then add a work-log line.

---

## Product thesis

SolidWorks is the target *feel* (FeatureManager, CommandManager-like strip, familiar mouse, guided simulation). Fusion is the target *shell* (ribbon while modeling, dashboard on launch). FreeCAD is the *foundation* (OCCT kernel, Body/Tip history, workbenches, CalculiX + Elmer).

Close the gap in this order:

1. **Shell** — Home dashboard + Fusion-style ribbon over existing commands.
2. **Look** — YAML tokens, QSS, icons. Not a C++ widget rewrite.
3. **Modeling UX** — Body/Tip, naming, rollback, sketch-in-tree.
4. **Mac smoothness** — Qt/OpenGL mitigation now; Metal later.
5. **Simulation** — guided CalculiX plus Elmer first-principles as WIP.

Keep the native macOS menu bar. The ribbon is the command strip, not a replacement for File / Edit / View.

Constraints: source-only until a Mac checkout launches the GUI; work from FreeCAD extension points; effort ratings are technical scope, not calendar time.

**Current phase: 3** (shell + look v0). Do not pull modeling-kernel or Metal work forward until a Mac build has validated Phase 3 visually.

---

## Status tracker

### Shipped and native Mac

| ID | Item | Status | Notes |
|---|---|---|---|
| A1 | SolidWorks nav default | **Done** | New profiles only; existing `User.cfg` unchanged. |
| A2 | Modern CAD behavior pack | **Done** | Nav, cube, combo view, ribbon flag. |
| A3 | View cube defaults | **Done** | Top-right, size 132. |
| A4 | First-start onboarding | **Done** | Applies Modern CAD pack once. |
| A5 | Fusion 360 nav class | **Done** | Additive; MMB pan / Shift+MMB orbit. Default stays SolidWorks. |
| A6 | Fusion-style ribbon | **Partial** | QAT, overflow », captions, sketch contextual tabs. Mac visual QA remaining. |
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
| D1 | Home dashboard | **Partial** | Metrics, tips, command search, projects, new-file cards. |
| D2 | Project folders | **Partial** | Create + list; open file from folder. |
| D3 | Dashboard health widgets | **Partial** | Drawing + Continue cards; recompute errors; GPU warning; units/nav; tips; command search. |
| E1 | Modern CAD Light/Dark tokens | **Partial** | Cool gray + SW blue; iterate on Mac. |
| E2 | Denser Feature tree / icons | **Partial** | Pack: 32px toolbars, tree icon 24 / indent 10. |
| E3 | Viewport / PD preview colors | **Partial** | Gradient off; dress-up preview is blue-gray not magenta. |
| E4 | Custom sketch/feature icons | Later | Optional icon set. |
| F1 | Rollback bar | Later | Body/Tip history UX. |
| F2 | Topological naming UX | Later | Kernel work, not chrome. |
| F3 | Sketch-in-tree FeatureManager | Later | Single tree like SW. |
| F4 | In-context assembly edits | Later | Beyond Ondsel joints. |
| G1 | First Principles study stub | **WIP** | Elmer elasticity + heat; labeled WIP. |
| G2 | Guided equation wizard | **Partial** | Mesh / material / BC checklist before solve. |
| G3 | CalculiX study presets | **Partial** | Static + thermal wrappers; no auto-mesh. |
| G4 | Assembly contact FEA | Later | Large gap vs SW Simulation. |

---

## Sequencing

| Phase | Focus | Items |
|---|---|---|
| 1 | Familiar defaults | A1, A3, A2, A4 **Done** |
| 2 | Native Mac chrome + arm64 | B1, B2, B4, C1, C2, C3 **Done** |
| **3** | **Shell + look v0 (current)** | A6, D1, D2, E1, G1 Partial / WIP |
| 4 | Shell/look polish (source in; Mac QA tonight) | A6 polish, D3, E2–E3 Partial; E4 later |
| 5 | Modeling UX | F1–F4 |
| 6 | Simulation depth + Metal | G4, C5, B3, C4 (A5/G2/G3 started in source) |

---

## Workstream notes

### A — CAD-familiar defaults

- **A1–A4 Done.** SolidWorks nav, turntable, object-center, Modern CAD behavior pack, cube top-right, first-start applies the pack once.
- **A5 Done.** Optional Fusion 360 style: MMB pan, Shift+MMB orbit, scroll zoom. New profiles still default to SolidWorks. Pick it in Preferences → Display → Navigation.
- **A6 Partial.** Ribbon replaces classic toolbars while a document is open; hidden on Home. Shipped polish: Quick Access (New/Save/Undo/Redo), overflow », Fusion-sized captions, sketch-edit contextual tabs, hide classic bars during sketch edit. Still needs Mac visual QA (height vs traffic lights, overflow at laptop widths).

### D — Home dashboard

Landing page must not show the ribbon.

- **D1 Partial.** Home: metric cards, tips banner, command search, projects, new-file / recent / examples.
- **D2 Partial.** Project = folder + `.freecad-project` marker. Not a SolidWorks assembly project yet.
- **D3 Partial.** Drawing (TechDraw) + Continue last file; recompute-error count; live GL renderer + Metal 90.x warning; units/nav card; dismissible tips; command search. Pinned folders / sketch-solver health still later.

### E — SolidWorks-like facelift

YAML tokens + `FreeCAD.qss`, not a C++ skin.

- **E1 Partial.** Modern CAD Light (`#F5F5F7` / `#0066B3`) and Dark (`#2D2D30`). QA on Mac.
- **E2 Partial.** Behavior + theme packs set toolbar icons to 32px and denser tree (icon 24, indent 10).
- **E3 Partial.** Packs keep a flat viewport (no purple gradient). PartDesign dress-up preview is blue-gray instead of magenta.
- **E4 Later.** Custom SW-like sketch/feature glyphs.

### F — Modeling kernel UX

The real SolidWorks gap. Chrome cannot fake it. Do not start F before D/E are usable on a Mac. Work in `src/Mod/PartDesign/` and `src/App/Document.cpp`.

### G — Simulation / first principles

CalculiX = structural workhorse. Elmer = continuum PDEs.

- **G1 WIP.** `FEM_FirstPrinciplesStudy` creates Elmer + elasticity + heat, one-time WIP dialog.
- **G2 Partial.** `FEM_StudyGuidedWizard` checklist: mesh, material, at least one BC; Run calls existing solver.
- **G3 Partial.** `FEM_CalculiXStaticStudy` / `FEM_CalculiXThermalStudy` create analysis + solver + empty material. No auto-mesh, no contact.
- **G4 Later.** Assembly-wide contact.

### B — macOS-native chrome

B0–B2, B4 done. B3 (NSWindow full-size content) later. Ribbon is *not* inside the unified 22 px title bar.

### C — Apple Silicon and M5

The 3D view is OpenGL via Coin3D, translated to Metal on macOS. That translation path is the M4/M5 lag. C1–C3 done. C5 Metal/Qt RHI is the real fix; near-term is vsync + software OpenGL. C4 (defer InitGui.py) later.

---

## Work log

Newest first.

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

### 1. Prerequisites

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
