import os

import pytest

from pylab.core import infos
from pylab.live import live
from pylab.live.plugin.saleae import logic


def test_init(adder, details):
    logic.init(adder, details)


@pytest.fixture
def adder():
    return infos.TestInfo(
        [
            infos.TargetInfo(
                name='adder',
                signals=[
                    infos.SignalInfo(
                        name='val1',
                        flags=['input', 'analog'],
                        min=0,
                        max=100
                    ),
                    infos.SignalInfo(
                        name='val2',
                        flags=['input', 'analog'],
                        min=0,
                        max=100
                    ),
                    infos.SignalInfo(
                        name='sum',
                        flags=['output', 'analog'],
                        min=0,
                        max=200
                    ),
                ],
            )
        ],
        [infos.LoggingInfo(target='adder', signal='sum', period=0.1)],
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


@pytest.fixture
def details():
    return live.Details(
        devices=[
            live.DeviceDetails(
                name='adder',
                module='pylab.live.live',
                type='UsbSerialDevice.from_serial_number',
                data={'serial_number': os.environ['PYLAB_USB_SERIAL_NUMBER_DEVICE']},
                interface=infos.ElectricalInterface(
                    ports=[
                        infos.PortInfo(
                            'val1',
                            'A0',
                            min=168, max=852,
                            flags=['input', 'analog']
                        ),
                        infos.PortInfo(
                            'val2',
                            'A1',
                            min=168, max=852,
                            flags=['input', 'analog']
                        ),
                        infos.PortInfo(
                            'sum',
                            'DAC0',
                            min=0, max=255,
                            flags=['output', 'analog']
                        ),
                    ]
                )
            ),
            live.DeviceDetails(
                name='gpio',
                module='pylab.live.plugin.controllino.controllino',
                type='PylabControllino.from_serial_number',
                data={
                    'serial_number': os.environ['PYLAB_USB_SERIAL_NUMBER_CONTROLLINO'],
                    'baudrate': 19200
                },
                interface=infos.ElectricalInterface(
                    ports=[
                        infos.PortInfo(
                            'out1',
                            'DAC0',
                            min=0, max=255,
                            flags=['output', 'analog'],
                        ),
                        infos.PortInfo(
                            'out2',
                            'DAC1',
                            min=0, max=255,
                            flags=['output', 'analog'],
                        ),
                        infos.PortInfo(
                            'sum',
                            'A0',
                            min=168, max=852,
                            flags=['input', 'analog']
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
        ],
        extension={
            'saleae': {
                'init': {
                    'host': 'localhost',
                    'performance': 'Full',
                    'port': 10429
                }
            }
        }
    )
