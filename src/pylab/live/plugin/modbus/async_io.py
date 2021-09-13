# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import pydantic
from pymodbus.register_read_message import (
    ReadInputRegistersResponse,
    ReadHoldingRegistersResponse,
)
from pymodbus.bit_read_message import ReadCoilsResponse, ReadDiscreteInputsResponse
from pymodbus.bit_write_message import WriteMultipleCoilsResponse
from pymodbus.register_write_message import WriteMultipleRegistersResponse

from pylab.live.plugin.modbus._const import DEFAULT_SLAVE
from pylab.live.plugin.modbus import layout


class ModbusResponseError(Exception):
    def __init__(
        self, response: pymodbus.pdu.ExceptionResponse, msg: Optional[str] = None
    ) -> None:
        if msg is None:
            msg = str(response)
        super().__init__(msg)
        self.response = response


class Protocol:
    """``asyncio`` protocol object for writing/reading using specified memory layouts."""

    def __init__(
        self,
        protocol: pymodbus.client.asynchronous.async_io.ModbusClientProtocol,
        slave_layout: Union[
            layout.SlaveContextLayout, dict[str, layout.SlaveContextLayout]
        ],
        single: bool = True,
    ):
        """Args:
        protocol: The `pymodbus` protocol to wrap around
        slave_layout:
            A single slave context layout or a ``dict`` that maps unit
            ids to their slave layout
        single: Set to ``False`` if multiple slave layouts are used

        If ``slave_layout`` is a ``dict``, then ``single`` must be set
        to ``False`` to indicate that multiple slaves are used.
        """
        self._protocol = protocol
        if single:
            self._slave_layout = {DEFAULT_SLAVE: slave_layout}
        else:
            self._slave_layout = slave_layout

    # TODO Fix code duplication!
    async def read_input_registers(
        self, variables: Optional[Iterable[str]] = None, unit=DEFAULT_SLAVE
    ) -> dict[str, _ValueType]:
        """Read ``variables`` from input register of ``unit``.

        Args:
            variables: The variables to read (all by default)
            unit: The unit to read from

        Returns:
            A ``dict`` mapping the queried variable's names to their
            values

        Raises:
            ModbusResponseError: If reading the slave failed
            VariableNotFound:
                If one or more items of ``variables`` are not mapped
                by the input register layout of ``unit``

        Note that this method will always execute a complete readout of
        the slave's input register layout's range.
        """
        slave_layout = self._slave_layout[unit].input_registers
        response = await self._protocol.read_input_registers(
            slave_layout.address, slave_layout.size, unit=unit
        )
        # Error handling. FIXME According to pymodbus examples, checking
        # for the function_code is idiomatic, but maybe just checking
        # type(response) != ReadInputRegistersResponse is better?
        if response.function_code != ReadInputRegistersResponse.function_code:
            raise ModbusResponseError(response)
        return slave_layout.decode_registers(response.registers, variables)

    async def read_input_register(self, var: str, unit=DEFAULT_SLAVE) -> _ValueType:
        """Read ``var`` from input register of ``unit``.

        Args:
            var: The variable to read
            unit: The unit to read from

        Returns: The value of the variable

        Raises:
            ModbusResponseError: If reading the slave failed
            VariableNotFound:
                If ``var`` is not mapped by the input register layout
                of ``unit``

        Note that this method will always execute a complete readout of
        the slave's input register layout's range.
        """
        d = await self.read_input_registers(unit=unit)
        return d[var]

    async def read_holding_registers(
        self, variables: Optional[Iterable[str]] = None, unit=DEFAULT_SLAVE
    ) -> dict[str, _ValueType]:
        """Read ``variables`` from holding register of ``unit``.

        Args:
            variables: The variables to read (all by default)
            unit: The unit to read from

        Returns:
            A ``dict`` mapping the queried variable's names to their
            values

        Raises:
            ModbusResponseError: If reading the slave failed
            VariableNotFound:
                If one or more items of ``variables`` are not mapped by
                the holding register layout

        Note that this method will always execute a complete readout of
        the slave's holding register layout's range.
        """
        slave_layout = self._slave_layout[unit].holding_registers
        response = await self._protocol.read_holding_registers(
            slave_layout.address, slave_layout.size, unit=unit
        )
        if response.function_code != ReadHoldingRegistersResponse.function_code:
            raise ModbusResponseError(response)
        return slave_layout.decode_registers(response.registers, variables)

    async def read_holding_register(self, var: str, unit=DEFAULT_SLAVE) -> _ValueType:
        """Read ``var`` from holding register of ``unit``.

        Args:
            var: The variable to read
            unit: The unit to read from

        Returns: The value of the variable

        Raises:
            ModbusResponseError: If reading the slave failed
            VariableNotFound:
                If ``var`` is not mapped by the holding register
                layout of ``unit``

        Note that this method will always execute a complete readout of
        the slave's holding register layout's range.
        """
        d = await self.read_holding_registers(unit=unit)
        return d[var]

    async def write_registers(
        self, values: dict[str, _ValueType], unit=DEFAULT_SLAVE
    ) -> None:
        """Write ``values`` to holding register memory of ``unit``.

        Args:
            values:
                A ``dict`` mapping variable names to the values to write
            unit: The unit to write to

        Raises:
            ModbusResponseError: If reading the slave failed
            VariableNotFound:
                If one or more keys of ``values`` are not mapped by
                the holding register layout of ``unit``

        This method will group values which occur back-to-back in memory
        into payload chunks in order to minimize the amount of write
        requests to the server.
        """
        payloads = self._slave_layout[unit].holding_registers.build_payload(values)
        for payload in payloads:
            response = await self._protocol.write_registers(
                payload.address, payload.values, skip_encode=True, unit=unit
            )
            if response.function_code != WriteMultipleRegistersResponse.function_code:
                raise ModbusResponseError(response)

    async def write_register(
        self, var: str, value: _ValueType, unit=DEFAULT_SLAVE
    ) -> None:
        """Set ``var`` in the holding register to ``value``.

        Args:
            var: The variable to modify
            value: The new value of ``var``
            unit: The unit to write to

        Raises:
            ModbusResponseError: If reading the slave failed
            VariableNotFound:
                If ``var`` is not mapped by the holding register layout
                of ``unit``
        """
        await self.write_registers({var: value}, unit)

    async def write_coils(
        self, values: dict[str, _ValueType], unit=DEFAULT_SLAVE
    ) -> None:
        """Write ``values`` to coil memory of ``unit``.

        Args:
            values:
                A ``dict`` mapping variable names to the values to write
            unit: The unit to write to

        Raises:
            ModbusResponseError: If reading the slave failed
            VariableNotFound:
                If one or more keys of ``values`` are not mapped by
                the coil layout of ``unit``

        This method will group values which occur back-to-back in memory
        into payload chunks in order to minimize the amount of write
        requests to the server.
        """
        payloads = self._slave_layout[unit].coils.build_payload(values)
        for payload in payloads:
            response = await self._protocol.write_coils(
                payload.address, payload.values, unit=unit
            )
            if response.function_code != WriteMultipleCoilsResponse.function_code:
                raise ModbusResponseError(response)

    async def write_coil(self, var: str, value: _ValueType, unit=DEFAULT_SLAVE) -> None:
        """Set ``var`` in coil memory to ``value``

        Args:
            var: The variable to modify
            value: The new value of ``var``
            unit: The unit to write to

        Raises:
            ModbusResponseError: If reading the slave failed
            VariableNotFound:
                If ``var`` is not mapped by the coil layout of ``unit``
        """
        await self.write_coils({var: value}, unit)

    async def read_coils(
        self, variables: Optional[Iterable[str]] = None, unit=DEFAULT_SLAVE
    ) -> dict[str, _ValueTypes]:
        """Read ``variables`` from coils of ``unit``.

        Args:
            variables: The variables to read (all by default)
            unit: The unit to read from

        Returns:
            A ``dict`` mapping the queried variable's names to their
            values

        Raises:
            ModbusResponseError: If reading the slave failed
            VariableNotFound:
                If one or more items of ``variables`` are not mapped by
                the coil layout

        Note that this method will always execute a complete readout of
        the slave's coil layout's range.
        """
        coil_layout = self._slave_layout[unit].coils
        response = await self._protocol.read_coils(
            coil_layout.address, coil_layout.size, unit=unit
        )
        if response.function_code != ReadCoilsResponse.function_code:
            raise ModbusResponseError(response)
        return coil_layout.decode_coils(response.bits, variables)

    async def read_coil(self, var: str, unit=DEFAULT_SLAVE) -> list[bool]:
        """Read ``var`` from coil memory of ``unit``.

        Args:
            var: The variable to read
            unit: The unit to read from

        Returns: The value of the variable

        Raises:
            ModbusResponseError: If reading the slave failed
            VariableNotFound:
                If ``var`` is not mapped by the coil layout of ``unit``

        Note that this method will always execute a complete readout of
        the slave's coil layout's range.
        """
        d = await self.read_coils(unit=unit)
        return d[var]

    async def read_discrete_inputs(
        self, variables: Optional[Iterable[str]] = None, unit=DEFAULT_SLAVE
    ) -> dict[str, list[bool]]:
        """Read ``variables`` from discrete inputs of ``unit``.

        Args:
            variables: The variables to read (all by default)
            unit: The unit to read from

        Returns:
            A ``dict`` mapping the queried variable's names to their
            values

        Raises:
            ModbusResponseError: If reading the slave failed
            VariableNotFound:
                If one or more items of ``variables`` are not mapped by
                the discrete input layout

        Note that this method will always execute a complete readout of
        the slave's discrete input layout's range.
        """
        coil_layout = self._slave_layout[unit].discrete_inputs
        response = await self._protocol.read_discrete_inputs(
            coil_layout.address, coil_layout.size, unit=unit
        )
        if response.function_code != ReadDiscreteInputsResponse.function_code:
            raise ModbusResponseError(response)
        return coil_layout.decode_coils(response.bits, variables)

    async def read_discrete_input(
        self, variable: str, unit=DEFAULT_SLAVE
    ) -> list[bool]:
        """Read ``var`` from discrete input memory of ``unit``.

        Args:
            var: The variable to read
            unit: The unit to read from

        Returns: The value of the variable

        Raises:
            ModbusResponseError: If reading the slave failed
            VariableNotFound:
                If ``var`` is not mapped by the discrete input register
                layout of ``unit``

        Note that this method will always execute a complete readout of
        the slave's discrete input layout's range.
        """
        d = await self.read_discrete_inputs(unit=unit)
        return d[variable]

    @property
    def protocol(self) -> pymodbus.client.asynchronous.async_io.ModbusClientProtocol:
        return self._protocol
