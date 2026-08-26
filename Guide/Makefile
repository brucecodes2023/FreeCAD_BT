# Makefile for the FreeCAD guide
# Usage:
#   make          -> build main.pdf via latexmk (recommended)
#   make quick    -> single pdflatex pass (fast, no bib/refs resolution)
#   make clean    -> remove build artifacts (keep the PDF)
#   make cleanall -> remove build artifacts and the PDF

MAIN    = main
LATEXMK = latexmk
LMKOPTS = -pdf -interaction=nonstopmode -halt-on-error -file-line-error

.PHONY: all quick clean cleanall watch

all: $(MAIN).pdf

$(MAIN).pdf: $(MAIN).tex preamble.tex references.bib
	$(LATEXMK) $(LMKOPTS) $(MAIN).tex

quick:
	pdflatex -interaction=nonstopmode -halt-on-error $(MAIN).tex

# Continuous rebuild on save (requires latexmk)
watch:
	$(LATEXMK) $(LMKOPTS) -pvc $(MAIN).tex

clean:
	$(LATEXMK) -c $(MAIN).tex
	rm -f *.bbl *.run.xml chapters/*.aux frontmatter/*.aux appendix/*.aux

cleanall: clean
	rm -f $(MAIN).pdf
