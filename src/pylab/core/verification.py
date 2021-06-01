# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import abc
import dataclasses
from typing import Optional

import numpy.testing
from numpy.typing import ArrayLike
import yaml

from pylab.core import timeseries
from pylab.core import infos
from pylab.core import utils


@dataclasses.dataclass(frozen=True)
class Check:
    failed: bool = False
    what: Optional[str] = ''


class AbstractAssertion(abc.ABC):

    @abc.abstractmethod
    def deploy(self, results: dict[str, timeseries.TimeSeries]) -> None:
        """Apply assertion to ``results`` and raise on failure.

        Args:
            results:
                A dictionary mapping fully qualified signal names to
                logged data

        Raises:
            AssertionError: If the test fails
        """
        pass


# FIXME The indirection via ``_verify`` may be a bad idea. It is
# entirely possible that an assertion will want to compare two results.
# T
class AbstractVerification(abc.ABC):
    """Represents the verification of a test result."""

    def __init__(self, vars: dict[str]) -> None:
        """Initialize the verification.

        Args:
            vars:   
                ``dict`` mapping verification roles to fully qualified
                signal names
        """
        self._vars = vars

    def deploy(self, results: dict[str, timeseries.TimeSeries]) -> None:
        """Apply assertion to ``results`` and raise on failure.

        Args:
            results:
                A dictionary mapping fully qualified signal names to
                logged data

        Raises:
            AssertionError: If the test fails
        """
        check = self.verify(results)
        if check.failed:
            raise AssertionError(check.what)

    def verify(self, results: dict[str, timeseries.TimeSeries]) -> Check:
        """Apply assertion to ``results``.

        Args:
            results:
                A dictionary mapping fully qualified signal names to
                logged data

        Returns:
            ``(False, None)`` if the assertion succeeded;
            ``(True, what)`` otherwise
        """
        try:
            kwargs = {k: results[v] for k, v in self._vars.items()}
        except KeyError as e:
            return Check(
                failed=True,
                what=f'Result {e} not found\n\nComplete list of results:\n\n{results}'
            )
        return self._verify(**kwargs)

    @abc.abstractmethod
    def _verify(self, **kwargs) -> Check:
        """Apply assertion to ``results``.

        Args: Implementation defined

        Returns:
            ``(False, None)`` if the assertion succeeded;
            ``(True, what)`` otherwise
        """
        pass


def load_info(info: infos.AssertionInfo) -> AbstractVerification:
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
    return type_(**info.data)


class IsEqual(AbstractVerification):

    def __init__(self, result: str, expected: timeseries.TimeSeries) -> None:
        super().__init__({'result': result})
        self._expected = expected

    def _verify(self, result: timeseries.TimeSeries) -> Check:
        # FIXME Add meaningful error message!
        assert self._expected == result


class AlmostEverywhereClose(AbstractVerification):

    def __init__(self,
                 result: str,
                 expected: timeseries.TimeSeries,
                 rtol: float = 1e-05,
                 atol: float = 1e-05) -> None:
        super().__init__({'result': result})
        self._expected = expected
        self._atol = atol
        self._rtol = rtol

    def _verify(self, result: timeseries.TimeSeries) -> Check:
        try:
            timeseries.assert_almost_everywhere_close(
                result, self._expected,
                lower=self._expected.lower, upper=self._expected.upper,
                rtol=self._rtol, atol=self._atol)
        except AssertionError as e:
            return Check(True, str(e))
        return Check()


class IntegralAlmostEqualTo(AbstractVerification):

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

    def _verify(self, result: timeseries.TimeSeries) -> Check:
        try:
            numpy.testing.assert_allclose(
                timeseries.l2norm(result, self._lower, self._upper),
                self._expected, rtol=self._rtol, atol=self._atol)
        except AssertionError as e:
            return Check(True, str(e))
        return Check()


class IsCloseAtTime(AbstractVerification):

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

    def _verify(self, result: timeseries.TimeSeries) -> Check:
        actual = result(self._time)
        try:
            numpy.testing.assert_allclose(
                actual, self._expected,
                rtol=self._rtol, atol=self._atol)
        except AssertionError as e:
            return Check(True, str(e))
        return Check()


class IsEqualAtTime(AbstractVerification):

    def __init__(self, result: str, expected: ArrayLike, time: float) -> None:
        super().__init__({'result': result})
        self._expected = expected
        self._time = time

    def _verify(self, result: timeseries.TimeSeries) -> Check:
        actual = result(self._time)
        if actual != self._expected:
            msg = (f'IsEqualAtTime failed:\n\n'
                   f'actual({self._time}) = {actual}\n'
                   f'expected({self._time}) = {self._expected}')
            return Check(True, msg)
        return Check()


class IsEqualOnce(AbstractVerification):

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

    def _verify(self, result: timeseries.TimeSeries) -> Check:
        for t in [each for each in result.time if self._lo <= each and each <= self._hi]:
            if self._result(t) == self._expected:
                return Check()
        return Check(
            True,
            f'TimeSeries not once equal to {self._expected} on [{self._lo}, {self._hi}]'
        )



