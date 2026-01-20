# Makefile for ChimeraX 3decision bundle

CHIMERAX_EXE = /Applications/ChimeraX-1.10.1.app/Contents/bin/ChimeraX

install:
	$(CHIMERAX_EXE) --nogui --cmd "devel install . ; exit"

test:
	$(CHIMERAX_EXE) --nogui --cmd "python 'import chimerax.threedecision; print("Bundle test successful")' ; exit"

wheel:
	$(CHIMERAX_EXE) --nogui --cmd "devel build . ; exit"

clean:
	rm -rf build dist *.egg-info

help:
	@echo "ChimeraX 3decision Bundle Makefile"
	@echo "Targets: install, test, wheel, clean, help"

.PHONY: install test wheel clean help
