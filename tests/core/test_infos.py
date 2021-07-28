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
        with pytest.raises(infos.InfoError):
            infos.TestInfo(targets, logging, phases)


class TestCommandInfo:

    def test_failure(self):
        with pytest.raises(infos.NegativeTimeError):
            infos.CommandInfo(time=-0.1, command='foo', target='bar')


class TestPhaseInfo:

    @pytest.mark.parametrize('duration, commands', [
        pytest.param(
            -0.3, [],
            id='Negative duration'
        ),
    ])
    def test_failure_due_to_negative_duration(self, duration, commands):
        with pytest.raises(infos.NegativeTimeError):
            infos.PhaseInfo(duration=duration, commands=commands)

    @pytest.mark.parametrize('duration, commands', [
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
    def test_failure_due_to_late_execution(self, duration, commands):
        with pytest.raises(infos.CommandTooLateError):
            infos.PhaseInfo(duration=duration, commands=commands)

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
        with pytest.raises(infos.InfoError):
            infos.PhaseInfo.from_dict(data)


class TestLoggingInfo:

    @pytest.mark.parametrize('period, kind', [
        pytest.param('foo', 'next', id='wrong period type'),
        pytest.param(-1.23, 'next', id='negative period'),
        pytest.param(0.0, 'next', id='zero period'),
        pytest.param(1.23, 'foo', id='unknown kind')
    ])
    def test_failure(self, period, kind):
        with pytest.raises(infos.InfoError):
            infos.LoggingInfo('foo', 'bar', period, kind)


class TestSignalInfo:

    @pytest.mark.parametrize('kwargs, expected', [
        pytest.param(
            {'name': 'foo', 'min': 1.2, 'max': 3.4},
            infos.SignalInfo(name='foo', min=1.2, max=3.4),
            id='Using min/max'
        ),
        pytest.param(
            {'name': 'bar', 'range': '1.2..3.4'},
            infos.SignalInfo(name='bar', min=1.2, max=3.4),
            id='Using range'
        )
    ])
    def test__init__success(self, kwargs, expected):
        info = infos.SignalInfo(**kwargs)
        assert info == expected

    @pytest.mark.parametrize('kwargs', [
        pytest.param(
            {'name': 'foo.bar', 'min': 1.0, 'max': 2.0},
            id='Invalid id'
        ),
        pytest.param(
            {'name': 'foo', 'min': 1.2, 'range': '1.2..3.4'},
            id='range and in specified'
        ),
        pytest.param(
            {'name': 'bar', 'max': 234, 'range': '1.2.0..3.4'},
            id='range and max specified'
        ),
        pytest.param(
            {'name': 'bar', 'min': 1.2, 'max': 234, 'range': '1.2.0..3.4'},
            id='range and min/max specified'
        ),
        pytest.param(
            {'name': 'foo', 'min': 1.2},
            id='No max specified'
        ),
        pytest.param(
            {'name': 'foo', 'max': 3.4},
            id='No min specified'
        ),
        pytest.param(
            {'name': 'foo', 'min': 1.2},
            id='No min specified'
        ),
        pytest.param(
            {'name': 'foo', 'min': 3.4, 'max': 1.2},
            id='min > max'
        ),
        pytest.param(
            {'name': 'bar'},
            id='No range specified'
        ),
    ])
    def test__init__failure(self, kwargs):
        with pytest.raises(infos.InfoError):
            infos.SignalInfo(**kwargs)


class TestTargetInfo:

    @pytest.mark.parametrize('name, signals', [
        pytest.param(
            'foo.bar', [],
            id='Invalid id'
        ),
        pytest.param(
            'foo',
            [
                infos.SignalInfo(name='bar', min=0, max=1),
                infos.SignalInfo(name='bar', min=1, max=2),
            ],
            id='Duplicate signal id'
        )
    ])
    def test_failure(self, name, signals):
        with pytest.raises(infos.InfoError):
            infos.TargetInfo(name, signals)

    def test_from_dict(self):
        data = {
            'name': 'foo',
            'signals': [
                {'name': 'bar', 'min': 1.2, 'max': 3.4},
                {'name': 'baz', 'min': 0, 'max': 1.2},
            ],
            'description': 'foobar'
        }
        info = infos.TargetInfo.from_dict(data)
        expected = infos.TargetInfo(
            name='foo',
            signals=[
                infos.SignalInfo(name='bar', min=1.2, max=3.4),
                infos.SignalInfo(name='baz', min=0, max=1.2),
            ],
            description='foobar'
        )
        assert info == expected

    @pytest.mark.parametrize('data', [
        pytest.param({}, id='Missing name'),
        pytest.param({'name': 'foo', 'foo': 'bar'}, id='Unexpected field')
    ])
    def test_from_dict_failure(self, data):
        with pytest.raises(infos.InfoError):
            infos.TargetInfo.from_dict(data)
