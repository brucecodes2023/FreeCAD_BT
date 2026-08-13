# Design documents

Canonical product plan for this fork (FreeCAD\_BT): close the gap from FreeCAD toward SolidWorks / Fusion 360, starting on Apple Silicon.

| File | What it is |
|---|---|
| `modern-cad-design.tex` | Living design plan and work tracker. Compile this. |
| `modern-cad-design.pdf` | Generated PDF (committed when rebuilt). |

The earlier Cloud Agent scoping file (`docs/macos-native-ui-scope.tex` on branch `cursor/setup-cloud-agent-env-d2a0`) lived under `docs/` and is not on this branch. This directory replaces it: same visual language, expanded to the whole plan, with Done / Partial / Later status on every item.

## Compile

```bash
cd Documents
./build.sh
```

That runs `pdflatex` twice and removes auxiliary files. The PDF is the review artifact.

## How we keep this current

When a workstream item lands, changes, or is deferred:

1. Update the status tag in the tracker table (Done / Partial / Later).
2. Note the landing files under that item.
3. Append a dated line to the **Work log**.

IDs (A1–A6, B0–B4, C1–C5, D1–D3, E1–E4, F1–F4, G1–G4) are stable. Do not renumber; add a new ID if the work is new.
