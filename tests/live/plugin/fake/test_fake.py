import pytest

import time

from pylab.core import timeseries
from pylab.core import report
from pylab.live.plugin.fake import fake


class Device(fake.Device):

    def __init__(self, name):
        super().__init__(
            name,
            [{'channel': 'IN', 'value': 0.0}, {'channel': 'OUT', 'value': 0.0}]
        )

    def update(self):
        self.set_value('OUT', 2*self.get_value('IN'))


class TestDevice:

    @pytest.fixture
    def device(self):
        return Device('device')

    def test_set_value_get_value(self, device):
        device.set_value('OUT', 1.23)
        value = device.get_value('OUT')
        assert value == 1.23

    def test_set_signal_get_value(self, device):
        assert device.set_signal('OUT', 1.23).done
        value = device.get_value('OUT')
        assert value == 1.23

    def test_set_value_failure(self, device):
        with pytest.raises(ValueError):
            device.set_value('OUT2', 1.23)

    def test_get_value_failure(self, device):
        with pytest.raises(ValueError):
            device.get_value('IN3')

    def test_set_signal_failure(self, device):
        future = device.set_signal('OUT3', 1.234)
        assert future.done
        assert future.log.severity == report.PANIC

    def test_update(self, device):
        device.set_value('IN', 1.23)
        device.update()
        assert device.get_value('OUT') == 2.46


class TestPluginFake:

    def test_functional(self):
        device1 = Device('device1')
        device2 = fake.Device(
            'device2',
            [{'channel': 'IN', 'value': 0.0}, {'channel': 'OUT', 'value': 0.0}]
        )
        devices = [device1, device2]
        manager = fake.DeviceManager(devices)
        manager.connect('device1', 'OUT', 'device2', 'IN')
        manager.connect('device2', 'OUT', 'device1', 'IN')
        plugin = fake.PluginFake(manager)

        plugin.start()
        device2.set_value('OUT', 1.23)
        time.sleep(0.01)
        plugin.stop()
        assert device2.get_value('IN') == 2.46

    def test_functional_with_logger(self):
        device = Device('device')
        logger = fake.Logger(
            'logger',
            [{'channel': 'IN', 'value': 0.0}, {'channel': 'OUT', 'value': 0.0}]
        )
        devices = [device, logger]
        manager = fake.DeviceManager(devices)
        manager.connect('device', 'OUT', 'logger', 'IN')
        manager.connect('logger', 'OUT', 'device', 'IN')

        plugin = fake.PluginFake(manager)
        plugin.start()
        accepted, future = logger.log_signal('IN', 0.1)
        assert accepted.done
        time.sleep(0.05)
        logger.set_value('OUT', 1)
        time.sleep(0.06)
        assert logger.end_log_signal('IN').done
        plugin.stop()
        assert future.done
        ts = future.get_result()
        ts.kind = 'nearest'
        assert ts(0.1) == 2
