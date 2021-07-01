# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import copy
from contextlib import nullcontext as does_not_raise
import io

import pytest
import yaml

from pylab.core import infos
from pylab.shared import infos as sharedinfos
from pylab.core import report
from pylab.core import timeseries
from pylab.simulink import simulink
from pylab.simulink import _engine

ml_engine = _engine.import_matlab_engine()


@pytest.mark.dependency('simulink')
@pytest.mark.slow
class TestTest:

    @pytest.mark.parametrize('code, requests, results, severity, effect', [
        pytest.param(
            "error('foo');", [], {}, '',
            pytest.raises(ml_engine.MatlabExecutionError),
            id='MATLAB engine error'
        ),
        pytest.param(
            '', [], {}, '',
            pytest.raises(ml_engine.MatlabExecutionError),
            id='Logbook not found'
        ),
        pytest.param(
            'PYLAB_LOGBOOK = []',
            [
                simulink._LoggingRequest(
                    infos.LoggingInfo(target='foo', signal='bar'),
                    lambda x: x
                )
            ],
            {},
            '',
            pytest.raises(ml_engine.MatlabExecutionError),
            id='Logged data not found'
        ),
        pytest.param(
            (
                "PYLAB_OUTPUT_fooPYLABDOTbar = timeseries([2, 4, 8]', [0, 1, 2]);\n"
                + 'PYLAB_LOGBOOK = ["{""what"": ""..."", ""severity"": ""info""}"];'
            ),
            [
                simulink._LoggingRequest(
                    infos.LoggingInfo(target='foo', signal='bar'),
                    lambda x: x
                )
            ],
            {'foo.bar': timeseries.TimeSeries([0, 1, 2], [[2], [4], [8]])},
            report.INFO,
            does_not_raise(),
            id='Successful extraction of logged data'
        )
    ])
    def test_execute(self, code, requests, results, severity, effect, mocker):
        test = simulink.Test(code, requests)
        with effect:
            report = test.execute()
            assert report.results == results
            assert report.logbook[-1].severity == severity


class TestLoadDetails:

    @pytest.mark.parametrize('side_effect', [
        OSError, FileNotFoundError
    ])
    def test_open_fails(self, side_effect, mocker):
        mocker.patch('builtins.open', mocker.mock_open())
        open.side_effect = side_effect()
        with pytest.raises(side_effect):
            simulink.load_details('/path/to/details')
        open.assert_called_once_with('/path/to/details', 'r')

    def test_yaml_error(self, mocker):
        mocker.patch('yaml.safe_load')
        yaml.safe_load.side_effect = yaml.YAMLError()
        mocker.patch('builtins.open', mocker.mock_open(read_data='foo'))

        with pytest.raises(yaml.YAMLError):
            simulink.load_details('/path/to/details')
        open.assert_called_once_with('/path/to/details', 'r')
        open().read.assert_called_once()
        yaml.safe_load.assert_called_once_with('foo')

    @pytest.mark.parametrize('fixture, path', [
        ('adder', 'resources/examples/adder/matlab_details.yml'),
        ('limit', 'resources/examples/limit_monitoring/matlab_details.yml')
    ])
    def test_success(self, request, fixture, path):
        data = request.getfixturevalue(fixture)
        details = simulink.load_details(path)
        assert details == data[1]


@pytest.mark.dependency('simulink')
@pytest.mark.slow
class TestExamples:

    def test_adder(self, adder):
        test = simulink.create(*adder)
        report = test.execute()
        assert not report.failed
        result = report.results['adder.sum']
        expected = timeseries.TimeSeries(
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            [[100], [125], [100], [50], [0], [100], [200], [100], [0], [0]]
        )
        timeseries.assert_almost_everywhere_close(result, expected, rtol=0.001)

    def test_limit(self, limit):
        test = simulink.create(*limit)
        report = test.execute()
        assert not report.failed
        # FIXME No verification...


@pytest.fixture
def adder():
    info = infos.TestInfo(
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
    details = simulink.Details(
        devices=[
            simulink.DeviceDetails(
                name='adder',
                type='Model',
                data={'filename': 'adder.slx'},
                interface=sharedinfos.ElectricalInterface(
                    ports=[
                        sharedinfos.PortInfo(
                            'val1',
                            1,
                            min=0, max=1,
                            flags=['input', 'analog']
                        ),
                        sharedinfos.PortInfo(
                            'val2',
                            2,
                            min=0, max=1,
                            flags=['input', 'analog']
                        ),
                        sharedinfos.PortInfo(
                            'sum',
                            1,
                            min=0, max=2,
                            flags=['output', 'analog']
                        ),
                    ]
                ),
            ),
            simulink.DeviceDetails(
                name='gpio1',
                type='MiniGenerator',
                data={},
                interface=sharedinfos.ElectricalInterface(
                    ports=[
                        sharedinfos.PortInfo(
                            'value',
                            1,
                            min=0, max=1,
                            flags=['output', 'analog']
                        )
                    ]
                )
            ),
            simulink.DeviceDetails(
                name='gpio2',
                type='MiniGenerator',
                data={},
                interface=sharedinfos.ElectricalInterface(
                    ports=[
                        sharedinfos.PortInfo(
                            'value',
                            1,
                            min=0, max=1,
                            flags=['output', 'analog']
                        )
                    ]
                )
            ),
            simulink.DeviceDetails(
                name='logger',
                type='MiniLogger',
                data={},
                interface=sharedinfos.ElectricalInterface(
                    ports=[
                        sharedinfos.PortInfo(
                            'sum',
                            1,
                            min=0, max=2,
                            flags=['input', 'analog']
                        )
                    ]
                )
            ),
        ],
        connections=[
            sharedinfos.ConnectionInfo('gpio1', 'value', 'adder', 'val1'),
            sharedinfos.ConnectionInfo('gpio2', 'value', 'adder', 'val2'),
            sharedinfos.ConnectionInfo('adder', 'sum', 'logger', 'sum'),
        ]
    )
    return info, details


@pytest.fixture
def limit():
    quick_pulse = infos.PhaseInfo(
        duration=1.0,
        commands=[
            infos.CommandInfo(
                time=0.0,
                command='CmdSetSignal',
                target='monitor',
                data={'signal': 'temperature', 'value': -100}
            ),
            infos.CommandInfo(
                time=0.4,
                command='CmdSetSignal',
                target='monitor',
                data={'signal': 'temperature', 'value': 100}
            ),
            infos.CommandInfo(
                time=0.6,
                command='CmdSetSignal',
                target='monitor',
                data={'signal': 'temperature', 'value': 0}
            ),
        ],
        description=('Send a short burst of high temperature to test the '
                     'responsiveness of the measurement')
    )
    info = infos.TestInfo(
        [
            infos.TargetInfo(
                name='monitor',
                signals=[
                    infos.SignalInfo(
                        name='temperature',
                        flags=['input', 'analog'],
                        min=-100, max=100
                    ),
                    infos.SignalInfo(
                        name='result',
                        flags=['output', 'digital'],
                        min=0, max=1,
                        description=('Return 1 if the temperature limit'
                                     ' exceeds 80 degrees; 0 otherwise')

                    ),
                ],
            )
        ],
        [infos.LoggingInfo(target='monitor', signal='result', period=0.1)],
        [
            copy.deepcopy(quick_pulse), copy.deepcopy(
                quick_pulse), copy.deepcopy(quick_pulse),
            infos.PhaseInfo(
                duration=2.0,
                commands=[
                    infos.CommandInfo(
                        time=0.0, command='CmdSetSignal', target='monitor',
                        data={'signal': 'temperature', 'value': 81}
                    ),
                    infos.CommandInfo(
                        time=1.0, command='CmdSetSignal', target='monitor',
                        data={'signal': 'temperature', 'value': 79}
                    ),
                ],
                description='Test limit values'
            ),
            infos.PhaseInfo(
                duration=2.0,
                commands=[
                    infos.CommandInfo(
                        time=0.0, command='CmdSetSignal', target='monitor',
                        data={'signal': 'temperature', 'value': -95}
                    ),
                    infos.CommandInfo(
                        time=1.0, command='CmdSetSignal', target='monitor',
                        data={'signal': 'temperature', 'value': 95}
                    ),
                ],
                description='Test LO-HI temperature'
            ),
        ]
    )
    details = simulink.Details(
        devices=[
            simulink.DeviceDetails(
                name='monitor',
                type='Model',
                data={'filename': 'limit_monitoring.slx'},
                interface=sharedinfos.ElectricalInterface(
                    ports=[
                        sharedinfos.PortInfo(
                            'temperature',
                            1,
                            min=-100, max=100,
                            flags=['input', 'analog']
                        ),
                        sharedinfos.PortInfo(
                            'result',
                            1,
                            min=0, max=1,
                            flags=['output', 'digital']
                        ),
                    ]
                ),
            ),
            simulink.DeviceDetails(
                name='gpio',
                type='MiniGenerator',
                data={},
                interface=sharedinfos.ElectricalInterface(
                    ports=[
                        sharedinfos.PortInfo(
                            'value',
                            1,
                            min=-100, max=100,
                            flags=['output', 'analog']
                        )
                    ]
                )
            ),
            simulink.DeviceDetails(
                name='logger',
                type='MiniLogger',
                data={},
                interface=sharedinfos.ElectricalInterface(
                    ports=[
                        sharedinfos.PortInfo(
                            'result',
                            1,
                            min=0, max=1,
                            flags=['input', 'digital']
                        )
                    ]
                )
            ),
        ],
        connections=[
            sharedinfos.ConnectionInfo('gpio', 'value', 'monitor', 'temperature'),
            sharedinfos.ConnectionInfo('monitor', 'result', 'logger', 'result'),
        ]
    )
    return info, details
