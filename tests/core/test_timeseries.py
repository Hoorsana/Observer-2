# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

import numpy as np
import numpy.testing
import yaml

from pylab.core import timeseries


@pytest.mark.parametrize(
    "data, expected",
    [
        (
            """
        !TimeSeries
        time: [0, 1, 2]
        values: [3, 4, 5]
        kind: linear
        """,
            timeseries.TimeSeries([0, 1, 2], [3, 4, 5], kind="linear"),
        ),
        (
            """
        !TimeSeries
        time: [-3, -2, -1]
        values: [[3, 4, 5], [6, 7, 8], [9, 0, 1]]
        """,
            timeseries.TimeSeries([-3, -2, -1], [[3, 4, 5], [6, 7, 8], [9, 0, 1]]),
        ),
    ],
)
def test_load_timeseries(data, expected):
    result = yaml.safe_load(data)
    assert result == expected


class TestTimeSeries:
    @pytest.mark.parametrize(
        "lhs, rhs, expected",
        [
            (
                timeseries.TimeSeries([0, 1, 2], [2, 4, 8]),
                timeseries.TimeSeries([0, 1, 2], [2, 4, 8]),
                True,
            ),
            (
                timeseries.TimeSeries([0, 1, 2], [2, 4, 8]),
                timeseries.TimeSeries([0, 1, 2], [2, 4, 7]),
                False,
            ),
            (
                timeseries.TimeSeries([0, 1, 3], [2, 4, 8]),
                timeseries.TimeSeries([0, 1, 2], [2, 4, 8]),
                False,
            ),
            (
                timeseries.TimeSeries([0, 1, 2, 3], [2, 4, 8, 16]),
                timeseries.TimeSeries([0, 1, 2], [2, 4, 8]),
                False,
            ),
        ],
    )
    def test__eq__(self, lhs, rhs, expected):
        assert (lhs == rhs) == expected

    def test_transform(self):
        ts = timeseries.TimeSeries([0, 1, 2, 3], [-2, 3, 2, -4], kind="linear")
        ts.transform(lambda v: -v)
        assert ts(1) == -3
        assert ts(2.5) == 1  # Check that after transforming, the ts is interpolated.

    @pytest.mark.parametrize(
        "ts, time, expected",
        [
            pytest.param(
                timeseries.TimeSeries([0, 1, 3], [-2, 3, 1], kind="linear"),
                2,
                timeseries.TimeSeries([0, 1, 2, 3], [-2, 3, 2, 1], kind="linear"),
            ),
            pytest.param(
                timeseries.TimeSeries(
                    [0, 1, 2], [[0, 1], [2, 3], [4, 5]], kind="linear"
                ),
                -1,
                timeseries.TimeSeries(
                    [-1, 0, 1, 2], [[-2, -1], [0, 1], [2, 3], [4, 5]], kind="linear"
                ),
            ),
            pytest.param(
                timeseries.TimeSeries(
                    [-3, -2, 0],
                    [
                        [[2.0, 3.0, 2.0], [1.5, 0.5, 3.33]],
                        [[1, 2, 0], [4, 1, -2]],
                        [[5, 4, 9], [4, 2, 1]],
                    ],
                    kind="linear",
                ),
                -1,
                timeseries.TimeSeries(
                    [-3, -2, -1, 0],
                    [
                        [[2.0, 3.0, 2.0], [1.5, 0.5, 3.33]],
                        [[1, 2, 0], [4, 1, -2]],
                        [[3, 3, 4.5], [4, 1.5, -0.5]],
                        [[5, 4, 9], [4, 2, 1]],
                    ],
                    kind="linear",
                ),
            ),
        ],
    )
    def test_add_breakpoint(self, ts, time, expected):
        ts.add_breakpoint(time)
        assert ts == expected

    @pytest.mark.parametrize(
        "ts, expected",
        [
            pytest.param(
                timeseries.TimeSeries([0, 1, 2], [4, 5, 6]),
                timeseries.TimeSeries([0, 1, 2], [4, 5, 6]),
                id="positive",
            ),
            pytest.param(
                timeseries.TimeSeries([0, 1, 2], [-4, -5, -6]),
                timeseries.TimeSeries([0, 1, 2], [4, 5, 6]),
                id="negative",
            ),
            pytest.param(
                timeseries.TimeSeries([0, 1, 2], [2, -2, 2]),
                timeseries.TimeSeries([0, 0.5, 1, 1.5, 2], [2, 0, 2, 0, 2]),
                id="dip",
                marks=pytest.mark.xfail,
            ),
        ],
    )
    def test_abs(self, ts, expected):
        assert ts.abs() == expected

    @pytest.mark.parametrize(
        "ts, expected",
        [
            pytest.param(timeseries.TimeSeries([0, 1, 2], [[2.0], [3.5], [5.1]]), (1,)),
            pytest.param(
                timeseries.TimeSeries(
                    [-3, -2, -1], [[2.0, 3.0, 1.5], [3.5, 2.0, 1.0], [5.1, 4.3, 2.3]]
                ),
                (3,),
            ),
            pytest.param(
                timeseries.TimeSeries(
                    [-3, -2, -1],
                    [
                        [[2.0, 3.0, 2.0], [1.5, 0.5, 3.33]],
                        [[3.5, 2.0, 0.0], [4.0, 1.0, -2.3]],
                        [[5.1, 4.3, 9.9], [4, 2.3, 1.1111]],
                    ],
                ),
                (2, 3),
            ),
        ],
    )
    def test_shape(self, ts, expected):
        assert ts.shape() == expected


@pytest.mark.parametrize(
    "lhs, rhs, expected",
    [
        (
            timeseries.TimeSeries([0.0, 1.0, 2.0], [1.0, 2.0, 3.0], kind="linear"),
            timeseries.TimeSeries([0.0, 1.0, 2.0], [4.0, 5.0, 6.0], kind="linear"),
            6.0,
        ),
        (
            timeseries.TimeSeries(
                [0.0, 1.0, 2.0], [[0.0, 1.0], [1.0, 0.0], [0.0, 2.0]], kind="linear"
            ),
            timeseries.TimeSeries(
                [0.0, 1.0, 2.0], [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]], kind="linear"
            ),
            np.sqrt(2.0),
        ),
        (
            timeseries.TimeSeries(
                [0.0, 1.0, 2.0],
                [
                    [[0.0, 0.0], [1.0, 1.0]],
                    [[0.0, 1.0], [1.0, 2.0]],
                    [[3.0, 4.0], [3.0, 3.0]],
                ],
                kind="linear",
            ),
            timeseries.TimeSeries(
                [0.0, 1.0, 2.0],
                [
                    [[0.0, 0.0], [1.0, 1.0]],
                    [[0.0, 1.0], [1.0, 2.0]],
                    [[1.0, 4.0], [3.0, 3.0]],
                ],
                kind="linear",
            ),
            1.0,
        ),
    ],
)
def test_l2distance(lhs, rhs, expected):
    np.testing.assert_allclose(timeseries.l2distance(lhs, rhs), expected)


@pytest.mark.parametrize(
    "lhs, rhs",
    [
        (
            timeseries.TimeSeries([0.0, 1.0], [2.0, 3.0]),
            timeseries.TimeSeries([0.0, 1.0], [2.0, 3.0]),
        ),
        (
            timeseries.TimeSeries([0.0, 1.0], [2.0, 3.1]),
            timeseries.TimeSeries([0.0, 1.0], [2.0, 3.0]),
        ),
    ],
)
def test_assert_almost_everywhere_close_success(lhs, rhs):
    timeseries.assert_almost_everywhere_close(lhs, rhs, atol=0.1, rtol=0.1)


@pytest.mark.parametrize(
    "lhs, rhs",
    [
        (
            timeseries.TimeSeries([0.0, 1.0], [2.0, 3.0], kind="linear"),
            timeseries.TimeSeries([0.0, 1.0], [2.0, 5.0], kind="linear"),
        ),
    ],
)
def test_assert_almost_everywhere_close_failure(lhs, rhs):
    with pytest.raises(AssertionError):
        timeseries.assert_almost_everywhere_close(lhs, rhs, atol=0.1, rtol=0.1)
