# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
# 
# SPDX-License-Identifier: CC0-1.0

.PHONY: default
default: freeze
	platformio run -e arduinodue

.PHONY: freeze
freeze:
	./freeze_device

.PHONY: clean
clean:
	platformio run --target clean
	git checkout platformio.ini

.PHONY: flash
flash: freeze
	platformio run -e arduinodue -t upload
