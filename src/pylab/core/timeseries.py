# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Module for timeseries (mainly used to hold logged data) and testing
utilities.
"""

from __future__ import annotations

import bisect
import copy
import sys
from typing import Any, Callable, Optional, Sequence
import yaml

import numpy as np
from numpy.typing import ArrayLike
import scipy.interpolate
import scipy.integrate

from pylab.tools import yamltools


@yamltools.yaml_object
class TimeSeries:
    """Utility class that maps time to values using interpolation."""

    def __init__(self,
                 time: Sequence[float],
                 values: Sequence[ArrayLike],
                 kind: str = 'previous') -> None:
        """Init time series from time and value sequences.

        Args:
            time: Sequence of sample times/breakpoints
            values: Sequence of values
            kind: The type of interpolation.

        Raises:
            ValueError: If ``len(time) != len(values)``.
        """
        if len(time) != len(values):
            raise ValueError(
                'failed to init TimeSeries: len(time) != len(values). '
                'The pylab API states: time and values must always have'
                ' the same length.'  # TODO Add reference to spec
            )
        self._time = np.array(time)
        self._values = np.array(values)
        self._kind = kind
        del time
        del values
        self._f = None
        self._interpolate()

    @property
    def time(self) -> ArrayLike:
        """Array of time points of the time series.

        This property is considered **read-only**.
        """
        return self._time

    @property
    def values(self) -> ArrayLike:
        """Array of data points of the time series.

        This property is considered **read-only**.
        """
        return self._values

    @property
    def kind(self) -> str:
        """The type of interpolation."""
        return self._kind

    @kind.setter
    def kind(self, kind: str) -> None:
        self._kind = kind
        self._interpolate()

    @property
    def lower(self) -> float:
        """Smallest time point of the time series."""
        return self._time[0]

    @property
    def upper(self) -> float:
        """Largest time point of the time series."""
        return self._time[-1]

    def __add__(self, other: TimeSeries) -> TimeSeries:
        result = _subdivision(self, other.time)
        for index, time in enumerate(self._time):
            result._values[index] += other._f(time)
        return result

    def __call__(self, t: float) -> ArrayLike:
        return self._f(t)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, TimeSeries):
            return False
        return (
            np.array_equal(self._time, other._time)
            and np.array_equal(self._values, other._values)
        )

    def __sub__(self, other: TimeSeries) -> TimeSeries:
        result = _subdivision(self, other.time)
        for index, time in enumerate(self._time):
            result._values[index] -= other._f(time)
        return result

    def transform(self, transf: Callable) -> None:
        """Transform the values of the time series.

        Args:
            transf: The transformation
        """
        self._values = np.array([transf(each) for each in self._values])
        self._interpolate()

    def add_breakpoint(self, time: float) -> None:
        """Add a breakpoint using interpolation."""
        if time in self._time:
            return
        index = bisect.bisect_right(self._time, time)
        self._time = np.insert(self._time, index, time)
        self._values = np.insert(self._values, index, self._f(time), 0)
        self._interpolate()

    def shift(self, offset: float) -> None:
        """Shift all time values by ``offset``."""
        self._time = [time + offset for time in self._time]
        self._interpolate()

    def abs(self) -> TimeSeries:
        """Return the time series of absolute values.

        Example:
            >>> ts = TimeSeries([0, 1, 2], [1, -1, 1])
            >>> ts(0.5)
            0.0
            >>> ts.abs()(0.5)
            1.0
        """
        # FIXME Fix the example above!
        result = copy.deepcopy(self)
        result.transform(lambda v: abs(v))
        return result

    def shape(self) -> tuple[int, ...]:
        """Return the shape of the data elements."""
        return self._values.shape[1:]

    def _interpolate(self) -> None:
        self._f = scipy.interpolate.interp1d(
            self._time, self._values, axis=0, copy=True,
            bounds_error=False, fill_value='extrapolate',
            kind=self._kind)


def pretty_print(ts: timeseries.TimeSeries, file=sys.stdout) -> str:
    """Pretty print a time series.

    Args:
        ts: The time series to be printed
        file: The file to print to

    Requires tabulate>=0.8.9.
    """
    from tabulate import tabulate
    data = zip(ts.time, ts.values)
    return str(tabulate(data, headers=['Time', 'Values']), file=file)


def _subdivision(ts: TimeSeries, time: list[float]) -> TimeSeries:
    """Return a subdivision of a timeseries.

    Args:
        ts: Time series to be subdivided
        time: Breakpoints used for divison
    """
    ts = copy.deepcopy(ts)
    for t in time:
        ts.add_breakpoint(t)
    return ts


def zeros(time: list[float], shape: tuple[int, ...]) -> TimeSeries:
    """Create zero time series.

    Args:
        time: The timepoints of the series
        shape: The shape of the (zero) data
    """
    return TimeSeries(time, [np.zeros(shape), np.zeros(shape)])


def l2norm(ts: TimeSeries,
           lower: Optional[float] = None,
           upper: Optional[float] = None) -> ArrayLike:
    """Return the L^2 norm of ``ts``.

    If ``lower`` or ``upper`` are specified, the time series is
    restricted to the interval ``[lower, upper]``.
    """

    if lower is None:
        lower = ts.lower
    if upper is None:
        upper = ts.upper
    result = scipy.integrate.quad_vec(ts, lower, upper)
    vec = result[0]
    return np.linalg.norm(vec)


def l2distance(lhs: TimeSeries,
               rhs: TimeSeries,
               lower: Optional[float] = None,
               upper: Optional[float] = None) -> ArrayLike:
    """Return the L^2 distance between two timeseries.

    If ``lower`` or ``upper`` are specified, the time series is
    restricted to the interval ``[lower, upper]``.
    """
    if lower is None:
        lower = max(lhs.lower, rhs.lower)
    if upper is None:
        upper = min(lhs.upper, rhs.upper)

    def diff(t: float) -> ArrayLike:
        return np.absolute(rhs(t) - lhs(t))
    result = scipy.integrate.quad_vec(diff, lower, upper)
    vec = result[0]
    return np.linalg.norm(vec)


def assert_almost_everywhere_close(actual: TimeSeries,
                                   expected: TimeSeries,
                                   lower: float = None,
                                   upper: float = None,
                                   rtol: float = 1e-07,
                                   atol: float = 1e-07) -> None:
    """Raise an ``AssertionError`` is two time series are not equal up to tolerance in L^2 space.

    Args:
        actual: The time series under test
        expected: The expected time series
        rtol: Relative tolerance
        atol: Absolute tolerance
    """
    dist = l2distance(actual, expected, lower, upper)
    norm = l2norm(expected, lower, upper)
    if dist <= atol + rtol * norm:
        return

    # TODO Advanced diagnostics, checking for areas with large
    # deviation.

    raise AssertionError(
        f'Time series not almost everywhere close '
        f'(rtol={rtol}, atol={atol}):\n'
        f'\n'
        f'actual =   {actual}\n\n'
        f'expected = {expected}\n\n'
        f'dist =     {dist}')


def assert_close(actual: TimeSeries,
                 expected: TimeSeries,
                 lower: float = None,
                 upper: float = None,
                 rtol: float = 1e-07, atol: float = 1e-07) -> None:
    """Raise an ``AssertionError`` is two time series are not equal up
    to tolerance in C^0 space.

    Args:
        actual: The time series under test
        expected: The expected time series
        rtol: Relative tolerance
        atol: Absolute tolerance
    """

    # FIXME
    #
    # dist = c0distance(actual, expected, lower, upper)
    # norm = c0norm(expected, lower, upper)
    # if dist <= atol + rtol*norm:
    #     return

    # raise AssertionError(
    #     f'Time series not almost everywhere close '
    #     f'(rtol={rtol}, atol={atol}):\n'
    #     f'\n'
    #     f'actual =   {actual}\n\n'
    #     f'expected = {expected}\n\n'
    #     f'dist =     {dist}')
