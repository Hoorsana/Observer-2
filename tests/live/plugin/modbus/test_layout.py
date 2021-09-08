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


class TestNumber:
    @pytest.mark.parametrize(
        "type, value, expected, byteorder, wordorder",
        [
            ("i16", 777, [b"\t\x03"], "<", ">"),
            ("i16", 777, [b"\x03\t"], ">", ">"),
            ("i32", 67108864, [b"\x00\x04", b"\x00\x00"], "<", ">"),
            ("i32", 67108864, [b"\x00\x00", b"\x00\x04"], "<", "<"),
            ("f64", 3.141, [b'\t@', b'\xc4 ', b'\xa5\x9b', b'T\xe3'], "<", ">"),
            ("f64", 3.141, [b'\xe3T', b'\x9b\xa5', b' \xc4', b'@\t'], ">", "<"),
        ],
    )
    def test_encode_single(self, type, value, expected, byteorder, wordorder):
        builder = layout._PayloadBuilder(byteorder=byteorder, wordorder=wordorder)
        var = layout.Number("", type)
        var.encode(builder, value)
        assert builder.build() == expected


class TestModbusRegisterMapping:
    pass


class TestModbusClient:
    pass
    # @pytest.fixture
    # def client(self):
    #     return layout.ModbusClient(
    #         pymodbus.client.sync.ModbusTcpClient(host="localhost", port=5020),
    #         {
    #             0: layout.ModbusRegisterMapping(
    #                 [
    #                     layout.Field("s", "str", length=5, address=2),
    #                     layout.Field("x", "i32"),
    #                     layout.Field("b", "bits", length=16, address=82),
    #                     layout.Field("y", "f16"),
    #                 ]
    #             ),
    #             1: layout.ModbusRegisterMapping(
    #                 [layout.Field("s", "str", length=5, address=2)]
    #             ),
    #         },
    #         single=False,
    #     )

    # @pytest.fixture
    # def client_with_tuples(self):
    #     return layout.ModbusClient(
    #         pymodbus.client.sync.ModbusTcpClient(host="localhost", port=5020),
    #         layout.ModbusRegisterMapping(
    #             [
    #                 layout.Field("x", "i32", address=2),
    #                 layout.Field("y", ("i8", "str", "bits", "u8")),
    #                 layout.Field("z", "i32"),
    #             ],
    #         ),
    #     )

    # def test_write_register_read_holding_registers(self, server, client):
    #     bits = [
    #         False,
    #         False,
    #         True,
    #         False,
    #         True,
    #         True,
    #         False,
    #         True,
    #         False,
    #         True,
    #         False,
    #         False,
    #         False,
    #         True,
    #         True,
    #         True,
    #     ]
    #     client.write_registers(
    #         {
    #             "x": 12,
    #             "s": "hello",
    #             "b": bits,
    #             "y": 3.4,
    #         }
    #     )
    #     assert client.read_holding_registers() == {
    #         "x": 12,
    #         "s": b"hello",
    #         "b": bits,
    #         "y": pytest.approx(3.4, abs=0.001),
    #     }

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
