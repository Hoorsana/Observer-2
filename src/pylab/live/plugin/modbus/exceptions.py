# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations


class ModbusBackendException(Exception):
    pass


class NoVariablesError(ModbusBackendException):
    pass


class NegativeAddressError(ModbusBackendException):
    def __init__(self, name: str, address: int, msg: Optional[str] = None) -> None:
        if msg is None:
            msg = f"Variable '{name}' has negative address {address}. Memory address must always be positive."
        super().__init__(msg)
        self.name = name
        self.address = address


class InvalidAddressLayoutError(ModbusBackendException):
    def __init__(
        self, previous: Variable, current: Variable, msg: Optional[str] = None
    ) -> None:
        if msg is None:
            msg = f"Invalid address for variable '{current.name}' specified: {current.address}. Previous variable store ends at {previous.end}. Variable stores must not overlap."
        super().__init__(msg)
        self.previous = previous
        self.current = current


class VariableNotFoundError(ModbusBackendException):
    def __init__(self, variables: Iterable[str], msg: Optional[str] = None) -> None:
        if msg is None:
            msg = f"Variables not found: {variables}"
        super().__init__(msg)
        self.variables = variables


class DuplicateVariableError(ModbusBackendException):
    def __init__(self, duplicate: str, msg: Optional[str] = None) -> None:
        if msg is None:
            msg = f"Duplicate variable name: {duplicate}"
        super().__init__(msg)
        self.duplicate = duplicate


class EncodingError(ModbusBackendException):
    pass
