import time

import pytest

from pylab._private import rogueplugin
from pylab.core import infos
from pylab.shared import infos as sharedinfos
from pylab.core import report
from pylab.live import live


STEP_SIZE = 0.1
TIMEOUT = 0.1
PERIOD = 0.01
MIN = 0
MAX = 100


class TestGlobal:

    @pytest.fixture
    def server(self):
        info = None  # Remains unused!
        details = live.Details(
            devices=[
                live.DeviceDetails(
                    name='adder',
                    module='pylab._private.rogueplugin',
                    type='Device',
                    data={},
                    extension={
                        'defaults': {
                            'DAC0': 0.0,
                            'A0': 0.0,
                            'A1': 0.0,
                        },
                        'loop': lambda d: d.set_value('DAC0', d.get_value('A0') + d.get_value('A1'))
                    },
                    interface=sharedinfos.ElectricalInterface(
                        ports=[
                            sharedinfos.PortInfo(
                                'val1',
                                'A0',
                                min=MIN, max=MAX,
                            ),
                            sharedinfos.PortInfo(
                                'val2',
                                'A1',
                                min=MIN, max=MAX,
                            ),
                            sharedinfos.PortInfo(
                                'sum',
                                'DAC0',
                                min=MIN, max=2*MAX,
                            ),
                        ]
                    )
                ),
                live.DeviceDetails(
                    name='gpio',
                    module='pylab._private.rogueplugin',
                    type='Device',
                    data={},
                    extension={
                        'defaults': {
                            'DAC0': 0.0,
                            'DAC1': 0.0,
                            'A0': 0.0,
                        }
                    },
                    interface=sharedinfos.ElectricalInterface(
                        ports=[
                            sharedinfos.PortInfo(
                                'out1',
                                'DAC0',
                                min=MIN, max=MAX
                            ),
                            sharedinfos.PortInfo(
                                'out2',
                                'DAC1',
                                min=MIN, max=MAX
                            ),
                            sharedinfos.PortInfo(
                                'sum',
                                'A0',
                                min=MIN, max=2*MAX
                            ),
                        ]
                    )
                )
            ],
            connections=[
                sharedinfos.ConnectionInfo(
                    sender='gpio', sender_port='out1',
                    receiver='adder', receiver_port='val1'
                ),
                sharedinfos.ConnectionInfo(
                    sender='gpio', sender_port='out2',
                    receiver='adder', receiver_port='val2'
                ),
                sharedinfos.ConnectionInfo(
                    sender='adder', sender_port='sum',
                    receiver='gpio', receiver_port='sum'
                ),
            ]
        )
        rogueplugin.init(info, details)
        yield
        rogueplugin.reset()

    @pytest.fixture
    def adder(self):
        _adder = rogueplugin.Device(
            id='adder',
            ports=['A0', 'A1', 'DAC0']
        )
        _adder.open()
        yield _adder
        _adder.close()

    @pytest.fixture
    def gpio(self):
        _gpio = rogueplugin.Device(
            id='gpio',
            ports=['DAC0', 'DAC1', 'A0']
        )
        _gpio.open()
        yield _gpio
        _gpio.close()

    def test_start_stop(self, server, adder, gpio):
        rogueplugin.post_init('unused', 'unused', 'unused')
        time.sleep(TIMEOUT)
        rogueplugin._server.process_errors()

    def test_set_signal_get_signal(self, server, adder, gpio):
        # `log_signal` and `post_init` occur in the opposite order in the
        # live driver, but the order used here makes testing easier.
        accept, future = gpio.log_signal('A0', PERIOD)
        assert accept.wait(timeout=TIMEOUT)
        rogueplugin.post_init('unused', 'unused', 'unused')
        time.sleep(TIMEOUT)
        gpio.set_signal('DAC0', 25).wait()
        time.sleep(TIMEOUT)
        gpio.set_signal('DAC1', 75).wait()
        time.sleep(TIMEOUT)
        gpio.set_signal('DAC1', 50).wait()
        time.sleep(TIMEOUT)
        gpio.end_log_signal('A0').wait()
        future.wait()
        rogueplugin._server.process_errors()
        result = future.get_result()
        print(result.values)
        assert result(0*STEP_SIZE + 0.05) == 0.0
        assert result(1*STEP_SIZE + 0.05) == 25.0
        assert result(2*STEP_SIZE + 0.05) == 100.0
        assert result(3*STEP_SIZE + 0.05) == 75.0


class TestDevice:

    @pytest.fixture
    def server(self):
        details = live.Details(
            devices=[
                live.DeviceDetails(
                    name='device',
                    module='pylab._private.rogueplugin',
                    type='Device',
                    data={},
                    extension={'defaults': {'port': 0.0}},
                    interface=sharedinfos.ElectricalInterface(
                        ports=[
                            sharedinfos.PortInfo(
                                'port_frontend',
                                'port',
                                min=MIN, max=MAX
                            ),
                        ]
                    )
                )
            ],
            connections=[]
        )
        rogueplugin.init(None, details)
        yield
        rogueplugin.reset()

    @pytest.fixture
    def device(self):
        return rogueplugin.Device(id='device', ports=['port'])

    def test_open(self, server, device):
        f = device.open()
        assert f.wait(timeout=TIMEOUT)
        f.log.expect(report.INFO)

    def test_close(self, server, device):
        f = device.close()
        assert f.wait(timeout=TIMEOUT)
        f.log.expect(report.INFO)

    def test_setup(self, server, device):
        f = device.setup()
        assert f.wait(timeout=TIMEOUT)
        f.log.expect(report.INFO)

    def test_log_signal(self, server, device):
        f, _ = device.log_signal('port', PERIOD)
        assert f.wait(timeout=TIMEOUT)
        f.log.expect(report.INFO)

    def test_log_signal_failure(self, server, device):
        f, _ = device.log_signal('this port does not exist', PERIOD)
        assert f.wait(timeout=TIMEOUT)
        f.log.expect(report.FAILED)

    def test_set_signal(self, server, device):
        f = device.set_signal('port', 1.2)
        assert f.wait(timeout=TIMEOUT)
        f.log.expect(report.INFO)

    def test_set_signal_failed(self, server, device):
        f = device.set_signal('this port does not exist', 1.2)
        assert f.wait(timeout=TIMEOUT)
        f.log.expect(report.FAILED)
