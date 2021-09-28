# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import time

import can
import pytest
import sys
from typing import Optional

from pylab.core import workflow
from pylab.live import live
from pylab.live.plugin.can import candriver


pytestmark = pytest.mark.skipif(
    not sys.platform.startswith("linux"), reason="vcan only available on linux"
)


class _CanPassthruBus(candriver.CanBus):
    yaml_tag = u"!_CanPassthruBus"

    def __init__(
        self, name: str, db: candriver.Database, bus: can.interface.Bus
    ) -> None:
        super().__init__(name, db, bus, _PassthruListener(db, bus))


class _PassthruListener:
    def __init__(self, db: candriver.Database, bus: can.interface.Bus) -> None:
        self._db = db
        self._bus = bus
        self._notifier = can.Notifier(bus, listeners=[self._passthru])

    def kill(self, timeout: Optional[float]) -> None:
        if timeout is None:
            self._notifier.stop()  # Use default timeout of python-can.
        else:
            self._notifier.stop(timeout)

    def _passthru(self, msg: can.Message) -> None:
        self._bus.send(msg)


def _create_can(channel: str) -> candriver.CanBus:
    db = candriver.Database(
        "resources/tests/live/plugin/can/test.dbc", encoding="utf-8"
    )
    bus = can.interface.Bus(bustype="socketcan", channel=channel, bitrate=125000)
    return candriver.CanBus("foo", db, bus)


@pytest.fixture
def data():
    return {"Temperature": 30, "Humidity": 50}


class TestDatabase:
    @pytest.fixture
    def db(self):
        return candriver.Database(
            "resources/tests/live/plugin/can/test.dbc", encoding="utf-8"
        )

    def test_encode_decode(self, data, db):
        msg = db.encode("Weather", data)
        assert db.decode(msg) == data

    @pytest.mark.parametrize(
        "name, data",
        [
            pytest.param("Foo", {}, id="unknown message name"),
            pytest.param("Weather", {"Bar": 111}, id="illegal data"),
        ],
    )
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


class TestCanBus:
    @pytest.fixture
    def vcan0(self):
        _vcan = _create_can("vcan0")
        yield _vcan
        _vcan.kill()

    @pytest.fixture
    def vcan1(self):
        _vcan = _create_can("vcan1")
        yield _vcan
        _vcan.kill()

    def test_functional(self, data, vcan0, vcan1):
        vcan0.send_message("Weather", data)
        time.sleep(0.01)
        result = vcan1.listener.take_received()
        assert result == [data]

    # Won't test!
    @pytest.mark.skip
    def test_from_config(self):
        pass


def test_functional():
    report = workflow.run_from_files(
        driver=live,
        test="resources/tests/live/plugin/can/test.yml",
        details="resources/tests/live/plugin/can/vcan_details.yml",
    )
    results = report.results["vcan0-dev.vcan0-signal"]
    assert results == [
        {"Temperature": 30, "Humidity": 50},
        {"Temperature": 50, "Humidity": 30},
    ]


@pytest.mark.skip
def test_pcan():
    report = workflow.run_from_files(
        driver=live,
        test="resources/tests/live/plugin/can/pcan.yml",
        details="resources/tests/live/plugin/can/pcan_details.yml",
    )
    results = reports.results["pcan0-dev.pcan0-signal"]
