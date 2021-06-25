# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from pylab.core import errors
from pylab.core import infos


class TestTestInfo:

    @pytest.mark.parametrize('targets, logging, phases', [
        pytest.param(
            [
                infos.TargetInfo(
                    name='foo',
                    signals=[]
                ),
                infos.TargetInfo(
                    name='foo',
                    signals=[]
                ),
            ],
            [],
            [],
            id='conflicting target ids'
        ),
        pytest.param(
            [
                infos.TargetInfo(
                    name='foo',
                    signals=[
                        infos.SignalInfo(
                            name='baz',
                            min=0, max=1
                        )
                    ]
                ),
            ],
            [
                infos.LoggingInfo(
                    target='bar',
                    signal='baz'
                )
            ],
            [],
            id='logging target not found'
        ),
        pytest.param(
            [
                infos.TargetInfo(
                    name='foo',
                    signals=[
                        infos.SignalInfo(
                            name='baz',
                            min=0, max=1
                        )
                    ]
                ),
            ],
            [
                infos.LoggingInfo(
                    target='bar',
                    signal='foobar'
                )
            ],
            [],
            id='signal not found'
        ),
        pytest.param(
            [
                infos.TargetInfo(
                    name='foo',
                    signals=[
                        infos.SignalInfo(
                            name='baz',
                            min=0, max=1
                        )
                    ]
                ),
            ],
            [
                infos.LoggingInfo(
                    target='bar',
                    signal='baz',
                    period=None
                ),
                infos.LoggingInfo(
                    target='bar',
                    signal='baz',
                    period=1.0
                )
            ],
            [],
            id='double logging request'
        ),
        pytest.param(
            [
                infos.TargetInfo(
                    name='foo',
                    signals=[
                        infos.SignalInfo(
                            name='baz',
                            min=0, max=1
                        )
                    ]
                ),
            ],
            [],
            [
                infos.PhaseInfo(
                    duration=1.0,
                    commands=[
                        infos.CommandInfo(
                            time=0.0,
                            command='bar',
                            target='baz'
                        )
                    ]
                )
            ],
            id='command target not found'
        ),
    ])
    def test_failure(self, targets, logging, phases):
        with pytest.raises(errors.InfoError):
            infos.TestInfo(targets, logging, phases)


class TestCommandInfo:

    def test_failure(self):
        with pytest.raises(errors.InfoError):
            infos.CommandInfo(-0.1, 'foo', 'bar')


class TestPhaseInfo:

    @pytest.mark.parametrize('duration, commands', [
        pytest.param(
            -0.3, [],
            id='Negative duration'
        ),
        pytest.param(
            1.23,
            [
                infos.CommandInfo(
                    time=2.34,
                    command='foo',
                    target='bar'
                )
            ],
            id='Execution time exceeds phase duration'
        )
    ])
    def test_failure(self, duration, commands):
        with pytest.raises(errors.InfoError):
            infos.PhaseInfo(duration, commands)

    def test_from_dict(self):
        data = {
            'duration': 12.34,
            'commands': [
                {'time': 1.2, 'command': 'CmdFoo', 'target': 'foo',
                    'data': {}, 'description': 'doc'},
                {'time': 3.4, 'command': 'CmdBar', 'target': 'foo',
                    'data': {'bar': 'baz'}, 'description': 'doc'},
            ],
            'description': 'foobar'
        }
        phase = infos.PhaseInfo.from_dict(data)
        expected = infos.PhaseInfo(
            duration=12.34,
            commands=[
                infos.CommandInfo(
                    time=1.2,
                    command='CmdFoo',
                    target='foo',
                    description='doc'
                ),
                infos.CommandInfo(
                    time=3.4,
                    command='CmdBar',
                    target='foo',
                    data={'bar': 'baz'},
                    description='doc'
                )
            ],
            description='foobar'
        )
        assert phase == expected

    @pytest.mark.parametrize('data', [
        pytest.param({}, id='Missing duration'),
        pytest.param({'duration': 1.2, 'foo': 'bar'}, id='Unexpected field')
    ])
    def test_from_dict_failure(self, data):
        with pytest.raises(errors.InfoError):
            infos.PhaseInfo.from_dict(data)


class TestLoggingInfo:

    @pytest.mark.parametrize('period, kind', [
        pytest.param('foo', 'next', id='wrong period type'),
        pytest.param(-1.23, 'next', id='negative period'),
        pytest.param(0.0, 'next', id='zero period'),
        pytest.param(1.23, 'foo', id='unknown kind')
    ])
    def test_failure(self, period, kind):
        with pytest.raises(errors.InfoError):
            infos.LoggingInfo('foo', 'bar', period, kind)


class TestSignalInfo:

    @pytest.mark.parametrize('name, min, max', [
        pytest.param(
            'foo', 2.0, 1.0,
            id='min larger than max'
        ),
        pytest.param(
            'foo.bar', 1.0, 2.0,
            id='invalid id'
        )
    ])
    def test_failure(self, name, min, max):
        with pytest.raises(errors.InfoError):
            infos.SignalInfo(name, min, max)

    @pytest.mark.parametrize('kwargs, expected', [
        ({'name': 'foo', 'min': 123, 'max': 456},
         infos.SignalInfo(name='foo', min=123, max=456)),
        ({'name': 'bar', 'range': '123.0..456'},
         infos.SignalInfo(name='bar', min=123, max=456))
    ])
    def test___init__success(self, kwargs, expected):
        info = infos.SignalInfo(**kwargs)
        assert info == expected

    @pytest.mark.parametrize('kwargs', [
        {'name': 'foo', 'min': 123, 'range': '123..456'},
        {'name': 'bar', 'max': 234, 'range': '123.0..456'},
        {'name': 'bar', 'min': 123, 'max': 234, 'range': '123.0..456'},
        pytest.param({'name': 'bar'}, id='No range specified', marks=pytest.mark.xfail),
    ])
    def test___init__failure(self, kwargs):
        with pytest.raises(ValueError):
            infos.SignalInfo(**kwargs)


class TestTargetInfo:

    @pytest.mark.parametrize('name, signals', [
        pytest.param(
            'foo.bar', [],
            id='invalid id'
        ),
        pytest.param(
            'foo',
            [
                infos.SignalInfo(name='bar', min=0, max=1),
                infos.SignalInfo(name='bar', min=1, max=2),
            ],
            id='duplicate signal id'
        )
    ])
    def test_failure(self, name, signals):
        with pytest.raises(errors.InfoError):
            infos.TargetInfo(name, signals)

    def test_from_dict(self):
        data = {
            'name': 'foo',
            'signals': [
                {'name': 'bar', 'min': 123, 'max': 456},
                {'name': 'baz', 'min': 0, 'max': 1.234},
            ],
            'description': 'foobar'
        }
        info = infos.TargetInfo.from_dict(data)
        expected = infos.TargetInfo(
            name='foo',
            signals=[
                infos.SignalInfo(name='bar', min=123, max=456),
                infos.SignalInfo(name='baz', min=0, max=1.234),
            ],
            description='foobar'
        )
        assert info == expected

    @pytest.mark.parametrize('data', [
        pytest.param({}, id='Missing name'),
        pytest.param({'name': 'foo', 'foo': 'bar'}, id='Unexpected field')
    ])
    def test_from_dict_failure(self, data):
        with pytest.raises(errors.InfoError):
            infos.TargetInfo.from_dict(data)


class TestPortInfo:

    @pytest.mark.parametrize('kwargs, expected', [
        ({'name': 'foo', 'channel': 'ch1', 'min': 123, 'max': 456},
         infos.SignalInfo(name='foo', min=123, max=456)),
        ({'name': 'bar', 'channel': 'ch2', 'range': '123.0..456'},
         infos.SignalInfo(name='bar', min=123, max=456))
    ])
    def test___init__success(self, kwargs, expected):
        info = infos.PortInfo(**kwargs)
        assert info == expected

    @pytest.mark.parametrize('kwargs', [
        {'signal': 'foo', 'channel': 'ch1', 'min': 123, 'range': '123..456'},
        {'signal': 'bar', 'channel': 'ch1', 'max': 234, 'range': '123.0..456'},
        {'signal': 'bar', 'channel': 'ch1', 'min': 123, 'max': 234, 'range': '123.0..456'},
        pytest.param(
            {'signal': 'bar', 'channel': 'ch1', },
            id='No range specified',
            marks=pytest.mark.xfail
        )
    ])
    def test___init__success(self, kwargs):
        with pytest.raises(ValueError):
            infos.PortInfo(**kwargs)


class TestElectricalInterface:

    @pytest.fixture
    def inf(self):
        return infos.ElectricalInterface(
            [infos.PortInfo('foo', 'ch1', 0, 1),
             infos.PortInfo('bar', 'ch2', 3, 4), ],
            'baz')

    def test_from_dict(self, inf):
        data = {
            'ports': [
                {'signal': 'foo', 'channel': 'ch1', 'min': 0, 'max': 1},
                {'signal': 'bar', 'channel': 'ch2', 'min': 3, 'max': 4},
            ],
            'description': 'baz'
        }
        info = infos.ElectricalInterface.from_dict(data)
        assert info == inf

    @pytest.mark.parametrize('data', [
        pytest.param({'foo': 'bar'}, id='Unexpected field')
    ])
    def test_from_dict_failure(self, data):
        with pytest.raises(errors.InfoError):
            infos.ElectricalInterface.from_dict(data)

    def test_get_port_success(self, inf):
        assert inf.get_port('foo') == inf.ports[0]
        assert inf.get_port('bar') == inf.ports[1]

    def test_get_port_failure(self, inf):
        with pytest.raises(ValueError):
            inf.get_port('baz')
