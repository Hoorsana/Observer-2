# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Module for ``*Info`` classes.

Some of the ``*Info`` classes have other ``*Info`` classes as members.
If that is the case, the former admits a ``from_dict`` method
which recursively unpacks a dictionary to create the object.
"""

from __future__ import annotations

import dataclasses
from dataclasses import InitVar
import itertools
import re
import pydantic
from typing import Any, List, Optional, Dict

from pylab._private import utils
from pylab.core import errors


class InfoError(errors.PylabError):
    """Raised if *Info instance is invalid."""


class NegativeTimeError(InfoError):
    """Raised if a time point is specified using a negative float."""


class CommandTooLateError(InfoError):
    """Raised if a command's execution time exceeds the phase's
    duration."""


class InvalidIdError(InfoError):
    """Raised if an id/name is not valid."""


class ConflictingDataError(InfoError):
    """Raised if specified data is ambiguous."""


class NonPositivePeriodError(InfoError):
    """Raised if the period of a request is not positive."""


class InvalidKindError(InfoError):
    """Raised if interpolation kind is invalid."""


class ConflictingSignalIdError(InfoError):
    """Raised if a ``TargetInfo`` is initialized with two or more
    signals with the same id."""


@dataclasses.dataclass(frozen=True)
class TestInfo:
    """Master info for a test, start-to-finish.

    Attributes:
        targets: Infos on targets in the test environment
        logging: Infos on signals to be logged during test
        phases: Infos on the phases of the test
        description: A detailed description of the test
    """
    targets: list[TargetInfo]
    logging: list[LoggingInfo]
    phases: list[PhaseInfo]
    description: Optional[str] = ''

    def __post_init__(self):
        # Check for duplicates in `targets`.
        seen = set()
        for elem in self.targets:
            if elem.name in seen:
                raise InfoError(
                    f'Invalid TestInfo: Found two targets with the same name: "{elem.name}". The pylab specification states: "All members of `targets` **must** have a unique name"')
            seen.add(elem.name)
        seen = set()
        for request in self.logging:
            try:
                target = next(
                    elem for elem in self.targets if request.target == elem.name)
            except StopIteration:
                raise InfoError(
                    f'Invalid TestInfo: Found no target for logging request "{request.target}". The pylab specification states: "For each `item` in `logging` the following **must** hold: There exists _exactly one_ `target` in `targets` with the following properties: `item.target == target.name`"')
            try:
                signal = next(
                    elem for elem in target.signals if request.signal == elem.name)
            except StopIteration:
                raise InfoError(
                    f'Invalid TestInfo: Signal "{request.signal}" for logging request "{request.name}" not found. The pylab specification states: "For each `item` in `logging` the following **must** hold: There exists _exactly one_ `target` in `targets` with the following properties: There exists `signal` in `target.signals` so that `item.signal == signal.name`"')
            data = (request.target, request.signal)
            if data in seen:
                raise InfoError(
                    f'Invalid TestInfo: Found two logging requests with the same target and signal: Target "{request.target}", signal "{request.signal}". The specification states: "There **must** not exist two members `request1` and `request2` in `logging` with equal `target` and `signal` fields"')
            seen.add(data)
        for phase in self.phases:
            for command in phase.commands:
                try:
                    next(elem for elem in self.targets if command.target == elem.name)
                except StopIteration:
                    raise InfoError(
                        f'Invalid TestInfo: Target "{command.target}" not found. The specification states: "For each `phase` in `phases` and each `command` in `phase.commands` there **must** exist _exactly one_ `target` in `targets` with `command.target == target.name`."')


class CommandInfo(pydantic.BaseModel):
    """Info for creating a command.

    Attributes:
        time: Time of execution during phase
        command: The command name
        target: The targeted device
        data: Arguments passed to the initializer of the command
        description: For documentation purposes
    """
    time: float
    command: str
    target: str  # Name of the targeted physical device.
    # Data that may depend on the type of command, like signal, value, etc.
    data: Dict[str, Any] = {}
    description: Optional[str] = ''

    @pydantic.validator('time', allow_reuse=True)
    @classmethod
    def time_must_be_positive(cls, v: float) -> float:
        if v < 0:
            raise NegativeTimeError(
                f'Invalid CommandInfo: `time` is equal to {v}. The specification states: "`time` **must** not be negative"'
            )
        return v


class PhaseInfo(pydantic.BaseModel):
    """Info for creating a test phase.

    Attributes:
        duration: Total duration of the phase
        commands: Commands the phase is comprised of
        description: For documentation purposes

    Note that ``commands`` need not be ordered by time of execution.
    """
    duration: float
    commands: List[CommandInfo]
    description: Optional[str] = ''

    @pydantic.validator('duration', allow_reuse=True)
    @classmethod
    def _duration_must_be_positive(cls, v: float) -> float:
        if v < 0:
            raise NegativeTimeError(
                f'Invalid PhaseInfo: duration {v} is negative. The specification states: "`duration` **must** be a non-negative float"'
            )
        return v

    @pydantic.validator('commands', each_item=True, allow_reuse=True)
    @classmethod
    def _command_time_must_not_exceed_duration(cls,
                                               v: CommandInfo,
                                               values
                                               ) -> CommandInfo:
        duration = values['duration']
        if v.time > duration:
            raise CommandTooLateError(
                f'Invalid PhaseInfo: CommandInfo execution time {v.time} exceeds PhaseInfo duration {duration}. The specification states: "For each `item in commands`, the following **must** hold: `duration > item.time`"')
        return v


@pydantic.dataclasses.dataclass(frozen=True)
class LoggingInfo:
    """Info for logging a signal during a test.

    Attributes:
        target: The target device the signal belongs to
        signal: The signal to log
        period: The period with which the signal is logged in seconds
        kind: The kind of interpolation
        description: For documentation purposes

    The kind of interpolation may be any value specified in the scipy
    1.6.0 documentation of ``interp1d``
    (https://docs.scipy.org/doc/scipy-1.6.0/reference/generated/scipy.interpolate.interp1d.html#scipy.interpolate.interp1d)
    ``linear``, ``nearest``, ``nearest-up``, ``zero``, ``slinear``,
    ``quadratic``, ``cubic``, ``previous``, ``next`` and will have the
    same meaning.
    """
    target: str
    signal: str
    period: Optional[float] = None
    kind: str = 'previous'
    description: Optional[str] = ''

    @pydantic.validator('period')
    @classmethod
    def _period_must_be_positive_or_none(cls, v):
        if v is None:
            return None
        if v <= 0.0:
            raise NonPositivePeriodError(
                f'Invalid LoggingInfo: period is {v}. The specification states: "`period` **must** be `None` or a positive `float`"')
        return v

    @pydantic.validator('kind')
    @classmethod
    def _kind_must_be_valid(cls, v):
        if v not in {'linear', 'nearest', 'nearest-up',
                             'zero', 'slinear', 'quadratic', 'cubic', 'previous', 'next'}:
            raise InvalidKindError(f'Invalid LoggingInfo: kind "{v}" is not valid. The specification states: "`kind` **must** be any value allowed by the documentation (https://docs.scipy.org/doc/scipy-1.6.0/reference/generated/scipy.interpolate.interp1d.html#scipy.interpolate.interp1d) of `scipy.interpolate.interp1d` from scipy 1.6.0: `\'linear\'`, `\'nearest\'`, `\'nearest-up\'`, `\'zero\'`, `\'slinear\'`, `\'quadratic\'`, `\'cubic\'`, `\'previous\'`"')
        return v

    def full_name(self) -> str:
        return f'{self.target}.{self.signal}'


@pydantic.dataclasses.dataclass(frozen=True)
class RangeInfo:
    min: float
    max: float

    @pydantic.validator('max')
    @classmethod
    def _max_must_be_larger_than_min(cls, v, values):
        min_ = values['min']
        if min_ > v:
            raise InfoError(
                f'Invalid SignalInfo: min {min_} exceeds max {v}. The specification states: "`min <= max` **must** hold"')
        return v


@pydantic.dataclasses.dataclass(frozen=True)
class SignalInfo:
    """Info data for a _physical_ signal.

    Attributes:
        name: ID of the signal
        min: Lower bound on the value of the physical signal
        min: Upper bound on the value of the physical signal
        flags: A list of additional info
        description: For documentation purposes
        range:
            A string of the form ``'{lo}..{hi}'``, where ``lo`` and
            ``hi`` are floats with ``lo < hi`` specifying the physical
            range of the signal

    The ``flags`` attribute may or may not be used by the driver to
    improve performance or raise errors which may otherwise not have
    been spotted.

    The ``__init__`` may be called with *either* ``range`` or *both*
    ``min`` and ``max``. Otherwise, ``__init__`` will raise a
    ``ValueError``.
    """
    name: str
    range: RangeInfo = None
    # unit: Optional[Any] = ''  # FIXME Currently not implemented
    flags: List[str] = dataclasses.field(default_factory=list)
    description: Optional[str] = ''

    @pydantic.validator('name', allow_reuse=True)
    @classmethod
    def _id_must_be_valid(cls, v: str) -> str:
        if not utils.is_valid_id(v):
            raise InvalidIdError(
                f'Invalid SignalInfo: name "{v}" is not valid. The specification states: "`name` **must** be a valid name"'
            )
        return v


@pydantic.dataclasses.dataclass(frozen=True)
class TargetInfo:
    """Info on a system under test.

    Attributes:
        name: id of the target
        signals: The signals that the target exposes
    """
    name: str
    signals: List[SignalInfo]
    description: Optional[str] = ''

    @pydantic.validator('name', allow_reuse=True)
    @classmethod
    def _id_must_be_valid(cls, v: str) -> str:
        if not utils.is_valid_id(v):
            raise InvalidIdError(
                f'Invalid TargetInfo: name "{v}" is not valid. The specification states: "`name` **must** be a valid name"'
            )
        return v

    @pydantic.validator('signals')
    @classmethod
    def _signal_ids_must_be_unique(cls, v):
        seen = set()
        for elem in v:
            if elem.name in seen:
                raise ConflictingSignalIdError(
                    f'Invalid TargetInfo: Found two signals with the same name "{elem.name}". The specification states: "No two elements of `signals` **must** have the same name"')
            seen.add(elem.name)
        return v

    @classmethod
    def from_dict(cls, data: dict) -> TargetInfo:
        try:
            utils.assert_keys(
                data, {'name'}, {'signals', 'description'},
                'Error when loading TargetInfo: '
            )
        except AssertionError as e:
            raise InfoError from e
        name = data['name']
        signals = [SignalInfo(**each) for each in data.get('signals', [])]
        description = data.get('description', '')
        return TargetInfo(name, signals, description)


@dataclasses.dataclass(frozen=True)
class AssertionInfo:
    """Class for representing assertions made about test data.

    Attributes:
        type:
            Namespace qualified name of a Python class which
            implements `AbstractVerification`
        data:
            Keyworded arguments for calling ``__init__`` of the class
            specified by the ``type`` field
    """
    type: str
    data: dict[str, Any]
    args: dict[str, str]
