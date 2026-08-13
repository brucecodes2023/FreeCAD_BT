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
| A5 | Fusion 360 nav class | Later | New `UserNavigationStyle` subclass. |
| A6 | Fusion-style ribbon | **Partial** | v0 over `ToolBarItem`; hide on Home. Polish remaining. |
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
| D1 | Home dashboard | **Partial** | Metrics placeholders, projects, existing file cards. |
| D2 | Project folders | **Partial** | Create + list; open file from folder. |
| D3 | Dashboard health widgets | Later | Recompute errors, solver, templates, search. |
| E1 | Modern CAD Light/Dark tokens | **Partial** | Cool gray + SW blue; iterate on Mac. |
| E2 | Denser Feature tree / icons | Later | 24/32 px, less padding. |
| E3 | Viewport / PD preview colors | Later | No purple gradient; `StyleParameters.h`. |
| E4 | Custom sketch/feature icons | Later | Optional icon set. |
| F1 | Rollback bar | Later | Body/Tip history UX. |
| F2 | Topological naming UX | Later | Kernel work, not chrome. |
| F3 | Sketch-in-tree FeatureManager | Later | Single tree like SW. |
| F4 | In-context assembly edits | Later | Beyond Ondsel joints. |
| G1 | First Principles study stub | **WIP** | Elmer elasticity + heat; labeled WIP. |
| G2 | Guided equation wizard | Later | Mesh/material/BC checklist. |
| G3 | CalculiX study presets | Later | SW-like static / thermal wrappers. |
| G4 | Assembly contact FEA | Later | Large gap vs SW Simulation. |

---

## Sequencing

| Phase | Focus | Items |
|---|---|---|
| 1 | Familiar defaults | A1, A3, A2, A4 **Done** |
| 2 | Native Mac chrome + arm64 | B1, B2, B4, C1, C2, C3 **Done** |
| **3** | **Shell + look v0 (current)** | A6, D1, D2, E1, G1 Partial / WIP |
| 4 | Shell/look polish on Mac | A6 polish, D3, E2–E4 |
| 5 | Modeling UX | F1–F4 |
| 6 | Simulation depth + Metal | G2–G4, C5, B3, A5, C4 |

---

## Workstream notes

### A — CAD-familiar defaults

- **A1–A4 Done.** SolidWorks nav, turntable, object-center, Modern CAD behavior pack, cube top-right, first-start applies the pack once.
- **A5 Later.** True Fusion 360 mouse model (new C++ class). Do not block shell/look on this.
- **A6 Partial.** Ribbon replaces classic toolbars while a document is open; hidden on Home. Still to polish: Fusion-sized captions, overflow, contextual tabs, QAT, Mac visual QA.

### D — Home dashboard

Landing page must not show the ribbon.

- **D1 Partial.** Home: metric cards, projects, new-file / recent / examples.
- **D2 Partial.** Project = folder + `.freecad-project` marker. Not a SolidWorks assembly project yet.
- **D3 Later.** Templates, health, search, GPU warning, what’s-new.

### E — SolidWorks-like facelift

YAML tokens + `FreeCAD.qss`, not a C++ skin.

- **E1 Partial.** Modern CAD Light (`#F5F5F7` / `#0066B3`) and Dark (`#2D2D30`). QA on Mac.
- **E2–E4 Later.** Icon size, Feature tree density, viewport colors, custom glyphs.

### F — Modeling kernel UX

The real SolidWorks gap. Chrome cannot fake it. Do not start F before D/E are usable on a Mac. Work in `src/Mod/PartDesign/` and `src/App/Document.cpp`.

### G — Simulation / first principles

CalculiX = structural workhorse. Elmer = continuum PDEs.

- **G1 WIP.** `FEM_FirstPrinciplesStudy` creates Elmer + elasticity + heat, one-time WIP dialog.
- **G2–G4 Later.** Wizard, CalculiX presets, assembly contact.

### B — macOS-native chrome

B0–B2, B4 done. B3 (NSWindow full-size content) later. Ribbon is *not* inside the unified 22 px title bar.

### C — Apple Silicon and M5

The 3D view is OpenGL via Coin3D, translated to Metal on macOS. That translation path is the M4/M5 lag. C1–C3 done. C5 Metal/Qt RHI is the real fix; near-term is vsync + software OpenGL. C4 (defer InitGui.py) later.

---

## Work log

Newest first.

- **13 Aug 2026 — GitHub-readable edition.** This README is the tab to keep open; Design PDF workflow rebuilds the typeset PDF.
- **13 Aug 2026 — Documents/ revived.** Living LaTeX plan replaces missing `docs/macos-native-ui-scope.tex`.
- **13 Aug 2026 — Phase 3 v0.** Ribbon (A6), Home + projects (D1/D2), Modern CAD Light/Dark (E1), FEM First Principles WIP (G1), macOS vsync (C5 near-term). PR #2.
- **13 Aug 2026 — Phase 2.** B1 unified toolbar, B2 native chrome, B4 bundle id, C1 arm64, C2 optional LTO/mcpu, C3 TBB.
- **13 Aug 2026 — Phase 1.** A1 SolidWorks nav, A2/A3 pack + cube, A4 first-start.
- **Earlier — env-setup branch.** Original A/B/C scoping LaTeX. Not on this branch.

---

## Rebuild the PDF locally

```bash
cd Documents
./build.sh
```

The repo root gitignores `Makefile`, so `./build.sh` is the compile entry point.
