import pytest

import pymodbus.client.sync
import pymodbus.datastore
import pymodbus.server.sync
import threading

from pylab.live.plugin.modbus import mapping


def run_server(server):
    server.serve_forever()


@pytest.fixture
def server():
    context = pymodbus.datastore.ModbusServerContext(
        slaves={
            0: pymodbus.datastore.ModbusSlaveContext(),
            1: pymodbus.datastore.ModbusSlaveContext(),
        },
        single=False,
    )
    server = pymodbus.server.sync.ModbusTcpServer(context, address=("localhost", 5020))
    t = threading.Thread(target=run_server, args=(server,))
    t.start()
    yield
    # FIXME It's not clear which of these is correct...
    server.shutdown()
    server.server_close()
    t.join()


class TestModbusRegisterMapping:
    pass


class TestModbusClient:
    @pytest.fixture
    def client(self):
        return mapping.ModbusClient(
            pymodbus.client.sync.ModbusTcpClient(host="localhost", port=5020),
            mapping.ModbusRegisterMapping(
                [
                    mapping.Field("s", "str", size_in_bytes=5, address=2),
                    mapping.Field("x", "i32"),
                    mapping.Field(
                        "b", "bits", size_in_bytes=2
                    ),  # , address=82),  # TODO
                    mapping.Field("y", "f16"),
                ],
                byteorder="<",
                wordorder=">",
            ),
        )

    def test_write_register_read_holding_registers(self, server, client):
        bits = [
            False,
            False,
            True,
            False,
            True,
            True,
            False,
            True,
            False,
            True,
            False,
            False,
            False,
            True,
            True,
            True,
        ]
        client.write_registers(
            {
                "x": 12,
                "s": "hello",
                "b": bits,
                "y": 3.4,
            }
        )
        assert client.read_holding_registers() == {
            "x": 12,
            "s": b"hello",
            "b": bits,
            "y": pytest.approx(3.4, abs=0.001),
        }
        # assert client.read_holding_register("b") == bits
        # client.write_register("s", "world")
        # assert client.read_holding_register("s") == b"world"
        # assert client.read_holding_register("b") == bits
        # # assert False
