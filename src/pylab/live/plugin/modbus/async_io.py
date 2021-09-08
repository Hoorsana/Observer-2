# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from pylab.live.plugin.modbus import layout

_DEFAULT_SLAVE = 0


class Protocol:
    def __init__(
        self,
        protocol: pymodbus.client.asynchronous.async_io.ModbusClientProtocol,
        mapping: layout.RegisterMapping,
        single: bool = True,
    ):
        self._protocol = protocol
        if single:
            self._mapping = {_DEFAULT_SLAVE: mapping}
        else:
            self._mapping = mapping

    async def read_holding_register(
        self, var: str, unit: Hashable = _DEFAULT_SLAVE
    ) -> _ValueType:
        mapping = self._mapping[unit]
        address, size = mapping.get_field_dimensions(var)  # TODO
        result = await self._protocol.read_holding_registers(address, size, unit=unit)
        d = mapping.decode_registers(result.registers, variables_to_decode={var})
        return d[var]

    async def read_holding_registers(
        self, variables: Optional[Iterable[str]] = None, unit: Hashable = _DEFAULT_SLAVE
    ) -> dict[str, _ValueType]:
        mapping = self._mapping[unit]
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
        payloads = self._mapping[unit].build_payload(values)
        for payload in payloads:
            await self._protocol.write_registers(
                payload.address, payload.values, skip_encode=True, unit=unit
            )

    @property
    def protocol(self) -> pymodbus.client.sync.ModbusClientMixin:
        return self._protocol
