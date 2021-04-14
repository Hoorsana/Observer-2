# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import time

import can
import pytest

from pylab.live.plugin.can import candriver


def _create_can(channel: str) -> candriver.Can:
    db = candriver.Database(
        'resources/tests/live/plugin/can/test.dbc', encoding='utf-8')
    bus = can.interface.Bus(bustype='socketcan', channel=channel, bitrate=125000)
    return candriver.Can(db, bus)


class TestDatabase:
    pass


class TestCan:

    @pytest.fixture
    def vcan0(self):
        _vcan = _create_can('vcan0')
        yield _vcan
        _vcan.kill()

    @pytest.fixture
    def vcan1(self):
        _vcan = _create_can('vcan1')
        yield _vcan
        _vcan.kill()

    def test_functional(self, vcan0, vcan1):
        data = {'Temperature': 30, 'Humidity': 50}
        vcan0.send_message('Weather', data)
        time.sleep(0.01)
        result = vcan1.take_received()
        assert result == [data]
