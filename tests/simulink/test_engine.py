# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

import numpy.testing

from pylab.core import timeseries
from pylab.simulink import _engine

@pytest.fixture(scope='session')
def simulation():
    return _engine.engine().sim('test_engine')


@pytest.mark.slow
@pytest.mark.dependency('simulink')
@pytest.mark.parametrize('var, expected0, expected1', [
    pytest.param('scal', 1.2, 3.4),
    pytest.param('vec', [1.2, 3.4], [5.6, 7.8]),
    pytest.param('mat', [[1.2, 3.4, 5.6], [7.8, 9.0, 1.2]], [[3.4, 5.6, 7.8], [9.0, 1.2, 3.4]])
])
def test_timeseries_to_python(var, expected0, expected1, simulation):
    obj = _engine.get_field(simulation, var)
    ts = _engine.timeseries_to_python(obj)
    numpy.testing.assert_array_equal(ts.time, [0.0, 1.0])
    numpy.testing.assert_array_equal(ts(0.0), expected0)
    numpy.testing.assert_array_equal(ts(1.0), expected1)


@pytest.mark.parametrize('time, data, expected', [
    (
        [[0], [1], [2]],
        [[2], [4], [8]],
        timeseries.TimeSeries([0, 1, 2], [[2], [4], [8]])
    ),
    (
        [[0], [1], [2]],
        [[2, 3, 4], [4, 6, 8], [8, 16, 32]],
        timeseries.TimeSeries(
            [0, 1, 2],
            [[2, 3, 4], [4, 6, 8], [8, 16, 32]]
        )
    ),
    (
        [[0], [1], [2]],
        [[[2, 7, 8], [3, 8, 1]], [[5, 9, 2], [6, 0, 5]]],
        timeseries.TimeSeries(
            [0, 1, 2],
            [
                [[2, 3],
                 [5, 6]],
                [[7, 8],
                 [9, 0]],
                [[8, 1],
                 [2, 5]]
            ]
        )
    ),
])
def test__timeseries_to_python(time, data, expected):
    result = _engine._timeseries_to_python(time, data)
    assert result == expected
