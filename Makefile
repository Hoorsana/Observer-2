# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
# 
# SPDX-License-Identifier: CC0-1.0

# virtualenv environment.
VENV?=.venv
ifeq ($(OS), Windows_NT)
	BIN?=$(VENV)\Scripts
else
	BIN?=$(VENV)/bin
endif
PYTHON?=$(BIN)/python
PIP?=$(BIN)/pip
PYTEST?=$(BIN)/pytest

ifeq ($(OS), Windows_NT)
define delete_dir
	if exist $(1) rmdir /Q /s $(1)
endef
else
define delete_dir
	rm -fr $(1)
endef
endif

ifeq ($(OS), Windows_NT)
define activate
	$(BIN)\activate
endef
else
define activate
	. $(BIN)/activate
endef
endif

.PHONY: default
default: venv
	$(call activate) && \
	pytest -vv tests/ && \
	deactivate

# We need to run pytest directly from the environment in order to test
# the command line interface (otherwise, we won't use the shell of the
# virtual environment).
.PHONY: cli
cli: venv
	$(call activate) && \
	pytest -vv tests/test_pylab_cli.py && \
	deactivate

.PHONY: tools
tools: venv
	$(PYTEST) -vv tests/tools

.PHONY: core
core: venv
	$(PYTEST) -vv tests/core

.PHONY: quick
quick: core cli tools

.PHONY: plugin-fake
plugin-fake: venv
	$(PYTEST) -vv tests/live/plugin/fake/test_fake.py

.PHONY: live
live: venv
	$(PYTEST) -vv tests/live/test_live.py

.PHONY: simulink
simulink: venv
	$(PYTEST) -vv tests/simulink

# Legacy target; deprecated
.PHONY: example
example: example-adder

# Beware! Removing the whitespace in `python freeze ;` will result in
# errors on windows!
.PHONY: example-adder
example-adder: venv
	$(call activate) && \
	cd resources/examples/adder && python freeze && \
	deactivate
	$(PYTEST) -vv -s example/test_example_adder.py

# Create virtual environment if it doesn't exist; setup MATLAB Python
# engine if available
.PHONY: venv
venv:
	pip install virtualenv
ifeq ($(OS), Windows_NT)
	if NOT exist $(VENV) virtualenv $(VENV)
else
	[ -d $(VENV) ] || virtualenv $(VENV)
endif
	$(PIP) install -r requirements.txt
ifdef PYLAB_MATLAB_PATH
	$(call activate) && \
	cd ${PYLAB_MATLAB_PATH}/extern/engines/python && \
	python setup.py install && \
	deactivate
endif
	$(PYTHON) setup.py install
	$(PYTHON) setup.py install_scripts

.PHONY: sphinx
sphinx:
	sphinx-apidoc --module-first --force --private --separate -o docs/build src
	cd docs && make html

.PHONY: clean
clean:
	python setup.py clean
	$(call delete_dir,build)
	$(call delete_dir,.venv)
	$(call delete_dir,docs/build)

.PHONY: install
install:
	python setup.py install
	python setup.py install_scripts
