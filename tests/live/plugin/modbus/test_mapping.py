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
        slaves=pymodbus.datastore.ModbusSlaveContext(), single=True
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
                    mapping.Field("x", "i32", address=0),
                    mapping.Field("y", "f16"),
                ],
                byteorder="<",
                wordorder=">",
            ),
        )

    def test_write_register_read_holding_registers(self, server, client):
        client.write_register("x", 12)
        client.write_register("y", 3.4)
        assert client.read_holding_registers() == {
            "x": 12,
            "y": pytest.approx(3.4, abs=0.001),
        }
