# Fork changelog

Files on `main` that are **not** in upstream `FreeCAD/FreeCAD`. Update this
on every fork addition so `git merge upstream/main` has a conflict checklist.

| Path | Why |
|---|---|
| `OVERVIEW.md` | Fork maintenance map |
| `run-freecad.sh` | Dev launcher (cocoa plugin flag, pixi, `-M BtStudio`) |
| `run-freecad-mcp.sh` | GUI + FcBridge MCP + BtStudio |
| `src/Mod/FcBridge/` | Loopback JSON-RPC for AI verification (OVERVIEW §9) |
| `src/Mod/BtStudio/` | Notes overlay: UI, FEM wizard, theory, OpenFOAM architecture |
| `CHANGELOG-FORK.md` | This file |

## Patches to upstream files (quit SIGSEGV)

`TaskDlgAttacher::~TaskDlgAttacher` called `getMainWindow()->hideHints()` after
`MainWindow` was already destroyed (Tasks dock still held the Attachment
dialog). Null-check every destructor/shutdown `hideHints()` caller, and clear
`MainWindow::instance` at the start of `~MainWindow`.

| Path | Why |
|---|---|
| `src/Gui/MainWindow.cpp` | Null singleton first; guard `showHints`/`hideHints` |
| `src/Mod/Part/Gui/TaskAttacher.cpp` | Null-check in `~TaskDlgAttacher` |
| `src/Mod/PartDesign/Gui/TaskPrimitiveParameters.cpp` | Null-check in `~TaskBoxPrimitives` |
| `src/Mod/PartDesign/Gui/TaskFeatureParameters.cpp` | Null-check in `hideDraggerHints` |
| `src/Gui/ToolHandler.cpp` | Null-check in `deactivate` |
| `src/Gui/TaskView/TaskImage.cpp` | Null-check in `InteractiveScale` |
| `src/Mod/Measure/Gui/TaskMeasure.cpp` | Null-check in `closeDialog` |
