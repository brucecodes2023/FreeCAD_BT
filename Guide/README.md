# A Rigorous Guide to FreeCAD — Modeling and the Finite Element Method

A LaTeX book aimed at engineers: a brisk tour of FreeCAD's core parametric
modeling, a self-contained and rigorous treatment of finite-element theory,
and a practical guide to driving FreeCAD's FEM Workbench (CalculiX / Elmer).

## Structure

```
Guide/
├── main.tex                # master file — \include's everything
├── preamble.tex            # packages, styling, math macros
├── references.bib          # bibliography
├── Makefile                # build shortcuts
├── frontmatter/
│   └── preface.tex
├── chapters/
│   ├── 01-introduction.tex        ┐
│   ├── 02-interface.tex           │ Part I  — FreeCAD foundations
│   ├── 03-sketcher.tex            │
│   ├── 04-part-partdesign.tex     ┘
│   ├── 05-continuum-mechanics.tex ┐
│   ├── 06-strong-weak-form.tex    │
│   ├── 07-discretization.tex      │ Part II — FEM theory
│   ├── 08-elements-assembly-solve.tex
│   ├── 09-extensions.tex          │
│   ├── 10-meshing-convergence.tex ┘
│   ├── 11-fem-workbench.tex       ┐
│   ├── 12-solvers.tex             │ Part III — FEM in FreeCAD
│   ├── 13-worked-example.tex      │
│   └── 14-postprocessing-verification.tex ┘
└── appendix/
    └── notation.tex
```

## Building

Requires a full TeX distribution (TeX Live / MacTeX) with `latexmk`.

```bash
make            # full build (latexmk, resolves refs + bibliography)
make watch      # continuous rebuild on save
make quick      # single fast pdflatex pass
make clean      # remove build artifacts (keep PDF)
```

The output is `main.pdf`.

## Conventions

- **Audience:** engineers; assumes mechanics + calculus.
- **Notation:** see `appendix/notation.tex`. Voigt order
  `[xx, yy, zz, yz, xz, xy]`, engineering shear strains.
- **FreeCAD version:** 1.x generation. Cross-check UI details against the
  live wiki, as the software evolves.

## Status

Work in progress on branch `claude/guides`. See the chapter files for
per-chapter completion notes.
