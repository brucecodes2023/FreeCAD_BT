#!/bin/sh
# Repo root gitignores Makefile, so this script is the compile entry point.
set -e
cd "$(dirname "$0")"
pdflatex -interaction=nonstopmode -halt-on-error modern-cad-design.tex
pdflatex -interaction=nonstopmode -halt-on-error modern-cad-design.tex
rm -f modern-cad-design.aux modern-cad-design.log modern-cad-design.out
echo "Wrote modern-cad-design.pdf"
