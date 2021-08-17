# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Wrapper module for Mathwork's MATLAB engine.

Typical usage:

    >>> from pylab.simulink import _engine
    >>> engine = _engine.engine()
    >>> engine.[MATLAB/Simulink command]()

In the documentation of this module, by the _handle_ of an object, we
shall always mean the MATLAB/Simulink handle (type ``float``), unless
stated otherwise. Furthermore, we shall identify an objects handle with
the object itself in an attempt to prevent excessive use of phrases like
"the model with handle ``model``".
"""

from __future__ import annotations

import abc
import importlib
import itertools
import io
import sys
from typing import Any, Callable, Optional, Sequence

import matlab

from pylab.core.typing import ArrayLike
from pylab.core import timeseries


class _MonkeypatchPythonVersion:
    """Context manager to force the engine to use the current version by
    monkeypatching sys.version_info if the current python version is not
    supported by MATLAB.
    """

    PYTHON_VERSION_FOR_MATLAB_ENGINE = (3, 7)

    def __enter__(self):
        self._stash = sys.version_info
        sys.version_info = _MonkeypatchPythonVersion.PYTHON_VERSION_FOR_MATLAB_ENGINE

    def __exit__(self, type, value, traceback):
        del type, value, traceback
        sys.version_info = self._stash


def import_matlab_engine():
    try:
        return importlib.import_module("matlab.engine")
    except OSError as e:
        try:
            with _MonkeypatchPythonVersion():
                return importlib.import_module("matlab.engine")
        except OSError:
            raise EnvironmentError from e


class _Cached:
    def __init__(self, f: Callable[[], _T]):
        self._f = f
        self._value: _T = None

    def get(self) -> _T:
        if self._value is None:
            self._value = self._f()
        return self._value


# matlab.engine module; not loaded by default so that importing
# `simulink._engine` doesn't cause an error.
_matlab_engine = _Cached(import_matlab_engine)


class Engine:
    def __init__(self):
        self._engine = _matlab_engine.get().start_matlab()

    def run_script_from_file(
        self,
        path: PathLike,
        stdout: Optional[io.StringIO] = None,
        stderr: Optional[io.StringIO] = None,
    ) -> None:
        if stdout is None:
            stdout = io.StringIO()
        if stderr is None:
            stderr = io.StringIO()
        self._engine.run(path, nargout=0, stdout=stdout, stderr=stderr)

    def workspace(self) -> matlab.engine.matlabengine.MatlabWorkSpace:
        """Return the current engine's workspace."""
        return self._engine.workspace

    def get_field(self, handle: float, field: str) -> Any:
        """Return the value of the field ``field`` of the MATLAB object
        ``handle``.
        """
        return self._engine.subsref(handle, {"type": ".", "subs": field})

    def timeseries_to_python(self, ts: matlab.object) -> timeseries.TimeSeries:
        """Convert MATLAB timeseries object ``ts`` to a pylab TimeSeries
        object.
        """
        time = self.get_field(ts, "time")  # [[0.0], [1.0], ...]
        data = self.get_field(ts, "data")
        return _timeseries_to_python(time, data)


def _timeseries_to_python(
    time: Sequence[Sequence[float]], data: Sequence[ArrayLike]
) -> timeseries.TimeSeries:
    """Convert ``time``, ``data`` sequences to a pylab TimeSeries object.

    ``time`` and ``data`` are expected to be in the shape in which they
    are returned from the MATLAB engine. In particular, ``time`` is a
    ``Sequence[Sequence[float]]``.

    Args:
        time: The time vector
        data: The data vector
    """
    time = list(itertools.chain.from_iterable(time))  # [0.0, 1.0, ...]
    data = _sequence_to_list(data)

    if not data:
        return timeseries.TimeSeries()
    shape = _shape(data[0])

    if len(shape) == 1:
        return timeseries.TimeSeries(time, data)  # Vector

    # Beware! MATLAB/Simulink returns matrix output as follows:
    #     data[i][j][k] = (i, j)^th index of the k^th matrix
    # But we want:
    #     data[i][j][k] = (j, k)^th index of the i^th matrix.
    if len(shape) == 2:
        rows = len(data)
        cols = len(data[0])
        breakpoint_count = len(data[0][0])
        reordered = []
        for k in range(breakpoint_count):
            elem = [[data[i][j][k] for j in range(cols)] for i in range(rows)]
            reordered.append(elem)
        return timeseries.TimeSeries(time, reordered)

    raise ValueError("failed to discover data type of MATLAB object")


def _check_methods(cls, *args):
    """Check if ``cls`` has the methods ``*args``."""
    for m in args:
        if not any(m in B.__dict__ for B in cls.__mro__):
            return NotImplemented
    return True


class _Sequence(abc.ABC):
    """ABC for duck type sequences.

    A class is considered a _sequence_ if it implements ``__getitem__``,
    ``__len__``, ``__contains__``, ``__iter__``, ``__reversed__``,
    ``index`` and ``count``. Note that the correct interplay between
    these methods is _not_ required.

    Note that we do not use ``collections.abc.Sequence`` as it does not
    provide a ``__subclasshook__``. See levkivskyi's comment on
    https://bugs.python.org/issue35190 for details.
    """

    @classmethod
    def __subclasshook__(cls, subclass):
        if cls is _Sequence:
            return _check_methods(
                subclass,
                "__getitem__",
                "__len__",
                "__contains__",
                "__iter__",
                "__reversed__",
                "index",
                "count",
            )
        return NotImplemented


def _sequence_to_list(obj: Any) -> List[Any]:
    """Recursively convert a sequence to a list."""
    if not isinstance(obj, _Sequence):
        return obj
    return [_sequence_to_list(each) for each in obj]


def _shape(obj: Any) -> Tuple[int, ...]:
    """Return the shape of ``obj``.

    Note that we don't do much error checking. In particular, ``obj``
    may be an object which doesn't have a well-defined shape. For
    example,

    >>> _shape([[0, 1], [2, [3, 4]]])

    will _not_ raise and return ``(2, 2)``.
    """
    if not isinstance(obj, _Sequence) or not obj:
        return ()
    first = obj[0]
    result = (len(obj),)

    if isinstance(first, _Sequence):
        assert all(isinstance(each, _Sequence) for each in obj)
        return result + _shape(first)

    return result
