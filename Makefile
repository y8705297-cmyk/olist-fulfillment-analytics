PYTHON ?= .venv/bin/python

.PHONY: all fetch build test reports
all: reports

fetch:
	$(PYTHON) -m src.fetch_data

build: fetch
	$(PYTHON) -m src.build_data

test: build
	$(PYTHON) -m unittest discover -s tests -v

reports: test
	$(PYTHON) -m src.validate_data
	$(PYTHON) -m src.feasibility

.PHONY: analysis
analysis: test
	MPLBACKEND=Agg MPLCONFIGDIR=data/processed/.matplotlib OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 $(PYTHON) -m src.run_analysis
