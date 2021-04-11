# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
# 
# SPDX-License-Identifier: CC0-1.0

# virtualenv environment.
VENV?=.venv
PYTHON?=$(VENV)/bin/python
PIP?=$(VENV)/bin/pip
PYTEST?=$(VENV)/bin/pytest

.PHONY: default
default: venv
	. $(VENV)/bin/activate; \
	pytest -vv tests/; \
	deactivate

.PHONY: cli
cli: venv
	. $(VENV)/bin/activate; \
	pytest -vv tests/test_pylab_cli.py; \
	deactivate

.PHONY: core
core: venv
	$(PYTEST) -vv tests/core

.PHONY: live
live: venv
	$(PYTEST) -vv tests/live

.PHONY: plugin-fake
plugin-fake: venv
	$(PYTEST) -vv tests/live/plugin/fake/test_fake.py

.PHONY: quick
quick: venv core cli

	# TODO Use python setup.py clean instead of build dir!

.PHONY: example
example: venv
	$(PYTEST) -vv -s example

.PHONY: venv
venv:
	pip install virtualenv
	# If virtualenv doesn't exist, create it, then fetch dependencies.
	[ -d $(VENV) ] || virtualenv $(VENV)
	$(PIP) install -r requirements.txt
	. $(VENV)/bin/activate; \
	if ! [[ -z $(PYLAB_MATLAB_PATH) ]]; then \
		cd ${PYLAB_MATLAB_PATH}/extern/engines/python; \
		python setup.py install; \
	fi; \
	pip install git+https://github.com/maltekliemann/controllino; \
	deactivate
	$(PYTHON) setup.py install
	$(PYTHON) setup.py install_scripts

.PHONY: sphinx
sphinx:
	sphinx-apidoc --module-first --force --private --separate -o docs/build src
	cd docs && make html

.PHONY: clean
clean:
	rm -fr build
	rm -fr .venv
	rm -fr docs/build

.PHONY: install
install:
	python setup.py install
	python setup.py install_scripts
