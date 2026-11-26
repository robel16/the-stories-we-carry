PYTHON ?= .venv314/Scripts/python.exe

.PHONY: film validate test phase1 phase2

film:
	$(PYTHON) -m pipeline.cli film

validate:
	$(PYTHON) -m pipeline.cli validate --check-assets

test:
	$(PYTHON) -m pytest

phase1:
	$(PYTHON) -m pipeline.cli phase1

phase2:
	$(PYTHON) -m pipeline.cli phase2
