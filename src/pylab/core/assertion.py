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
class AssertionResult:
    success: bool = True
    what: str = ''

    @property
    def failed(self):
        return not self.success

    def throw_if_failed(self):
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
    def apply(self, *args, **kwargs) -> AssertionResult:
        """Apply assertion to ``results``.

        Returns:
            The result of the assertion

        **Note.** `apply` does **not** modify the arguments passed to it.
        """
        pass


def load_info(info: infos.AssertionInfo) -> AbstractAssertion:
    """Create an assertion from info.

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
    def wrap_in_dispatcher(cls, *args, **kwargs, vars: dict[str, str] = None) -> AssertOnReport:
        a = cls(*args, **kwargs)
        return Dispatcher(a, vars)

    def assert_(self, *args, **kwargs) -> None:
        result = self.apply(*args, **kwargs)
        result.throw_if_failed()

    def apply(self, *args, **kwargs) -> AssertionResult:
        pass


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

    def apply(self, results: dict[str, timeseries.TimeSeries]) -> AssertionResult:
        try:
            kwargs = {k: results[v] for k, v in self._args}
        except KeyError as e:
            return AssertionResult(True, str(e))
        return self._assertion.apply(**kwargs)


class IsEqual(BaseAssertion):

    def __init__(self, expected: _T) -> None:
        super().__init__()
        self._expected = expected

    def apply(self, actual: _T) -> AssertionResult:
        # FIXME Add meaningful error message!
        return self._expected == result, f'{actual} not equal to expected {expected}'


class AlmostEverywhereClose(BaseAssertion):

    def __init__(self,
                 result: str,
                 expected: timeseries.TimeSeries,
                 rtol: float = 1e-05,
                 atol: float = 1e-05) -> None:
        super().__init__({'result': result})
        self._expected = expected
        self._atol = atol
        self._rtol = rtol

    def _verify(self, result: timeseries.TimeSeries) -> AssertionResult:
        try:
            timeseries.assert_almost_everywhere_close(
                result, self._expected,
                lower=self._expected.lower, upper=self._expected.upper,
                rtol=self._rtol, atol=self._atol)
        except AssertionError as e:
            return AssertionResult(True, str(e))
        return AssertionResult()


class IntegralAlmostEqualTo(BaseAssertion):

    def __init__(self,
                 result: str,
                 expected: float,
                 rtol: float = 1e-05,
                 atol: float = 1e-05,
                 lower: Optional[float] = None,
                 upper: Optional[float] = None) -> None:
        super().__init__({'result': result})
        self._expected = expected
        self._atol = atol
        self._rtol = rtol
        self._lower = lower
        self._upper = upper

    def _verify(self, result: timeseries.TimeSeries) -> AssertionResult:
        try:
            numpy.testing.assert_allclose(
                timeseries.l2norm(result, self._lower, self._upper),
                self._expected, rtol=self._rtol, atol=self._atol)
        except AssertionError as e:
            return AssertionResult(True, str(e))
        return AssertionResult()


class IsCloseAtTime(BaseAssertion):

    def __init__(self,
                 result: str,
                 expected: ArrayLike,
                 time: float,
                 rtol: float = 1e-05,
                 atol: float = 1e-05) -> None:
        super().__init__({'result': result})
        self._expected = expected
        self._time = time
        self._rtol = rtol
        self._atol = atol

    def _verify(self, result: timeseries.TimeSeries) -> AssertionResult:
        actual = result(self._time)
        try:
            numpy.testing.assert_allclose(
                actual, self._expected,
                rtol=self._rtol, atol=self._atol)
        except AssertionError as e:
            return AssertionResult(True, str(e))
        return AssertionResult()


class IsEqualAtTime(BaseAssertion):

    def __init__(self, result: str, expected: ArrayLike, time: float) -> None:
        super().__init__({'result': result})
        self._expected = expected
        self._time = time

    def _verify(self, result: timeseries.TimeSeries) -> AssertionResult:
        actual = result(self._time)
        if actual != self._expected:
            msg = (f'IsEqualAtTime failed:\n\n'
                   f'actual({self._time}) = {actual}\n'
                   f'expected({self._time}) = {self._expected}')
            return AssertionResult(True, msg)
        return AssertionResult()


class IsEqualOnce(BaseAssertion):

    def __init__(self,
                 result: str,
                 expected: ArrayLike,
                 lo: float,
                 hi: float) -> None:
        super().__init__({'result': result})
        self._result = result
        self._expected = expected
        self._lo = lo
        self._hi = hi

    def _verify(self, result: timeseries.TimeSeries) -> AssertionResult:
        for t in [each for each in result.time if self._lo <= each and each <= self._hi]:
            if self._result(t) == self._expected:
                return AssertionResult()
        return AssertionResult(
            True,
            f'TimeSeries not once equal to {self._expected} on [{self._lo}, {self._hi}]'
        )



