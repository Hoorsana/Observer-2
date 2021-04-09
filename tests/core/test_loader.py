# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from pylab.core import loader
from pylab.core import infos
from pylab.core import timeseries


def test_load_test():
    test = loader.load_test('resources/tests/test.yml')

    targets = [
        infos.TargetInfo(
            name='system_under_test',
            signals=[
                infos.SignalInfo(
                    name='temp1',
                    flags=['input'],
                    min=0, max=100,
                    description='bla bla bla'),
                infos.SignalInfo(
                    name='temp2',
                    flags=['input'],
                    min=0, max=100,
                    description='bla bla bla'),
                infos.SignalInfo(
                    name='sum',
                    flags=['output'],
                    min=0, max=200,
                    description='lalala')
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
                data={'signal': 'temp1', 'value': 2.0}),
            infos.CommandInfo(
                time=0.0,
                command='CmdSetSignal',
                target='system_under_test',
                data={'signal': 'temp2', 'value': 3.0}),
            infos.CommandInfo(
                time=1.0,
                command='CmdSetSignal',
                target='system_under_test',
                data={'signal': 'temp2', 'value': 0.0}),
        ])
    assert test.phases == [phase, phase]


class _Assert:

    def __init__(self, value):
        self.value = value


def test_load_asserts(mocker):
    content = """
- type: IsEqual
  data:
    result: output
    expected:
      !TimeSeries
      time: [-2, -1, 0, 1, 2]
      values: [[4], [1], [0], [1], [4]]
    """
    mocker.patch('builtins.open', mocker.mock_open(read_data=content))
    result = loader.load_asserts('/path/to/asserts')
    open.assert_called_once_with('/path/to/asserts', 'r')
    open().read.assert_called_once()
    assert result[0]._expected == timeseries.TimeSeries([-2, -1, 0, 1, 2], [[4], [1], [0], [1], [4]])
