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
                holding_registers=registers.RegisterMapping(
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
                input_registers=registers.RegisterMapping(
                    [
                        registers.Number("a", "u16"),
                        registers.Number("b", "u16"),
                        registers.Number("c", "u16"),
                    ],
                    byteorder=">",
                ),
            ),
            1: layout.SlaveContextLayout(
                holding_registers=registers.RegisterMapping(
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


class TestPayloadBuilder:
    @pytest.mark.parametrize(
        "type, value, expected, byteorder, wordorder",
        [
            ("i16", 777, [b"\t\x03"], "<", ">"),
            ("i16", 777, [b"\x03\t"], ">", ">"),
            ("i32", 67108864, [b"\x00\x04", b"\x00\x00"], "<", ">"),
            ("i32", 67108864, [b"\x00\x00", b"\x00\x04"], "<", "<"),
            ("f64", 3.141, [b"\t@", b"\xc4 ", b"\xa5\x9b", b"T\xe3"], "<", ">"),
            ("f64", 3.141, [b"\xe3T", b"\x9b\xa5", b" \xc4", b"@\t"], ">", "<"),
        ],
    )
    def test_encode_number_single(self, type, value, expected, byteorder, wordorder):
        builder = registers._PayloadBuilder(byteorder=byteorder, wordorder=wordorder)
        var = registers.Number("", type)
        var.encode(builder, value)
        assert builder.build() == expected

    @pytest.mark.parametrize(
        "payload, expected, byteorder, wordorder",
        [
            (
                [("i16", 777), ("i32", 67108864), ("f64", 3.141)],
                [
                    b"\t\x03",
                    b"\x00\x04",
                    b"\x00\x00",
                    b"\t@",
                    b"\xc4 ",
                    b"\xa5\x9b",
                    b"T\xe3",
                ],
                "<",
                ">",
            ),
        ],
    )
    def test_encode_number_multiple(self, payload, expected, byteorder, wordorder):
        builder = registers._PayloadBuilder(byteorder, wordorder)
        for type_, value in payload:
            var = registers.Number("", type_)
            var.encode(builder, value)
        assert builder.build() == expected

    def test_encode_string(self):
        builder = registers._PayloadBuilder("<", ">")
        var = registers.Str("", 7)
        var.encode(builder, "Hullo")
        assert builder.build() == [b"Hu", b"ll", b"o ", b"  "]


@pytest.mark.parametrize(
    "fields, values, byteorder, wordorder",
    [
        (
            [
                registers.Field("CHANGED", "u1"),
                registers.Field("ELEMENT_TYPE", "u7"),
                registers.Field("ELEMENT_ID", "u8"),
            ],
            {
                "CHANGED": 1,
                "ELEMENT_TYPE": 33,
                "ELEMENT_ID": 7,
            },
            "<",
            ">",
        ),
        pytest.param(
            [
                registers.Field("CHANGED", "u1"),
                registers.Field("ELEMENT_TYPE", "u7"),
                registers.Field("ELEMENT_ID", "u5"),
            ],
            {
                "CHANGED": 1,
                "ELEMENT_TYPE": 33,
                "ELEMENT_ID": 7,
            },
            "<",
            ">",
            id="With padding",
        ),
    ],
)
def test_encode_decode_struct(fields, values, byteorder, wordorder):
    s = registers.Struct("", fields)
    builder = registers._PayloadBuilder(byteorder, wordorder)
    s.encode(builder, values)
    payload = b"".join(builder.build())
    decoder = registers._PayloadDecoder(payload, byteorder, wordorder)
    assert s.decode(decoder) == values


def test_encode_decode_mixed():
    byteorder = ">"
    wordorder = "<"


class TestPayloadDecoder:
    @pytest.mark.parametrize(
        "type, expected, payload, byteorder, wordorder",
        [
            ("i16", 777, b"\t\x03", "<", ">"),
            ("i16", 777, b"\x03\t", ">", ">"),
            ("i32", 67108864, b"\x00\x04\x00\x00", "<", ">"),
            ("i32", 67108864, b"\x00\x00\x00\x04", "<", "<"),
            ("f64", 3.141, b"\t@\xc4 \xa5\x9bT\xe3", "<", ">"),
            ("f64", 3.141, b"\xe3T\x9b\xa5 \xc4@\t", ">", "<"),
        ],
    )
    def test_decode_single(self, type, expected, payload, byteorder, wordorder):
        builder = registers._PayloadDecoder(payload, byteorder, wordorder)
        var = registers.Number("", type)
        assert var.decode(builder) == expected
