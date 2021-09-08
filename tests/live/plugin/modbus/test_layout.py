# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

import pymodbus.payload
import pymodbus.client.sync
import pymodbus.datastore
import pymodbus.server.sync
import threading

from pylab.live.plugin.modbus import layout
from pylab.live.plugin.modbus import async_io


@pytest.fixture(scope="session")
def server():
    context = pymodbus.datastore.ModbusServerContext(
        slaves={
            0: pymodbus.datastore.ModbusSlaveContext(),
            1: pymodbus.datastore.ModbusSlaveContext(),
        },
        single=False,
    )
    server = pymodbus.server.sync.ModbusTcpServer(context, address=("localhost", 5020))
    t = threading.Thread(target=lambda s: s.serve_forever(), args=(server,))
    t.start()
    yield
    # FIXME It's not clear which of these is correct...
    server.shutdown()
    server.server_close()
    t.join()


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
    ]
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


class TestModbusRegisterMapping:
    pass


class TestModbusClient:
    @pytest.fixture
    def client(self):
        return async_io.Client(
            pymodbus.client.sync.ModbusTcpClient(host="localhost", port=5020),
            {
                0: layout.RegisterMapping(
                    [
                        layout.Str("str", length=5, address=2),
                        layout.Number("i", "i32"),
                        # layout.Struct(
                        #     "struct",
                        #     [
                        #         layout.Field("CHANGED", "u1"),
                        #         layout.Field("ELEMENT_TYPE", "u7"),
                        #         layout.Field("ELEMENT_ID", "u5"),
                        #     ],
                        #     address=19
                        # ),
                        layout.Number("f", "f16"),
                    ]
                ),
                1: layout.RegisterMapping(
                    [layout.Str("str", length=5, address=2)]
                ),
            },
            single=False,
        )

    def test_write_register_read_holding_registers(self, server, client):
        client.write_registers(
            {
                "str": "hello",
                "i": 12,
                # "struct": {
                #     "CHANGED": 1,
                #     "ELEMENT_TYPE": 33,
                #     "ELEMENT_ID": 7,
                # },
                "f": 3.4,
            }
        )
        assert client.read_holding_registers() == {
            "str": b"hello",
            "i": 12,
            # "struct": {
            #     "CHANGED": 1,
            #     "ELEMENT_TYPE": 33,
            #     "ELEMENT_ID": 7,
            # },
            "f": pytest.approx(3.4, abs=0.001),
        }

    #     assert client.read_holding_register("b") == bits
    #     client.write_register("s", "world")
    #     assert client.read_holding_register("s") == b"world"
    #     client.write_registers(
    #         {
    #             "x": 34,
    #             "s": "hello",
    #         }
    #     )
    #     assert client.read_holding_registers({"x", "s"}) == {
    #         "x": 34,
    #         "s": b"hello",
    #     }

    # def test_multiple_slaves(self, server, client):
    #     client.write_register("s", "world", unit=0)
    #     client.write_register("s", "hello", unit=1)
    #     assert client.read_holding_register("s", unit=0) == b"world"
    #     assert client.read_holding_register("s", unit=1) == b"hello"

    # def test_write_holding_register_read_holding_register_with_tuples(
    #     self, server, client_with_tuples
    # ):
    #     bits = [True, False, True, False, False, False, True, True]
    #     client_with_tuples.write_register("z", 5)
    #     client_with_tuples.write_register("y", (1, "b", bits, 4))
    #     assert client_with_tuples.read_holding_register("y") == (1, b"b", bits, 4)
    #     assert client_with_tuples.read_holding_register("z") == 5

    # def test_layout(self):
    #     layout = layout.MemoryLayout(
    #         [
    #             layout.variable(
    #                 "STATE",
    #                 "struct",
    #                 [
    #                     layout.Field("CHANGED", "int", 1),  # TODO bool?
    #                     layout.Field("ELEMENT_TYPE", "int", 7),  # TODO
    #                     layout.Field("ELEMENT_ID", "int", 8),
    #                     layout.Field("VALUE", "float", 16),
    #                     layout.Field("MESSAGE", "str", 24),
    #                 ]
    #             ),
    #         ]
