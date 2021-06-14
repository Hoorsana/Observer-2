# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import abc
import dataclasses
import inspect
from typing import Optional

import numpy.testing
from numpy.typing import ArrayLike
import yaml

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
    what: str = ''

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
    if '.' in info.type:
        type_ = utils.module_getattr(info.type)
    else:  # No absolute path specified, use local block module!
        type_ = globals()[info.type]
    return type_.wrap_in_dispatcher(info.data, info.args)


class BaseAssertion(AbstractAssertion):
    """Convenience ABC which handles access to the results."""

    @classmethod
    def wrap_in_dispatcher(cls, data: dict[str, Any],
                           args: dict[str, str]) -> Dispatcher:
        a = cls(**data)
        return Dispatcher(a, args)

    def assert_(self, *args, **kwargs) -> Result:
        result = self.apply(*args, **kwargs)
        result.throw_if_failed()


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
    def wrap_in_dispatcher(cls, *args, **kwargs) -> None:
        raise NotImplementedError()

    def apply(self, results: dict[str, Any]) -> Result:
        try:
            kwargs = {k: results[v] for k, v in self._args}
        except KeyError as e:
            return Result.from_error(e)
        return self._assertion.apply(**kwargs)


class Equal(BaseAssertion):

    def __init__(self, expected: _T) -> None:
        self._expected = expected

    def apply(self, actual: _T) -> Result:
        return Result(
            self._expected == result,
            f'{actual} not equal to expected {expected}'
        )


class TimeseriesAlmostEqual(BaseAssertion):

    def __init__(self, expected: timeseries.TimeSeries,
                 rtol: float = 1e-05, atol: float = 1e-05) -> None:
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
                atol=self._atol)
        except AssertionError as e:
            return Result.from_error(e)
        return Result()


class CloseAtTime(BaseAssertion):

    def __init__(self, expected: ArrayLike, time: float,
                 rtol: float = 1e-05, atol: float = 1e-05) -> None:
        self._expected = expected
        self._time = time
        self._rtol = rtol
        self._atol = atol

    def apply(self, actual: timeseries.TimeSeries) -> Result:
        value = result(self._time)
        try:
            numpy.testing.assert_allclose(
                value, self._expected, rtol=self._rtol, atol=self._atol)
        except AssertionError as e:
            return Result.from_error(e)
        return Result()


class EqualOnce(BaseAssertion):

    def __init__(self, expected: ArrayLike, lo: float, hi: float) -> None:
        self._expected = expected
        self._lo = lo
        self._hi = hi

    def apply(self, ts: timeseries.TimeSeries) -> Result:
        hits = [t for t in ts.time
                if self._lo <= t and t <= self._hi
                and self._result(t) == self._expected]
        return Result(
            bool(hits),
            f'TimeSeries not once equal to {self._expected} on [{self._lo}, {self._hi}]'
        )
