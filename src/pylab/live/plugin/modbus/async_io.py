# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import pydantic

from pylab.live.plugin.modbus import layout

_DEFAULT_SLAVE = 0


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
        result = await self._protocol.read_input_registers(
            mapping.address, mapping.size, unit=unit
        )
        return mapping.decode_registers(result.registers, variables)

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
        result = await self._protocol.read_holding_registers(
            mapping.address, mapping.size, unit=unit
        )
        return mapping.decode_registers(result.registers, variables)

    async def write_register(
        self, field: str, value: _ValueType, unit: Hashable = _DEFAULT_SLAVE
    ) -> None:
        await self.write_registers({field: value}, unit)

    async def write_registers(
        self, values: dict[str, _ValueType], unit: Hashable = _DEFAULT_SLAVE
    ) -> None:
        payloads = self._mapping[unit].holding_registers.build_payload(values)
        for payload in payloads:
            await self._protocol.write_registers(
                payload.address, payload.values, skip_encode=True, unit=unit
            )

    @property
    def protocol(self) -> pymodbus.client.sync.ModbusClientMixin:
        return self._protocol
