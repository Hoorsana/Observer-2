# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio

import pytest

from pylab.live.plugin.modbus import layout
from pylab.live.plugin.modbus import registers
from pylab.live.plugin.modbus import async_io


@pytest.fixture
def protocol(client):
    return async_io.Protocol(
        client.protocol,
        {
            0: layout.SlaveContextLayout(
                holding_registers=registers.RegisterLayout(
                    [
                        registers.Str("str", length=5, address=2),
                        registers.Number("i", "i32"),
                        registers.Struct(
                            "struct",
                            [
                                registers.Field("CHANGED", "u1"),
                                registers.Field("ELEMENT_TYPE", "u7"),
                                registers.Field("ELEMENT_ID", "u5"),
                            ],
                            address=19
                        ),
                        registers.Number("f", "f16"),
                    ]
                ),
                input_registers=registers.RegisterLayout(
                    [
                        registers.Number("a", "u16"),
                        registers.Number("b", "u16"),
                        registers.Number("c", "u16"),
                    ],
                    byteorder=">",
                ),
            ),
            1: layout.SlaveContextLayout(
                holding_registers=registers.RegisterLayout(
                    [
                        registers.Number("a", "u16", address=0),
                        registers.Number("b", "u16"),
                        registers.Number("c", "u16"),
                        registers.Str("str", length=5, address=12),
                    ],
                    byteorder=">",
                )
            ),
        },
        single=False,
    )


class TestProtocol:
    @pytest.mark.asyncio
    async def test_write_registers_read_holding_registers(self, server, protocol):
        await protocol.write_registers({
                "str": "hello",
                "i": 12,
                "struct": {
                    "CHANGED": 1,
                    "ELEMENT_TYPE": 33,
                    "ELEMENT_ID": 7,
                },
                "f": 3.4,
            }
        )
        assert await protocol.read_holding_registers() == {
            "str": "hello",
            "i": 12,
            "struct": {
                "CHANGED": 1,
                "ELEMENT_TYPE": 33,
                "ELEMENT_ID": 7,
            },
            "f": pytest.approx(3.4, abs=0.001),
        }
        await protocol.write_register("str", "world")
        assert await protocol.read_holding_register("str") == "world"
        assert await protocol.read_holding_register("i") == 12
        assert await protocol.read_holding_register("struct") == {
            "CHANGED": 1,
            "ELEMENT_TYPE": 33,
            "ELEMENT_ID": 7,
        }
        assert await protocol.read_holding_register("f") == pytest.approx(
            3.4, abs=0.001
        )
        assert await protocol.read_holding_registers({"i", "str"}) == {
            "i": 12,
            "str": "world",
        }


    @pytest.mark.asyncio
    async def test_read_holding_registers(self, server, protocol):
        result = await protocol.read_holding_registers(unit=1)
        assert result["a"] == 0
        assert result["b"] == 1
        assert result["c"] == 2

    @pytest.mark.asyncio
    async def test_read_input_registers(self, server, protocol):
        result = await protocol.read_input_registers()
        assert result["a"] == 0
        assert result["b"] == 1
        assert result["c"] == 2

    @pytest.mark.asyncio
    async def test_multiple_slaves(self, server, protocol):
        await protocol.write_register("str", "world", unit=0)
        await protocol.write_register("str", "hello", unit=1)
        assert await protocol.read_holding_register("str", unit=0) == "world"
        assert await protocol.read_holding_register("str", unit=1) == "hello"
