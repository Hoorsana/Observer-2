# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import importlib

import pymodbus.datastore

from pylab.core import utils
from pylab.live.plugin.modbus import layout
from pylab.live.plugin.modbus._const import DEFAULT_SLAVE


class ServerContext:
    def __init__(
        self,
        context: pymodbus.datastore.context.ModbusServerContext,
        slave_layout: Union[layout.SlaveLayout, dict[str, layout.SlaveLayout]],
        single: bool = True,
    ) -> None:
        """Server context with a layout for each slave.

        Args:
            context: The underlying server context
            slave_layout:
                A single slave layout or a ``dict`` which maps a unit id
                to the unit's layout
            single:
                Set to ``False`` if multiple slave layouts are specified
        """
        self._context = context
        if single:
            self._slave_layout = {DEFAULT_SLAVE: slave_layout}
        else:
            self._slave_layout = slave_layout
        # TODO Check that the keys of _context and _slave_layout are the
        # same!

    @classmethod
    def load(cls, context, slave_layout, single=True) -> ServerContext:
        if single:
            slave_layout = layout.SlaveContextLayout.load(**slave_layout)
        else:
            slave_layout = {
                k: layout.SlaveContextLayout.load(**v) for k, v in slave_layout
            }
        return cls(
            _load_pymodbus_server_context(context),
            slave_layout,
            single,
        )

    # FIXME Race condition if client issues write concurrently?
    def get_input_registers(
        self, variables: Optional[Iterable[str]] = None, unit=DEFAULT_SLAVE
    ) -> None:
        slave_layout = self._slave_layout[unit].input_registers
        store = self._context[unit].store["i"]
        registers = store.getValues(slave_layout.address, slave_layout.size)
        return slave_layout.decode_registers(registers, variables)

    def set_input_registers(
        self, values: dict[str, _ValueType], unit=DEFAULT_SLAVE
    ) -> None:
        payloads = self._slave_layout[unit].input_registers.build_payload(values)
        for payload in payloads:
            # For some reason, pymodbus stores each register as big-endian
            # integer in memory, so we need to convert.
            self._context[unit].store["i"].setValues(
                payload.address, [_bytes_to_16bit_int(x) for x in payload.values]
            )

    def get_holding_registers(
        self, variables: Optional[Iterable[str]] = None, unit=DEFAULT_SLAVE
    ) -> None:
        slave_layout = self._slave_layout[unit].holding_registers
        store = self._context[unit].store["h"]
        registers = store.getValues(slave_layout.address, slave_layout.size)
        return slave_layout.decode_registers(registers, variables)

    def set_holding_registers(
        self, values: dict[str, _ValueType], unit=DEFAULT_SLAVE
    ) -> None:
        payloads = self._slave_layout[unit].holding_registers.build_payload(values)
        # For some reason, pymodbus stores each register as big-endian
        # integer in memory, so we need to convert.
        for payload in payloads:
            self._context[unit].store["h"].setValues(
                payload.address, [_bytes_to_16bit_int(x) for x in payload.values]
            )

    def get_coils(
        self, variables: Optional[Iterable[str]] = None, unit=DEFAULT_SLAVE
    ) -> None:
        slave_layout = self._slave_layout[unit].coils
        store = self._context[unit].store["c"]
        coils = store.getValues(slave_layout.address, slave_layout.size)
        return slave_layout.decode_coils(coils, variables)

    def set_coils(self, values: dict[str, _ValueType], unit=DEFAULT_SLAVE) -> None:
        payloads = self._slave_layout[unit].coils.build_payload(values)
        for payload in payloads:
            self._context[unit].store["c"].setValues(payload.address, payload.values)

    def get_discrete_inputs(
        self, variables: Optional[Iterable[str]] = None, unit=DEFAULT_SLAVE
    ) -> None:
        slave_layout = self._slave_layout[unit].discrete_inputs
        store = self._context[unit].store["d"]
        coils = store.getValues(slave_layout.address, slave_layout.size)
        return slave_layout.decode_coils(coils, variables)

    def set_discrete_inputs(
        self, values: dict[str, _ValueType], unit=DEFAULT_SLAVE
    ) -> None:
        payloads = self._slave_layout[unit].discrete_inputs.build_payload(values)
        for payload in payloads:
            self._context[unit].store["d"].setValues(payload.address, payload.values)


def _bytes_to_16bit_int(b: bytes) -> int:
    """Convert two bytes to integer.

    Args:
        b: Sequence of bytes of length at least 2

    Wordorder and byteorder are big-endian.
    """
    assert len(b) > 1
    return 256 * b[0] + b[1]


def _load_pymodbus_server_context(data: dict):
    single = data.get("single", True)
    if single:
        data["slaves"] = _load_slave_context(data.pop("slaves"))
    else:
        data["slaves"] = {
            k: _load_slave_context(v) for k, v in data.pop("slaves").items()
        }
    factory = utils.getattr_from_module(data.pop("factory"))
    return factory(**data)


def _load_slave_context(data: dict):
    kwargs = {}
    for key in _KEYS:
        d = data[key]
        factory = utils.getattr_from_module(d.pop("factory"))
        # FIXME There's a problem here: Users can't specify large blocks of
        # data in yaml. Instead, we use the ``value`` field for specifying a
        # default value which is used to fill a list of size ``length``.
        # Explicit values can be specified using ``values`` (this is only
        # really useful for sparse memory. Maybe use `0..100:1` syntax
        # to specify lists?
        if "values" not in d:  # No explicit values, use ``value`` and ``length``!
            d["values"] = d.pop("length") * [d.pop("value")]
        data[key] = factory(**d)
    return pymodbus.datastore.ModbusSlaveContext(**data)


_KEYS = {"hr", "ir", "co", "di"}
# _KEYS = {"holding_registers", "input_registers", "coils", "discrete_inputs"}
