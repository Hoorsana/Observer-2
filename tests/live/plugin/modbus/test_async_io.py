import pytest

from pylab.live.plugin.modbus import async_io


class TestProtocol:
    @pytest.mark.asyncio
    async def test_read_holding_register_failure(self, server, protocol):
        with pytest.raises(async_io.ModbusResponseError):
            # The context is too small for this write!
            await protocol.read_holding_register("a", unit=2)
