# FreeCAD_BT — Codebase Overview & Change-Safety Map

**Purpose of this doc:** a map to consult *before* making any change in this repo, so that changes stay cheap to maintain long-term. The single most important fact about this repo:

> **`main` is the fork trunk: upstream `FreeCAD/FreeCAD` plus a small set of *additive, fork-only* files, with zero edits to upstream files.**
> As of 2026-08-23 `main` carries a couple of unique commits that only **add new files** not present upstream (this doc, `run-freecad.sh`, …); upstream is ~172 commits ahead. Because those additions are new files (Tier 4, §4), `git merge upstream/main` never conflicts on them — so `main` is no longer byte-identical to upstream, but stays cheap to sync.

Everything you build from here is fork work. The maintenance strategy: **keep fork work additive** — new files, and where an upstream file must change, minimal marker-bracketed diffs — so that pulling upstream never becomes painful. Every section below serves that goal.

---

## 1. Repository identity

| Fact | Value |
|---|---|
| Upstream | https://github.com/FreeCAD/FreeCAD (remote `upstream`) |
| Fork origin | https://github.com/brucecodes2023/FreeCAD_BT.git (remote `origin`) |
| Version | FreeCAD 26.3.0 dev (`version.json`) |
| License | LGPL-2.1-or-later — **fork additions must remain LGPL-compatible** |
| Language mix | C++ (kernel + GUI core), Python (workbenches, tests, tooling), CMake everywhere |

### Git layout

- `main` — the fork trunk: upstream snapshot + additive fork-only files (no edits to upstream files).
- `upstream/main` — the real project; moves constantly (~daily merges).
- Old `cursor/*` branches on origin — prior fork experiments (ribbon, Fusion nav style, macOS packaging, FEM/Robotics add-ons). **Out of scope** per current direction, but they demonstrate which files upstream churns vs. which are stable.

### Sync discipline (the whole game)

```bash
git fetch upstream
git merge upstream/main          # or rebase if history stays linear
```

The cost of this operation is proportional to how many lines of `main` we touch that upstream also touches. That is exactly what Section 4 quantifies.

---

## 2. Top-level directory map

```
FreeCAD_BT/
├── src/                    # ALL product source lives here
│   ├── Base/               # Core non-GUI lib: types, math, units, Document/Object model, persistence
│   ├── App/                # Application-layer lib: documents, transactions, features, properties
│   ├── Gui/                # GUI lib: MainWindow, ViewProviders, 3D view (Coin3D), dialogs, preferences
│   ├── Main/               # Entry points: MainGui.cpp, MainCmd.cpp, FreeCADGuiPy.cpp
│   ├── Ext/                # freecad Python package wrapper
│   ├── Tools/              # Build-time code generators (e.g. pyi stub generation)
│   ├── 3rdParty/           # VENDORED libraries (OndselSolver, salomesmesh, PyCXX, coin bindings...)
│   ├── MacAppBundle/       # macOS .app skeleton (Info.plist etc.)
│   └── Mod/<Name>/         # One directory per workbench (see §3)
├── cMake/                  # CMake find-modules + FreeCAD_Helpers/*.cmake build logic
├── CMakeLists.txt          # Root build file (options, subdirs)
├── CMakePresets.json       # Configure presets (common/debug/release/conda-*/rpm)
├── data/                   # Example files + test data (not code)
├── tests/
│   ├── src/                # C++ unit tests mirroring src/ (App/Base/Gui/Mod)
│   └── visual/             # Screenshot-regression suite with baselines
├── tools/                  # lint / profiling / rendering helpers
├── contrib/                # IDE configs (clion), debugger helpers
├── package/                # OS packaging (WindowsInstaller, ubuntu, fedora, rattler-build, libpack)
├── .github/workflows/      # CI: build_release.yml + sub_build{Pixi,Ubuntu,Windows}.yml, lint, codeql...
├── pixi.toml / pixi.lock   # Conda-forge dependency environment used by CI and local builds
├── .pre-commit-config.yaml # Lint/format hooks; scoped to specific dirs (see §5)
├── .clang-format/.clang-tidy/.pylintrc
└── version.json            # Version source-of-truth
```

Key takeaway: there are effectively **three layers** — `Base`+`App` (data model), `Gui` (interaction), `Mod/*` (feature workbenches). Almost all safe customization happens in `Mod/*`; almost all dangerous customization happens in `Base`/`App`/`Gui`.

---

## 3. The `src/Mod/` workbenches

Each module is self-contained with a common shape:

```
src/Mod/Foo/
├── App/            # document objects, algorithms (C++)
├── Gui/            # view providers, commands, task panels, .ui files
├── Init.py         # module init (App side)
├── InitGui.py      # workbench registration (GUI side)
├── CMakeLists.txt  # usually just installs Python files
└── *.py            # most modern modules are mostly pure Python
```

Current modules (26.3.0 dev):

`AddonManager, Assembly, BIM, CAM, Draft, Fem, Help, Import, Inspection, JtReader, Material, Measure, Mesh, MeshPart, OpenSCAD, Part, PartDesign, Plot, Points, ReverseEngineering, Robot, Show, Sketcher, Spreadsheet, Start, Surface, TechDraw, TemplatePyMod, Test, Tux, Web`

Notes:

- `Start` = the Home/first-start dashboard (Qt C++).
- `Test` = the Python test framework (`FreeCAD.__unit_test__` registry); run via `FreeCADCmd` console.
- `Tux` = navigation indicator widget.
- `Assembly` embeds the vendored `OndselSolver` from `src/3rdParty`.
- Pure-Python modules (e.g. `Draft`, `Fem`, `BIM`, `CAM`) are the cheapest place to experiment: no rebuild needed, easy to inspect at runtime.

---

## 4. Conflict tiers — where changes hurt later

Upstream is extremely active. When classifying where to put new code, use these tiers:

### Tier 1 — Never modify directly (highest churn, highest blast radius)

These files change in nearly every upstream merge window; edits here cause conflicts on every sync.

- `src/Base/**` — core object model, properties, persistence
- `src/App/**` — document/transaction/recompute engine
- `src/Gui/NavigationStyle.h` — historically huge churn (1,300-line diffs between releases)
- `pixi.lock` — regenerated lockfile; always conflicts; regenerate rather than hand-edit
- Any `.ui` file heavily customized by hand (Qt Designer XML churns badly)

If a feature seems to require touching these, look for an extension point first (§6).

### Tier 2 — Hot but sometimes unavoidable

- `src/Gui/Application.cpp`, `MainWindow.cpp`, `ToolBarManager.cpp`
- `CMakeLists.txt` (root), `cMake/FreeCAD_Helpers/*.cmake`
- `CMakePresets.json`
- Workbench `Workbench.cpp` / `InitGui.py` files (menus/toolbars get reshuffled often)
- `src/Mod/Sketcher`, `src/Mod/PartDesign` App-side files (active development area, e.g. topological-naming work)

Rules if you must touch Tier 2:
1. Keep edits **small, contiguous, and bracketed by marker comments** so a merge conflict is trivially resolvable.
2. Prefer adding a new file + one hook line over editing existing logic.
3. Never reformat or reorder surrounding code — that manufactures conflicts.

### Tier 3 — Safe-ish to modify

- Your own new directories/files anywhere under `src/Mod/<YourThing>/`
- New `.qss` stylesheets, new preference packs (self-contained dirs)
- `package/` scripts, `Documents/`-style docs folders, `contrib/`

### Tier 4 — Zero-conflict by construction (always preferred)

- **External workbenches**: a separate addon-style folder registered like any other `Mod`. FreeCAD loads user-installed addons from the user's application data dir without them living in this git tree at all.
- **Python-only modules** placed in a new `src/Mod/<Name>/` with its own `CMakeLists.txt` (install-only) — upstream never touches your directory.
- Preference packs / parameter YAMLs / QSS in their own files.
- Macros and scripts outside the tree, loaded via user Macro path.

**Default decision rule:** every proposed change starts at Tier 4 and only escalates when proven impossible there.

---

## 5. Conventions enforced by the repo (don't fight these)

- **Formatting/lint gates CI**: `clang-format` (LLVM-derived config), `clang-tidy`, `pylint` (`.pylintrc`), `black/isort/flint` via `.pre-commit-config.yaml`. Note the pre-commit `files:` allowlist covers specific paths (`src/Base|src/Gui|src/Main|most Mods`) — code inside those paths must pass hooks.
- **SPDX headers**: every new file needs `# SPDX-License-Identifier: LGPL-2.1-or-later`.
- **C++ standard**: C++17 (per root `CMakeLists.txt`); Qt6 / OCCT 7.8-era APIs via pixi env.
- **Tests live beside structure**: C++ tests in `tests/src/<layer>/<Module>`, Python tests inside each module (e.g. `src/Mod/Fem/femtest/`). New behavior should come with a test in the matching location, or CI/code-review friction follows.
- **No secrets/binaries** in-tree beyond what already exists (PDFs/docs are exceptions made by past branches).

---

## 6. Extension points (how to customize WITHOUT touching Tier 1/2)

This is the toolkit for low-maintenance customization. In rough order of preference:

1. **New Python workbench/module** (`src/Mod/<Name>/InitGui.py`) — full access to commands, menus, toolbars; zero overlap with upstream files.
2. **Commands registered at runtime** — Python `Command` classes can add menu/toolbar entries to *existing* workbenches from your own module (via `Gui.addCommand` + workbench append) instead of editing their `Workbench.cpp`.
3. **Preference packs + parameter overrides** — `Preferences → General → Preference Packs`; ships `.cfg` + optional QSS; changes behavior/appearance with zero code.
4. **Stylesheets** — drop-in `.qss` plus the existing token-YAML parameter system under `src/Gui/Stylesheets/parameters/`.
5. **ViewProvider override from Python** — replace/augment display behavior per-object-type without touching `src/Gui`.
6. **Document observers / signal hooks** — e.g. `App.addDocumentObserver`, selection observers; react to events instead of patching emitters.
7. **C++: add new files, wire minimal registration** — if C++ is required, put classes in new files and add exactly one line in the corresponding `CMakeLists.txt` + one factory/registration call. Keep the diff to shared files at "one line" size.
8. **Startup plugins** — `Ext/freecad` and `Mod` init ordering allows post-start tweaks from your own module rather than editing `Application.cpp`.

---

## 7. Build system quick reference

**Build & run the development version (macOS, canonical CI-equivalent path):**

```bash
pixi run configure-release && pixi run build-release && ./build/release/bin/FreeCAD
```

**macOS GUI launch gotcha — the "cocoa" plugin failure.** The GUI aborts with
`Could not find the Qt platform plugin "cocoa"` (SIGABRT / exit 134) whenever pixi/rattler
extracts the environment: it marks the Qt plugin dylibs under
`.pixi/envs/default/lib/qt6/plugins/` with the macOS `UF_HIDDEN` flag, and Qt's plugin
scanner (`QDir::Files` without `Hidden`) can't see `libqcocoa.dylib`. This is **not** a build
problem — `FreeCADCmd` (headless) works and the GUI launches fine once the flag is cleared.
Clear it before launching (pixi re-applies it on every env refresh):

```bash
chflags -R nohidden .pixi/envs/default/lib/qt6/plugins
./build/release/bin/FreeCAD
```

`./run-freecad.sh` does this automatically — prefer it for day-to-day launching. Do **not** set
`QT_PLUGIN_PATH` / `QT_QPA_PLATFORM_PLUGIN_PATH`; Qt resolves the plugins relative to
`libQt6Core` on its own, and those overrides can re-trigger the same failure.

**macOS 27 / clang 18 known-good configure overrides.** The stock preset fails on a fresh machine here — apply these once if the build dir is wiped:

```bash
pixi run cmake -S . -B build/release \
  -DCMAKE_OSX_SYSROOT=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk \
  -DCMAKE_CXX_FLAGS="-Wno-elaborated-enum-base -Wno-availability -Wno-nullability-extension" \
  -DFREECAD_3DCONNEXION_SUPPORT=None
```

Why each flag exists:
- `CMAKE_OSX_SYSROOT`: the CLT `MacOSX.sdk` symlink can break after macOS upgrades (`INFINITY` undeclared in libc++ headers); the full Xcode SDK always works.
- Warning suppressions: conda clang 18 vs the newer SDK headers trips `-Werror` on SDK-owned code (elaborated enum, availability, nullability).
- `FREECAD_3DCONNEXION_SUPPORT=None`: the navlib path hardcodes the CLT sysroot and dies with cstddef header-search errors; only needed for 3D-mouse hardware.

Also: default full parallelism (`-j 18`) gets compiler processes killed silently by macOS memory pressure on this 48 GB machine — use `-j 12`.

- First `pixi run` installs the whole pinned toolchain from `pixi.lock`; `configure-*` also refreshes git submodules automatically.
- Binary lands at `build/<config>/bin/FreeCAD` (GUI) and `FreeCADCmd` (headless).
- Incremental rebuild after edits: just `pixi run build-release` again.
- Tests: `./build/release/bin/FreeCADCmd -t 0`.
- Debug variant: swap `release` for `debug` throughout.

- **Presets**: `cmake --preset release` family; `conda-macos*` presets wrap the pixi environment.
- **pixi** drives dependency install (`pixi shell` / `pixi run`) against conda-forge; `pixi.lock` pins everything. CI uses it (`.github/workflows/sub_buildPixi.yml`).
- Adding a dependency = edit `pixi.toml` + regenerate `pixi.lock` (never hand-edit the lock).
- macOS app packaging hooks exist in `src/MacAppBundle/` and `packaging` scripts under `package/`.

---

## 8. Testing map

- **Python unit tests**: `src/Mod/*/...test*.py`, executed through `Mod/Test` framework:
  `FreeCADCmd -c "import FreeCAD, Test; Test.runAll()"` (or targeted: `Test.run('TestFemApp')`).
- **C++ tests**: `tests/src/**` built as part of the normal build; run via ctest.
- **Visual regression**: `tests/visual/` with committed baselines — relevant if you change anything visual (stylesheets, view providers). Baseline updates are expected churn; keep visual changes behind preference packs where possible so baselines don't need constant refreshing.

---

## 9. Feature verification policy (every feature must be proven)

**The gate (hard):** a feature is **not "done" and does not merge off its feature branch until it has been *verified* to actually work** by one of the three paths below. Code without verification stays on its branch. Every feature PR/commit must state **which path verified it and the outcome** (what was run/done, and what was observed). "It compiles" / "it launched" is **not** verification — the feature's own behavior must be exercised and observed end-to-end.

Why: this repo's GUI can't be trusted to merely "look right" — the macOS dev build has a launch gotcha and a rare runtime crash (§7), and upstream churns constantly. Proving each feature is how fork work stays trustworthy and cheap to sync.

**Verification paths — use the cheapest one that actually exercises the feature's real surface:**

1. **Headless script** — *preferred for App/kernel logic.* For document objects, algorithms, properties, persistence — anything not inherently GUI — drive the feature from `FreeCADCmd -c "…"` (or the `Mod/Test` framework, see §8) with a script that **asserts** the result. Cheapest and most reliable; no GUI, no rebuild-to-click. Keep the script with the feature (the module's `*test*.py`).
2. **AI-driven MCP** — *preferred for GUI features, but does not exist yet and must be built.* This would be an MCP server letting the AI drive the running FreeCAD GUI (commands, view providers, dialogs, 3D view) and observe results. Until it exists, GUI features fall to path 3; once built it becomes the default for GUI-level verification.
3. **Human physical test** — *fallback for GUI features today.* The AI prints **explicit numbered steps** in the conversation window — exact menu/click paths, inputs, and the **expected result / pass-fail criteria** — and the user runs them in the GUI (`./run-freecad.sh`) and reports back. The AI records that outcome as the verification.

**Rules of thumb:**
- Match path to surface: `App`/`Base`/kernel → path 1; a command/toolbar/view-provider/dialog/3D-view behavior → path 2 (when available) else path 3.
- A feature spanning both layers (App logic **and** GUI) needs **both** a headless assertion for the logic and a GUI check for the interaction.
- Record the verification in the PR/commit body (path used + what was run + observed result) so reviews and future upstream syncs can trust it.

---

## 10. Parallel work — worktrees & multi-agent

Multiple agents (Claude, Grok, Cursor, …) work in parallel via **git worktrees** so changes never overwrite each other. A Cursor dashboard tracks progress across them.

**Rule: one persistent worktree per agent, one branch per task.** Each agent works its tasks *sequentially* in its own reused directory, so the heavy `build/` / `.pixi` are built once and kept. Every task still gets its own branch (cut from `main`) so PRs stay reviewable and the dashboard can track them.

```bash
# once per agent — create the persistent worktree
git worktree add ../fcbt-worktrees/<agent> -b <agent>/<first-slug> main

# per task, from inside that worktree: main is checked out in the primary
# dir, so base new task branches on origin/main (don't check out main)
git fetch origin && git checkout -b <agent>/<slug> origin/main
```

- **Worktree location (persistent, per agent):** `../fcbt-worktrees/<agent>` — outside the main tree so it never nests or clutters `main`. Reused for all of that agent's tasks.
- **Branch naming (per task): `<agent>/<slug>`** — `<agent>` ∈ {`claude`, `grok`, `cursor`, …}; `<slug>` kebab-case (e.g. `claude/fcbridge-bridge`, `grok/measure-tool`). The dashboard groups by the agent prefix.
- **Merge each task branch to `main` via PR, only after §9 verification.** Delete the merged branch, but **keep the agent's worktree** for the next task.

**Avoiding collisions (the whole point):**

- Keep work **Tier-4 / Python-first** (§4, §6): new files under your own `src/Mod/<Name>/` never collide — and pure-Python features need no rebuild, which is what makes worktrees cheap.
- **Shared files are the hot-spots:** `OVERVIEW.md` (this file), root `CMakeLists.txt`, `src/Mod/CMakeLists.txt`, `pixi.toml`/`pixi.lock`. Touch them in **small, quick PRs**, never in long-lived branches, and never reformat around your change.
- **`.pixi/` and `build/` are per-directory and heavy.** A fresh worktree has neither, and a full C++ build is long. Prefer the main checkout's build for Python-only work; only build inside a worktree when C++ actually changes there.
- **This doc is the guiding file** — it states *what* changes we make and *how* we work. When the workflow changes, update it (small PR) so every worktree inherits the same rules.

---

## 11. Maintenance playbook (the point of all this)

When proposing any change, answer in order:

1. **Can it be a new directory/file?** (Tier 4) → do that.
2. **Can it be Python?** → prefer Python over C++; no rebuilds, smaller conflict surface.
3. **Must edit shared files?** (Tier 2) → smallest possible diff, marker-commented block, no drive-by formatting.
4. **Does it touch Tier 1?** → stop; find an extension point (§6) or accept ongoing maintenance cost explicitly.
5. After any upstream sync: `git fetch upstream && git merge upstream/main`, resolve using the tier map above, then run lint + tests before pushing.

### Sync cadence recommendation

- Fetch upstream regularly (weekly-ish) even when not merging — small frequent merges are dramatically cheaper than rare giant ones.
- Keep a short `CHANGELOG-FORK.md` listing every file on `main` that diverges from upstream (append on every fork change). This is the authoritative conflict checklist during merges. *(Consider starting this file now while divergence = 0.)*

---

## 12. Glossary (for navigating the code)

| Term | Meaning in this codebase |
|---|---|
| `App::DocumentObject` | Base class of every parametric object in a document |
| `ViewProvider` | GUI counterpart of a DocumentObject (display + interaction) |
| `FeaturePython` | Python-implemented document object |
| Workbench | A named set of commands/toolbars (`Mod/*/InitGui.py`) |
| `Tip` | PartDesign Body's active end-of-history feature (rollback semantics) |
| Recompute | Dependency-graph-driven re-execution of touched objects |
| LibPack | Prebuilt Windows dependency bundle (`package/libpack-windows`) |
| Coin3D | Open Inventor-compatible 3D scene library backing the 3D view |
| OCCT / OpenCASCADE | The geometry kernel (external dep, pinned via pixi) |

---

*Doc scope: `main` branch only. Written 2026-08-23 against upstream commit `77069de933`. Update the "ahead by N" figure whenever you sync.*
