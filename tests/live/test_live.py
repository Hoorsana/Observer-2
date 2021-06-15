# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os

import pytest

from pylab.core import infos
from pylab.core import timeseries
from pylab.core import workflow
from pylab.core import testing
from pylab.live import live
from pylab.live.plugin import controllino


@pytest.fixture
def assertion():
    a = testing.TimeseriesAlmostEqual(
        timeseries.TimeSeries(
            list(range(10)),
            [[100], [125], [100], [50], [0], [100], [200], [100], [0], [0]]
        ),
        rtol=0.2
    )
    return a.wrap_in_dispatcher({'actual': 'adder.sum'})


@pytest.mark.xfail
def test_functional_fake(adder, details_fake, assertion):
    report = workflow.run(live, adder, details_fake)
    result = report.results['adder.sum']
    assertion.assert_(report.results)


@pytest.mark.timeout(20.0)
def test_functional_arduino(adder, details_arduino, assertion):
    report = workflow.run(live, adder, details_arduino)
    result = report.results['adder.sum']
    result.shift(-0.30)
    timeseries.pretty_print(result)
    assertion.assert_(report.results)


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
def details_arduino():
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
        ]
    )


@pytest.fixture
def details_fake():
    return live.Details(
        devices=[
            live.DeviceDetails(
                name='adder',
                module='pylab.live.plugin.fake.fake',
                type='Device',
                data={
                    'name': 'adder',
                    'ports': [
                        {'channel': 'IN1'},
                        {'channel': 'IN2'},
                        {'channel': 'OUT'},
                    ]
                },
                interface=infos.ElectricalInterface(
                    ports=[
                        infos.PortInfo(
                            'val1',
                            'IN1',
                            min=0, max=100,
                            flags=['input', 'analog']
                        ),
                        infos.PortInfo(
                            'val2',
                            'IN2',
                            min=0, max=100,
                            flags=['input', 'analog']
                        ),
                        infos.PortInfo(
                            'sum',
                            'OUT',
                            min=0, max=200,
                            flags=['output', 'analog']
                        ),
                    ]
                )
            ),
            live.DeviceDetails(
                name='gpio',
                module='pylab.live.plugin.fake.fake',
                type='Logger',
                data={
                    'name': 'gpio',
                    'ports': [
                        {'channel': 'OUT1'},
                        {'channel': 'OUT2'},
                        {'channel': 'IN'},
                    ]
                },
                interface=infos.ElectricalInterface(
                    ports=[
                        infos.PortInfo(
                            'out1',
                            'OUT1',
                            min=0, max=100,
                            flags=['output', 'analog'],
                        ),
                        infos.PortInfo(
                            'out2',
                            'OUT2',
                            min=0, max=100,
                            flags=['output', 'analog'],
                        ),
                        infos.PortInfo(
                            'sum',
                            'IN',
                            min=0, max=200,
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
        ]
    )
