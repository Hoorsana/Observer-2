# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import time

import can
import pytest

from pylab.live.plugin.can import candriver


@pytest.fixture
def data():
    return {'Temperature': 30, 'Humidity': 50}


def _create_can(channel: str) -> candriver.Can:
    db = candriver.Database(
        'resources/tests/live/plugin/can/test.dbc', encoding='utf-8')
    bus = can.interface.Bus(bustype='socketcan', channel=channel, bitrate=125000)
    return candriver.Can(db, bus)


class TestDatabase:

    @pytest.fixture
    def db(self):
        return candriver.Database('resources/tests/live/plugin/can/test.dbc', encoding='utf-8')

    def test_encode_decode(self, data, db):
        msg = db.encode('Weather', data)
        assert db.decode(msg) == data

    @pytest.mark.parametrize('name, data', [
        pytest.param('Foo', {}, id='unknown message name'),
        pytest.param('Weather', {'Bar': 111}, id='illegal data')
    ])
    def test_encode_failure(self, name, data, db):
        with pytest.raises(candriver.CanError):
            db.encode(name, data)

    @pytest.mark.skip
    def test_decode_failure(self):
        pass  # TODO It is unclear which exceptions are thrown.


# Won't test!
@pytest.mark.skip
class TestBusConfig:
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

    def test_functional(self, data, vcan0, vcan1):
        vcan0.send_message('Weather', data)
        time.sleep(0.01)
        result = vcan1.take_received()
        assert result == [data]

    # Won't test!
    @pytest.mark.skip
    def test_from_config(self):
        pass
