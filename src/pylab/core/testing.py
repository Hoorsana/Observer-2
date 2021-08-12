# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import abc
import dataclasses
import inspect
from typing import Optional

import numpy.testing
import yaml

from pylab.core.typing import ArrayLike
from pylab.core import timeseries
from pylab.core import infos
from pylab.core import utils


@dataclasses.dataclass(frozen=True)
class Result:
    """Stores the result of an assertion.

    Attributes:
        success: Indicates truth or falsehood of the assertion
        what:
            Error message if assertion failed (may be left untouched if
            ``succcess`` is ``True``)

    Default value are chosen so that ``Result()`` indicates
    success.
    """

    success: bool = True
    what: str = ""

    def __str__(self):
        return self.what

    @classmethod
    def from_error(cls, e: BaseException) -> Result:
        return Result(False, str(e))

    @property
    def failed(self) -> bool:
        return not self.success

    def throw_if_failed(self) -> None:
        """Raise an ``AssertionError`` if the assertion is wrong.

        Raises:
            AssertionError: If the assertion is wrong
        """
        if self.failed:
            raise AssertionError(self.what)


class AbstractAssertion(abc.ABC):
    """Abstract base class for assertions.

    In addition to the requirements of the API specified below, it is
    also required that `assert_` and `apply` have the same `*args` and
    `**kwargs`.
    """

    @abc.abstractmethod
    def assert_(self, *args, **kwargs) -> None:
        """Apply assertion to ``results`` and raise on failure.

        Raises:
            AssertionError: If the assertion fails

        **Note.** `assert_` does **not** modify the arguments passed to it.
        """
        pass

    @abc.abstractmethod
    def apply(self, *args, **kwargs) -> Result:
        """Apply assertion to ``results``.

        Returns:
            The result of the assertion

        **Note.** `apply` does **not** modify the arguments passed to it.
        """
        pass


def load_info(info: infos.AssertionInfo) -> list[Dispatcher]:
    """Create an assertion from info.

    Returns:
        The loaded assertions, wrapped into `Dispatcher` objects

    Raises:
        ModuleNotFoundError:
            If the module speicified by ``info.type`` doesn't exist
        AttributeError: If module doesn't have the specified attribute
    """
    # FIXME code-duplication: simulink.simulink.Device.from_details
    if "." in info.type:
        type_ = utils.module_getattr(info.type)
    else:  # No absolute path specified, use local block module!
        type_ = globals()[info.type]
    return type_.create_with_dispatcher(info.data, info.args)


class BaseAssertion(AbstractAssertion):
    """Convenience ABC which handles access to the results."""

    @classmethod
    def create_with_dispatcher(
        cls, data: dict[str, Any], args: dict[str, str]
    ) -> Dispatcher:
        a = cls(**data)
        return Dispatcher(a, args)

    def assert_(self, *args, **kwargs) -> Result:
        result = self.apply(*args, **kwargs)
        result.throw_if_failed()

    def wrap_in_dispatcher(self, args: dict[str, str]) -> Dispatcher:
        return Dispatcher(self, args)

    def wrapped_in_dispatcher(self, args: dict[str, str]) -> Dispatcher:
        a = copy.deepcopy(self)
        return a.wrap_in_dispatcher(args)


class Dispatcher(BaseAssertion):
    """Convenience class which unpacks the ``results`` dict of a
    ``Report`` object and applies the assertion to the data of
    previously specified items of the dict.
    """

    def __init__(self, assertion: AbstractAssertion, args: dict[str, str]) -> None:
        """Args:
        assertion: The wrapped assertion
        args:
            ``dict`` that maps parameter names of
            ``assertion.assert_`` and ``assertion.apply`` to the
            fully qualified name of the signals to which the
            assertion is to be applied
        """
        self._assertion = assertion
        self._args = args

    @classmethod
    def create_with_dispatcher(cls, *args, **kwargs) -> None:
        raise NotImplementedError()

    def apply(self, results: dict[str, Any]) -> Result:
        try:
            kwargs = {k: results[v] for k, v in self._args.items()}
        except KeyError as e:
            return Result.from_error(e)
        return self._assertion.apply(**kwargs)


class Equal(BaseAssertion):
    """Assertion for _exact_ equality implemented by ``__eq__``."""

    def __init__(self, expected: Any) -> None:
        """Args:
        expected: The expected value
        """
        self._expected = expected

    def apply(self, actual: Any) -> Result:
        """Args:
        actual: The actual result
        """
        return Result(
            self._expected == result, f"{actual} not equal to expected {expected}"
        )


class TimeseriesAlmostEqual(BaseAssertion):
    """Assert that two time series are almost everywhere close.

    The assertion succeeds if the following is true: Take the absolute
    difference of the expected time series f and the actual time
    series g (as functions) and integrate the result over the domain
    [a, b] of the _expected_ time series, then compare that result to
    the absolute integral of the expected time series:

    \\int_a^b |f - g| dt < t_{rel} \\cdot \\int_a^b |f| dt + t_{abs}

    Note that if the domain of integration exceeds the bounds of the
    domain of g, then the values of g are extrapolated using the
    interpolation/extrapolation kind provided by the underlying time
    series.
    """

    def __init__(
        self, expected: timeseries.TimeSeries, rtol: float = 1e-05, atol: float = 1e-05
    ) -> None:
        """Args:
        expected: The expected time series
        rtol: The relative tolerance
        atol: The absolute tolerance
        """
        self._expected = expected
        self._expected = expected
        self._atol = atol
        self._rtol = rtol

    def apply(self, actual: timeseries.TimeSeries) -> Result:
        try:
            timeseries.assert_almost_everywhere_close(
                actual,
                self._expected,
                lower=self._expected.lower,
                upper=self._expected.upper,
                rtol=self._rtol,
                atol=self._atol,
            )
        except AssertionError as e:
            return Result.from_error(e)
        return Result()


class TimeseriesIntegralAlmostEqual(BaseAssertion):
    """Assert that the integral of a time series over a certain domain
    is almost equal to an expected value:

    \\int_l^u actual dt < t_{rel} \\cdot expected + t_{abs}
    """

    def __init__(
        self,
        expected: float,
        rtol: float = 1e-05,
        atol: float = 1e-05,
        lower: Optional[float] = None,
        upper: Optional[float] = None,
    ) -> None:
        """Args:
        expected: The expected value
        rtol: The relative tolerance
        atol: The absolute Tolerance
        lower: The lower bound of the domain of integration
        upper: The upper bound of the domain of integration
        """
        self._expected = expected
        self._atol = atol
        self._rtol = rtol
        self._lower = lower
        self._upper = upper

    def apply(self, actual: timeseries.TimeSeries) -> Check:
        try:
            numpy.testing.assert_allclose(
                timeseries.l2norm(actual, self._lower, self._upper),
                self._expected,
                rtol=self._rtol,
                atol=self._atol,
            )
        except AssertionError as e:
            return Result.from_error(e)
        return Result()


class CloseAtTime(BaseAssertion):
    """Assert that the value of a time series at a specified time is
    close to an expected value:

    |expected(t_0) - actual(t_0)| < t_{rel} \\cdot expected(t_0) + t_{abs}
    """

    def __init__(
        self, expected: ArrayLike, time: float, rtol: float = 1e-05, atol: float = 1e-05
    ) -> None:
        """Args:
        expected: The expected value
        time: The time of comparison
        rtol: The relative tolerance
        atol: The absolute tolerance
        """
        self._expected = expected
        self._time = time
        self._rtol = rtol
        self._atol = atol

    def apply(self, actual: timeseries.TimeSeries) -> Result:
        value = result(self._time)
        try:
            numpy.testing.assert_allclose(
                value, self._expected, rtol=self._rtol, atol=self._atol
            )
        except AssertionError as e:
            return Result.from_error(e)
        return Result()


class EqualAtLeastOnce(BaseAssertion):
    """Assert that a timeseries assumes a certain value at least once."""

    def __init__(
        self,
        expected: ArrayLike,
        lower: Optional[flowerat] = None,
        upper: Optional[flowerat] = None,
    ) -> None:
        self._expected = expected
        self._lower = lower
        self._upper = upper

    def apply(self, ts: timeseries.TimeSeries) -> Result:
        if self._lower is None:
            lower = self._lower
        else:
            lower = ts.lower
        if self._upper is None:
            upper = self.upper
        else:
            upper = ts.upper
        hits = [
            t for t in ts.time if lower <= t and t <= upper and ts(t) == self._expected
        ]
        return Result(
            bool(hits),
            f"TimeSeries not at least once equal to {self._expected} on [{self._lower}, {self._upper}]",
        )
