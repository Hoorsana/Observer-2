# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio

import pymodbus.datastore
import pymodbus.server.async_io
import pymodbus.client.asynchronous.tcp
import pymodbus.client.asynchronous.schedulers
import pytest

from pylab.live.plugin.modbus import async_io


# See https://github.com/pytest-dev/pytest-asyncio/issues/68
@pytest.fixture(scope="session")
def event_loop(request):
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# We would like to start a new server for every test, but this results
# in connectivity issues. Hence, ``scope="session"``.
@pytest.fixture(scope="session")
async def server():
    context = pymodbus.datastore.ModbusServerContext(
        slaves={
            0: pymodbus.datastore.ModbusSlaveContext(
                hr=pymodbus.datastore.ModbusSequentialDataBlock(0, list(range(100))),
                ir=pymodbus.datastore.ModbusSequentialDataBlock(0, list(range(100))),
                co=pymodbus.datastore.ModbusSequentialDataBlock(0, [0]*100),
                di=pymodbus.datastore.ModbusSequentialDataBlock(0, [0b10100100]*100),
                zero_mode=True,
            ),
            1: pymodbus.datastore.ModbusSlaveContext(
                hr=pymodbus.datastore.ModbusSequentialDataBlock(0, list(range(100))),
                ir=pymodbus.datastore.ModbusSequentialDataBlock(0, list(range(100))),
                zero_mode=True,
            ),
            2: pymodbus.datastore.ModbusSlaveContext(
                hr=pymodbus.datastore.ModbusSequentialDataBlock(0, [0, 1, 2]),
                zero_mode=True
            ),
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


@pytest.fixture
def client(event_loop):
    _, client = pymodbus.client.asynchronous.tcp.AsyncModbusTCPClient(
        pymodbus.client.asynchronous.schedulers.ASYNC_IO,
        port=5020,
        loop=event_loop,
    )
    return client
