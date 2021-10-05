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
	make quick
	make simulink
	make live-flash
	make example-adder-flash
	make example-limit-flash

.PHONY: private
private: install
	$(PYTEST) -vv tests/_private

.PHONY: shared
shared: install
	$(PYTEST) -vv tests/shared

.PHONY: rogueplugin
rogueplugin: install
	$(PYTEST) -vv tests/_private/test_rogueplugin.py

.PHONY: saleae-flash
saleae-flash: install
	cd arduino/pulsar && make flash
	make saleae

.PHONY: saleae-quick
saleae-quick: install
	$(PYTEST) -vv tests/live/plugin/saleae/test_parser.py

.PHONY: saleae
saleae: install
	$(PYTEST) -vv tests/live/plugin/saleae/test_logic.py
	$(PYTEST) -vv tests/live/plugin/saleae/test_parser.py

.PHONY: can
can: install
	$(PYTEST) -vv tests/live/plugin/can/

# We need to run pytest directly from the environment in order to test
# the command line interface (otherwise, we won't use the shell of the
# virtual environment).
.PHONY: cli
cli: install
	$(call activate) && \
	pytest -vv tests/test_pylab_cli.py && \
	deactivate

.PHONY: tools
tools: install
	$(PYTEST) -vv tests/tools

.PHONY: core
core: install
	$(PYTEST) -vv tests/core

.PHONY: quick
quick: core cli tools shared live modbus private

.PHONY: plugin-fake
plugin-fake: install
	$(PYTEST) -vv tests/live/plugin/fake/test_fake.py

.PHONY: live
live: install
	$(PYTEST) -vv tests/live/test_live.py

.PHONY: live-flash
live-flash: install
	cd arduino/adder && make flash
	make live

.PHONY: simulink
simulink: install
	$(PYTEST) -vv tests/simulink

.PHONY: modbus
modbus: install
	$(PYTEST) -vv tests/live/plugin/modbus

# Legacy target; deprecated
.PHONY: example
example: example-adder

.PHONY: example-adder
example-adder: install
	$(call activate) && \
	cd resources/examples/adder && python freeze && \
	deactivate
	$(PYTEST) -vv -s example/test_example_adder.py

.PHONY: ball
ball: install
	$(PYTEST) -vv example/test_example_ball_and_beam.py

.PHONY: example-adder-flash
example-adder-flash: install
	cd arduino/adder && make flash
	make example-adder

.PHONY: example-limit
example-limit: install
	$(call activate) && \
	cd resources/examples/limit_monitoring && python freeze && \
	deactivate
	$(PYTEST) -vv -s example/test_example_limit_monitoring.py

.PHONY: example-limit-flash
example-limit-flash: install
	cd arduino/limit_monitoring && make flash
	make example-limit

# Create virtual environment if it doesn't exist; setup MATLAB Python
# engine if available
.PHONY: venv
venv:
	python freeze
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
	make install

.PHONY: sphinx
sphinx:
	sphinx-apidoc --module-first --force --private --separate -o docs/build src
	cd docs && make html

.PHONY: clean
clean:
	python setup.py clean
	$(call delete_dir,build)
	$(call delete_dir,dist)
	$(call delete_dir,.venv)
	$(call delete_dir,docs/build)

.PHONY: install
install:
	$(PYTHON) setup.py install
	$(PYTHON) setup.py install_scripts
