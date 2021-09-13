# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from pylab.live.plugin.modbus import layout
from pylab.live.plugin.modbus._const import DEFAULT_SLAVE


class ServerContextWithLayout:
    def __init__(
        self,
        context: pymodbus.datastore.context.ModbusServerContext,
        slave_layout: layout.SlaveLayout,
        single: bool = True,
    ):
        self._context = context
        if single:
            self._slave_layout = {DEFAULT_SLAVE: slave_layout}
        else:
            self._slave_layout = slave_layout

    # FIXME Race condition if client issues write concurrently?
    def get_input_registers(
        self, variables: Optional[Iterable[str]] = None, unit: Hashable = DEFAULT_SLAVE
    ) -> None:
        slave_layout = self._slave_layout[unit].input_registers
        store = self._context[unit].store["i"]
        registers = store.getValues(slave_layout.address, slave_layout.size)
        return slave_layout.decode_registers(registers, variables)

    def set_input_registers(
        self, values: dict[str, _ValueType], unit: Hashable = DEFAULT_SLAVE
    ) -> None:
        payloads = self._slave_layout[unit].input_registers.build_payload(values)
        for payload in payloads:
            # For some reason, pymodbus stores each register as big-endian
            # integer in memory, so we need to convert.
            self._context[unit].store["i"].setValues(
                payload.address, [_bytes_to_16bit_int(x) for x in payload.values]
            )

    def get_holding_registers(
        self, variables: Optional[Iterable[str]] = None, unit: Hashable = DEFAULT_SLAVE
    ) -> None:
        slave_layout = self._slave_layout[unit].holding_registers
        store = self._context[unit].store["h"]
        registers = store.getValues(slave_layout.address, slave_layout.size)
        return slave_layout.decode_registers(registers, variables)

    def set_holding_registers(
        self, values: dict[str, _ValueType], unit: Hashable = DEFAULT_SLAVE
    ) -> None:
        payloads = self._slave_layout[unit].holding_registers.build_payload(values)
        # For some reason, pymodbus stores each register as big-endian
        # integer in memory, so we need to convert.
        for payload in payloads:
            self._context[unit].store["h"].setValues(
                payload.address, [_bytes_to_16bit_int(x) for x in payload.values]
            )

    def get_coils(
        self, variables: Optional[Iterable[str]] = None, unit: Hashable = DEFAULT_SLAVE
    ) -> None:
        slave_layout = self._slave_layout[unit].coils
        store = self._context[unit].store["c"]
        coils = store.getValues(slave_layout.address, slave_layout.size)
        return slave_layout.decode_coils(coils, variables)

    def set_coils(
        self, values: dict[str, _ValueType], unit: Hashable = DEFAULT_SLAVE
    ) -> None:
        payloads = self._slave_layout[unit].coils.build_payload(values)
        for payload in payloads:
            self._context[unit].store["c"].setValues(payload.address, payload.values)

    def get_discrete_inputs(
        self, variables: Optional[Iterable[str]] = None, unit: Hashable = DEFAULT_SLAVE
    ) -> None:
        slave_layout = self._slave_layout[unit].discrete_inputs
        store = self._context[unit].store["d"]
        coils = store.getValues(slave_layout.address, slave_layout.size)
        return slave_layout.decode_coils(coils, variables)

    def set_discrete_inputs(
        self, values: dict[str, _ValueType], unit: Hashable = DEFAULT_SLAVE
    ) -> None:
        payloads = self._slave_layout[unit].discrete_inputs.build_payload(values)
        for payload in payloads:
            self._context[unit].store["d"].setValues(payload.address, payload.values)


def _bytes_to_16bit_int(b: bytes) -> int:
    """Convert two bytes integer.

    Args:
        b: Sequence of bytes of length at least 2

    Wordorder and byteorder are big-endian.
    """
    assert len(b) > 1
    return 256 * b[0] + b[1]
