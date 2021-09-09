# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import pydantic
from pymodbus.register_read_message import (
    ReadInputRegistersResponse,
    ReadHoldingRegistersResponse,
)
from pymodbus.register_write_message import WriteMultipleRegistersResponse

from pylab.live.plugin.modbus import layout

_DEFAULT_SLAVE = 0


class ModbusResponseError(Exception):
    def __init__(self, response: pymodbus.pdu.ExceptionResponse, message: str) -> None:
        self.response = response
        self._message = message

    def __str__(self) -> str:
        return str(self.response) + ": " + self._message


class Protocol:
    def __init__(
        self,
        protocol: pymodbus.client.asynchronous.async_io.ModbusClientProtocol,
        mapping: layout.SlaveContextLayout,
        single: bool = True,
    ):
        self._protocol = protocol
        if single:
            self._mapping = {_DEFAULT_SLAVE: mapping}
        else:
            self._mapping = mapping

    # TODO Fix code duplication!
    async def read_input_registers(
        self, variables: Optional[Iterable[str]] = None, unit: Hashable = _DEFAULT_SLAVE
    ) -> dict[str, _ValueType]:
        mapping = self._mapping[unit].input_registers
        response = await self._protocol.read_input_registers(
            mapping.address, mapping.size, unit=unit
        )
        # Error handling. FIXME According to pymodbus examples, checking
        # for the function_code is idiomatic, but maybe just checking
        # type(response) != ReadInputRegistersResponse is better?
        if response.function_code != ReadInputRegistersResponse.function_code:
            raise ModbusResponseError(response, "Failed to read from input registers")
            # TODO Add variables and unit to error artifacts?
        return mapping.decode_registers(response.registers, variables)

    async def read_input_register(
        self, var: str, unit: Hashable = _DEFAULT_SLAVE
    ) -> _ValueType:
        d = await self.read_input_registers(unit=unit)
        return d[var]

    async def read_holding_register(
        self, var: str, unit: Hashable = _DEFAULT_SLAVE
    ) -> _ValueType:
        d = await self.read_holding_registers(unit=unit)
        return d[var]

    async def read_holding_registers(
        self, variables: Optional[Iterable[str]] = None, unit: Hashable = _DEFAULT_SLAVE
    ) -> dict[str, _ValueType]:
        mapping = self._mapping[unit].holding_registers
        response = await self._protocol.read_holding_registers(
            mapping.address, mapping.size, unit=unit
        )
        if response.function_code != ReadHoldingRegistersResponse.function_code:
            raise ModbusResponseError(response, "Failed to read from holding registers")
        return mapping.decode_registers(response.registers, variables)

    async def write_register(
        self, field: str, value: _ValueType, unit: Hashable = _DEFAULT_SLAVE
    ) -> None:
        await self.write_registers({field: value}, unit)

    async def write_registers(
        self, values: dict[str, _ValueType], unit: Hashable = _DEFAULT_SLAVE
    ) -> None:
        payloads = self._mapping[unit].holding_registers.build_payload(values)
        for payload in payloads:
            response = await self._protocol.write_registers(
                payload.address, payload.values, skip_encode=True, unit=unit
            )
            if response.function_code != WriteMultipleRegistersResponse.function_code:
                raise ModbusResponseError(
                    response, "Failed to write to holding registers"
                )

    @property
    def protocol(self) -> pymodbus.client.sync.ModbusClientMixin:
        return self._protocol
