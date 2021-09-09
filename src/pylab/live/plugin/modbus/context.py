# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

from pylab.live.plugin.modbus import layout

# FIXME Place in seperate module to avoid duplication?
DEFAULT_SLAVE = 0


class ServerContextWithLayout:
    def __init__(
        self,
        context: pymodbus.datastore.context.ModbusServerContext,
        slave_layout: layout.SlaveLayout,
    ):
        self._context = context
        self._slave_layout = slave_layout

    # FIXME Race condition if client issues write concurrently?
    def get_input_registers(
        self, variables: Optional[Iterable[str]] = None, unit: Hashable = DEFAULT_SLAVE
    ) -> None:
        slave_layout = self._slave_layout[unit].input_registers
        store = self._context[unit].store["i"]
        registers = store.getValues(slave_layout.address, slave_layout.size)
        return slave_layout.decode_registers(registers, variables)

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
        payload = self._slave_layout[unit].holding_registers.build_payload(values)
        for payload in payloads:
            self._context[unit].store["h"].setValues(payload.address, payload.values)

    def set_coils(
        self, value: dict[str, _ValueType], unit: Hashable = DEFAULT_SLAVE
    ) -> None:
        payload = self._slave_layout[unit].coils.build_payload(values)
        for payload in payloads:
            self._context[unit].store["c"].setValues(payload.address, payload.values)

    def get_coils(
        self, variables: Optional[Iterable[str]] = None, unit: Hashable = DEFAULT_SLAVE
    ) -> None:
        slave_layout = self._slave_layout[unit].coils
        store = self._context[unit].store["c"]
        coils = store.getValues(slave_layout.address, slave_layout.size)
        return slave_layout.decode_coils(coils, variables)

    def get_discrete_inputs(self, variables: Optional[Iterable[str]] = None, unit: Hashable = DEFAULT_SLAVE) -> None:
        slave_layout = self._slave_layout[unit].discrete_inputs
        store = self._context[unit].store["d"]
        coils = store.getValues(slave_layout.address, slave_layout.size)
        return slave_layout.decode_coils(coils, variables)
