# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from pylab.core import timeseries
from pylab.simulink import _engine


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
