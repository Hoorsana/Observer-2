# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from pylab.core import testing
from pylab.core import loader
from pylab.core import infos
from pylab.core import timeseries


def test_load_test():
    test = loader.load_test('resources/tests/core/loader/load_test.yml')

    targets = [
        infos.TargetInfo(
            name='system_under_test',
            signals=[
                infos.SignalInfo(
                    name='temp1',
                    flags=['input'],
                    min=0, max=100,
                    description='bla bla bla'
                ),
                infos.SignalInfo(
                    name='temp2',
                    flags=['input'],
                    min=0, max=100,
                    description='bla bla bla'
                ),
                infos.SignalInfo(
                    name='sum',
                    flags=['output'],
                    min=0, max=200,
                    description='lalala'
                ),
            ]
        )
    ]
    assert test.targets == targets
    logging = [infos.LoggingInfo(target='system_under_test',
                                 signal='sum',
                                 period=0.5)]
    assert test.logging == logging
    phase = infos.PhaseInfo(
        description='Set some values...',
        duration=2.0,
        commands=[
            infos.CommandInfo(
                time=0.0,
                command='CmdSetSignal',
                target='system_under_test',
                data={'signal': 'temp1', 'value': 2.0}
            ),
            infos.CommandInfo(
                time=0.0,
                command='CmdSetSignal',
                target='system_under_test',
                data={'signal': 'temp2', 'value': 3.0}
            ),
            infos.CommandInfo(
                time=1.0,
                command='CmdSetSignal',
                target='system_under_test',
                data={'signal': 'temp2', 'value': 0.0}
            ),
        ]
    )
    assert test.phases == [phase, phase]


def test_load_asserts():
    asserts = loader.load_asserts('resources/tests/core/loader/asserts.yml')
    assert len(asserts) == 2
    [is_equal, almost_equal] = asserts
    assert type(is_equal._assertion) == testing.Equal
    assert type(almost_equal._assertion) == testing.TimeseriesAlmostEqual
    assert is_equal._assertion._expected == 1.23
    assert almost_equal._assertion._expected == timeseries.TimeSeries([-2, -1, 0, 1, 2], [[4], [1], [0], [1], [4]])
