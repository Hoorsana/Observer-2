import time

import pytest

from pylab._private import rogueplugin
from pylab.core import infos
from pylab.live import live


@pytest.fixture
def configure():
    # TODO This type of info appears in many tests. Refactor in conftest?
    info = infos.TestInfo(
        [
            infos.TargetInfo(
                name='adder',
                signals=[
                    infos.SignalInfo(
                        name='val1',
                        min=0,
                        max=100
                    ),
                    infos.SignalInfo(
                        name='val2',
                        min=0,
                        max=100
                    ),
                    infos.SignalInfo(
                        name='sum',
                        min=0,
                        max=200
                    ),
                ],
            )
        ],
        [infos.LoggingInfo(target='adder', signal='sum', period=0.01)],
        [
            infos.PhaseInfo(
                duration=5.0,
                commands=[
                    infos.CommandInfo(
                        time=0.0, command='CmdSetSignal', target='adder',
                        data={'signal': 'val1', 'value': 50}
                    ),
                    infos.CommandInfo(
                        time=0.0, command='CmdSetSignal', target='adder',
                        data={'signal': 'val2', 'value': 50}
                    ),
                    infos.CommandInfo(
                        time=1.0, command='CmdSetSignal', target='adder',
                        data={'signal': 'val1', 'value': 75}
                    ),
                    infos.CommandInfo(
                        time=2.0, command='CmdSetSignal', target='adder',
                        data={'signal': 'val2', 'value': 25}
                    ),
                    infos.CommandInfo(
                        time=3.0, command='CmdSetSignal', target='adder',
                        data={'signal': 'val1', 'value': 25}
                    ),
                    infos.CommandInfo(
                        time=4.0, command='CmdSetSignal', target='adder',
                        data={'signal': 'val1', 'value': 0}
                    ),
                    infos.CommandInfo(
                        time=4.0, command='CmdSetSignal', target='adder',
                        data={'signal': 'val2', 'value': 0}
                    ),
                ]
            ),
            infos.PhaseInfo(
                duration=4.0,
                commands=[
                    infos.CommandInfo(
                        time=0.0, command='CmdSetSignal', target='adder',
                        data={'signal': 'val1', 'value': 0}
                    ),
                    infos.CommandInfo(
                        time=0.0, command='CmdSetSignal', target='adder',
                        data={'signal': 'val2', 'value': 100}
                    ),
                    infos.CommandInfo(
                        time=1.0, command='CmdSetSignal', target='adder',
                        data={'signal': 'val1', 'value': 100}
                    ),
                    infos.CommandInfo(
                        time=2.0, command='CmdSetSignal', target='adder',
                        data={'signal': 'val2', 'value': 0}
                    ),
                    infos.CommandInfo(
                        time=3.0, command='CmdSetSignal', target='adder',
                        data={'signal': 'val1', 'value': 0}
                    ),
                ]
            ),
        ]
    )
    details = live.Details(
        devices=[
            live.DeviceDetails(
                name='adder',
                module='pylab._private.rogueplugin',
                type='Device',
                data={
                    'defaults': {
                        'DAC0': 0.0,
                        'A0': 0.0,
                        'A1': 0.0,
                    },
                    'loop': lambda d: d.set_value('DAC0', d.get_value('A0') + d.get_value('A1'))
                },
                interface=infos.ElectricalInterface(
                    ports=[
                        infos.PortInfo(
                            'val1',
                            'A0',
                            min=0, max=100,
                        ),
                        infos.PortInfo(
                            'val2',
                            'A1',
                            min=0, max=100,
                        ),
                        infos.PortInfo(
                            'sum',
                            'DAC0',
                            min=0, max=200,
                        ),
                    ]
                )
            ),
            live.DeviceDetails(
                name='gpio',
                module='pylab._private.rogueplugin',
                type='Device',
                data={
                    'defaults': {
                        'DAC0': 0.0,
                        'DAC1': 0.0,
                        'A0': 0.0,
                    }
                },
                interface=infos.ElectricalInterface(
                    ports=[
                        infos.PortInfo(
                            'out1',
                            'DAC0',
                            min=0, max=100
                        ),
                        infos.PortInfo(
                            'out2',
                            'DAC1',
                            min=0, max=100
                        ),
                        infos.PortInfo(
                            'sum',
                            'A0',
                            min=0, max=200
                        ),
                    ]
                )
            )
        ],
        connections=[
            infos.ConnectionInfo(
                sender='gpio', sender_port='out1',
                receiver='adder', receiver_port='val1'
            ),
            infos.ConnectionInfo(
                sender='gpio', sender_port='out2',
                receiver='adder', receiver_port='val2'
            ),
            infos.ConnectionInfo(
                sender='adder', sender_port='sum',
                receiver='gpio', receiver_port='sum'
            ),
        ]
    )
    rogueplugin.init(info, details)
    yield
    rogueplugin.reset()


@pytest.fixture
def adder():
    _adder = rogueplugin.Device(
        id='adder',
        ports=['A0', 'A1', 'DAC0']
    )
    _adder.open()
    yield _adder
    _adder.close()


@pytest.fixture
def gpio():
    _gpio = rogueplugin.Device(
        id='gpio',
        ports=['DAC0', 'DAC1', 'A0']
    )
    _gpio.open()
    yield _gpio
    _gpio.close()


def test_minimal(configure, adder, gpio):
    rogueplugin.post_init('unused', 'unused', 'unused')
    time.sleep(0.1)
    rogueplugin._server.process_errors()


def test_set_signal_get_signal(configure, adder, gpio):
    # TODO `log_signal` and `post_init` occur in the opposite order in
    # the live driver, but the order used here makes testing easier.
    _, future = gpio.log_signal('A0', 0.01)
    rogueplugin.post_init('unused', 'unused', 'unused')
    time.sleep(0.1)
    gpio.set_signal('DAC0', 25).wait()
    time.sleep(0.1)
    gpio.set_signal('DAC1', 75).wait()
    time.sleep(0.1)
    gpio.set_signal('DAC1', 50).wait()
    time.sleep(0.1)
    gpio.end_log_signal('A0').wait()
    future.wait()
    rogueplugin._server.process_errors()
    result = future.get_result()
    assert result(0.05) == 0.0
    assert result(0.15) == 25.0
    assert result(0.25) == 100.0
    assert result(0.35) == 75.0
