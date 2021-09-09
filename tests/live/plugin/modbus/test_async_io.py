# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from pylab.live.plugin.modbus import async_io
from pylab.live.plugin.modbus import layout
from pylab.live.plugin.modbus import registers


# FIXME It's slightly awkward that all layouts refer to the slave context of the server in
# conftest.py
@pytest.fixture
def protocol(client):
    return async_io.Protocol(
        client.protocol,
        # This layout is too large for its context:
        {
            2: layout.SlaveContextLayout(
                holding_registers=registers.RegisterMapping([registers.Number("a", "i64", address=23)])
            ),
        },
        single=False
    )


class TestProtocol:
    @pytest.mark.asyncio
    async def test_read_holding_register_failure(self, server, protocol):
        with pytest.raises(async_io.ModbusResponseError):
            # The context is too small for this write!
            await protocol.read_holding_register("a", unit=2)
