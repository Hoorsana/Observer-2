# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio

import pymodbus.payload
import pymodbus.datastore
import pymodbus.server.async_io
import pymodbus.client.asynchronous.tcp
import pymodbus.client.asynchronous.schedulers
import pytest
import threading

from pylab.live.plugin.modbus import layout
from pylab.live.plugin.modbus import async_io


@pytest.fixture(scope="session")
def event_loop(request):
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def server():
    context = pymodbus.datastore.ModbusServerContext(
        slaves={
            0: pymodbus.datastore.ModbusSlaveContext(),
            1: pymodbus.datastore.ModbusSlaveContext(),
        },
        single=False,
    )
    server = await pymodbus.server.async_io.StartTcpServer(
        context, address=("localhost", 5020)
    )
    task = asyncio.create_task(server.serve_forever())
    await asyncio.sleep(0.01)  # Make sure that the server is up when the fixture yields
    yield
    task.cancel()


class TestProtocol:
    @pytest.fixture
    def protocol(self, event_loop):
        _, client = pymodbus.client.asynchronous.tcp.AsyncModbusTCPClient(
            pymodbus.client.asynchronous.schedulers.ASYNC_IO,
            port=5020,
            loop=event_loop,
        )
        return async_io.Protocol(
            client.protocol,
            {
                0: layout.RegisterMapping(
                    [
                        layout.Str("str", length=5, address=2),
                        layout.Number("i", "i32"),
                        layout.Struct(
                            "struct",
                            [
                                layout.Field("CHANGED", "u1"),
                                layout.Field("ELEMENT_TYPE", "u7"),
                                layout.Field("ELEMENT_ID", "u5"),
                            ],
                            # address=19
                        ),
                        layout.Number("f", "f16"),
                    ]
                ),
                1: layout.RegisterMapping([layout.Str("str", length=5, address=2)]),
            },
            single=False,
        )

    @pytest.mark.asyncio
    async def test_write_registers_read_holding_registers(self, server, protocol):
        await protocol.write_registers(
            {
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
        assert await protocol.read_holding_register("f") == pytest.approx(3.4, abs=0.001)
        assert await protocol.read_holding_registers({"i", "str"}) == {
            "i": 12,
            "str": "world",
        }

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
        builder = layout._PayloadBuilder(byteorder=byteorder, wordorder=wordorder)
        var = layout.Number("", type)
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
        builder = layout._PayloadBuilder(byteorder, wordorder)
        for type_, value in payload:
            var = layout.Number("", type_)
            var.encode(builder, value)
        assert builder.build() == expected

    def test_encode_string(self):
        builder = layout._PayloadBuilder("<", ">")
        var = layout.Str("", 7)
        var.encode(builder, "Hullo")
        assert builder.build() == [b"Hu", b"ll", b"o ", b"  "]


@pytest.mark.parametrize(
    "fields, values, byteorder, wordorder",
    [
        (
            [
                layout.Field("CHANGED", "u1"),
                layout.Field("ELEMENT_TYPE", "u7"),
                layout.Field("ELEMENT_ID", "u8"),
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
                layout.Field("CHANGED", "u1"),
                layout.Field("ELEMENT_TYPE", "u7"),
                layout.Field("ELEMENT_ID", "u5"),
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
    s = layout.Struct("", fields)
    builder = layout._PayloadBuilder(byteorder, wordorder)
    s.encode(builder, values)
    payload = b"".join(builder.build())
    decoder = layout._PayloadDecoder(payload, byteorder, wordorder)
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
        builder = layout._PayloadDecoder(payload, byteorder, wordorder)
        var = layout.Number("", type)
        assert var.decode(builder) == expected
