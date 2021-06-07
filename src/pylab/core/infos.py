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
from typing import Any, Optional

from pylab.core import errors


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
                raise errors.InfoError(f'Invalid TestInfo: Found two targets with the same name: "{elem.name}". The pylab specification states: "All members of `targets` **must** have a unique name"')
            seen.add(elem.name)
        seen = set()
        for request in self.logging:
            try:
                target = next(elem for elem in self.targets if request.target == elem.name)
            except StopIteration:
                raise errors.InfoError(f'Invalid TestInfo: Found no target for logging request "{request.target}". The pylab specification states: "For each `item` in `logging` the following **must** hold: There exists _exactly one_ `target` in `targets` with the following properties: `item.target == target.name`"')
            try:
                signal = next(elem for elem in target.signals if request.signal == elem.name)
            except StopIteration:
                raise errors.InfoError(f'Invalid TestInfo: Signal "{request.signal}" for logging request "{request.name}" not found. The pylab specification states: "For each `item` in `logging` the following **must** hold: There exists _exactly one_ `target` in `targets` with the following properties: There exists `signal` in `target.signals` so that `item.signal == signal.name`"')
            data = (request.target, request.signal)
            if data in seen:
                raise errors.InfoError(f'Invalid TestInfo: Found two logging requests with the same target and signal: Target "{request.target}", signal "{request.signal}". The specification states: "There **must** not exist two members `request1` and `request2` in `logging` with equal `target` and `signal` fields"')
            seen.add(data)
        for phase in self.phases:
            for command in phase.commands:
                try:
                    next(elem for elem in self.targets if command.target == elem.name)
                except StopIteration:
                    raise errors.InfoError(f'Invalid TestInfo: Target "{command.target}" not found. The specification states: "For each `phase` in `phases` and each `command` in `phase.commands` there **must** exist _exactly one_ `target` in `targets` with `command.target == target.name`."')


@dataclasses.dataclass(frozen=True)
class CommandInfo:
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
    data: dict[str, Any] = dataclasses.field(default_factory=dict)
    description: Optional[str] = ''

    def __post_init__(self):
        if self.time < 0.0:
            raise errors.InfoError(f'Invalid CommandInfo: `time` is equal to {self.time}. The specification states: "`time` **must** not be negative"')


@dataclasses.dataclass(frozen=True)
class PhaseInfo:
    """Info for creating a test phase.

    Attributes:
        duration: Total duration of the phase
        commands: Commands the phase is comprised of
        description: For documentation purposes

    Note that ``commands`` need not be ordered by time of execution.
    """
    duration: float
    commands: list[CommandInfo]
    description: Optional[str] = ''

    def __post_init__(self):
        if self.duration < 0.0:
            raise errors.InfoError(f'Invalid PhaseInfo: duration {self.duration} is negative. The specification states: "`duration` **must** be a non-negative float"')
        for elem in [elem for elem in self.commands if self.duration < elem.time]:
            raise errors.InfoError(f'Invalid PhaseInfo: CommandInfo execution time {elem.time} exceeds PhaseInfo duration {self.duration}. The specification states: "For each `item in commands`, the following **must** hold: `duration > item.time`"')

    @classmethod
    def from_dict(cls, data: dict) -> PhaseInfo:
        duration = data['duration']
        commands = [CommandInfo(**each) for each in data['commands']]
        description = data.get('description', '')
        return cls(duration, commands, description)


@dataclasses.dataclass(frozen=True)
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

    def __post_init__(self):
        if self.period is not None and self.period <= 0.0:
            raise errors.InfoError(f'Invalid LoggingInfo: period is {period}. The specification states: "`period` **must** be `None` or a positive `float`"')
        if self.kind not in {'linear', 'nearest', 'nearest-up', 'zero', 'slinear', 'quadratic', 'cubic', 'previous', 'next'}:
            raise errors.InfoError(f'Invalid LoggingInfo: kind is not valid. The specification states: "`kind` **must** be any value allowed by the documentation (https://docs.scipy.org/doc/scipy-1.6.0/reference/generated/scipy.interpolate.interp1d.html#scipy.interpolate.interp1d) of `scipy.interpolate.interp1d` from scipy 1.6.0: `\'linear\'`, `\'nearest\'`, `\'nearest-up\'`, `\'zero\'`, `\'slinear\'`, `\'quadratic\'`, `\'cubic\'`, `\'previous\'`"')

    def full_name(self) -> str:
        return f'{self.target}.{self.signal}'


@dataclasses.dataclass(frozen=True)
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
    min: float = None
    max: float = None
    # unit: Optional[Any] = ''  # FIXME Currently not implemented
    flags: list[str] = dataclasses.field(default_factory=list)
    description: Optional[str] = ''
    range: InitVar[str] = None

    def __post_init__(self, range: str):
        """Args:
            range:
                A string of the form ``'{lo}..{hi}'``, where ``lo`` and
                ``hi`` are floats with ``lo < hi``

        Raises:
            ValueError: If ``range`` is not correctly formatted
        """
        self._set_range(range)
        if not _is_valid_id(self.name):
            raise errors.InfoError(f'Invalid SignalInfo: name "{self.name}" is not valid. The specification states: "`name` **must** be a valid name"')
        if self.min > self.max:
            raise errors.InfoError(f'Invalid SignalInfo: min {self.min} exceeds max {self.max}. The specification states: "`min <= max` **must** hold"')

    def _set_range(self, range):
        if range is not None:
            if not (self.min is None and self.max is None):
                raise ValueError(
                    'Failed to init SignalInfo: SignalInfo.range '
                    'and SignalInfo.min or SignalInfo.max specified.')
            min, max = _load_range(range)
            object.__setattr__(self, 'min', min)
            object.__setattr__(self, 'max', max)


@dataclasses.dataclass(frozen=True)
class TargetInfo:
    """Info on a system under test.

    Attributes:
        name: id of the target
        signals: The signals that the target exposes
    """
    name: str
    signals: list[SignalInfo]
    description: Optional[str] = ''

    def __post_init__(self):
        if not _is_valid_id(self.name):
            raise errors.InfoError(f'Invalid TargetInfo: name "{self.name}" is not valid. The specification states: "`name` **must** be a valid name"')
        seen = set()
        for elem in self.signals:
            if elem.name in seen:
                raise errors.InfoError(f'Invalid TargetInfo: Found two signals with the same name "{elem.name}". The specification states: "No two elements of `signals` **must** have the same name"')
            seen.add(elem.name)


    @classmethod
    def from_dict(cls, data: dict) -> TargetInfo:
        name = data['name']
        signals = [SignalInfo(**each) for each in data['signals']]
        description = data.get('description', '')
        return TargetInfo(name, signals, description)


@dataclasses.dataclass(frozen=True)
class PortInfo:
    """Physical to electrical interface of a port on a device

    Attributes:
        signal: The physical signal
        channel: The electrical channel represented by the port
        min: Lower bound on the value of the electrical signal
        min: Upper bound on the value of the electrical signal
        flags: A list of additional info
        description: For documentation purposes

    The ``flags`` attribute may or may not be used by the driver to
    improve performance or raise errors which may otherwise not have
    been spotted.
    """
    signal: str
    channel: str
    min: float = None
    max: float = None
    flags: list[str] = dataclasses.field(default_factory=list)
    description: Optional[str] = ''
    range: InitVar[str] = None

    # FIXME Code duplication (see SignalInfo.__post_init__). Fix by
    # introducing ``class RangeInfo`` and replacing min, max with it.
    def __post_init__(self, range: str):
        if range is not None:
            if not (self.min is None and self.max is None):
                raise ValueError(
                    'failed to init PortInfo: SignalInfo.range '
                    'and SignalInfo.min or SignalInfo.max specified.')
            min, max = _load_range(range)
            object.__setattr__(self, 'min', min)
            object.__setattr__(self, 'max', max)


@dataclasses.dataclass(frozen=True)
class ConnectionInfo:
    """Class for representing wires or lines between ports.

    Attributes:
        sender: The ID of the sending device
        sender_port: The ID of the sending port
        receiver: The ID of the receiving device
        receiver_port: The ID of the receiving port
        description: For documentation purposes
    """
    sender: str
    sender_port: str
    receiver: str
    receiver_port: str
    description: Optional[str] = ''


@dataclasses.dataclass(frozen=True)
class ElectricalInterface:
    """Info class for the electrical interface of a device.

    Attributes:
        ports: The electrical ports of the device
        description: For documentation purposes
    """
    ports: list[PortInfo]
    description: Optional[str] = ''

    @classmethod
    def from_dict(cls, data: dict) -> ElectricalInterface:
        ports = [PortInfo(**each) for each in data['ports']]
        description = data.get('description', '')
        return cls(ports, description)

    def get_port(self, signal: str) -> PortInfo:
        """Return the electrical port associated with the physical
        ``signal``.

        Args:
            signal: The ID of the physical signal

        Raises:
            ValueError if the interface doesn't have a port representing
            ``signal``
        """
        info = next((each for each in self.ports if each.signal == signal), None)
        if info is None:
            raise ValueError(f'port for signal "{signal}" not found')
        return info


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


def _load_range(expr: str) -> tuple[float, float]:
    """Extract ``lo`` and ``hi`` from a range expression ``lo..hi``.

    Args:
        expr: A range expression of the form ``"lo..hi"``

    Returns:
        The numbers ``lo`` and ``hi``
    """
    # Regex for numbers:
    #      Optional sign
    #                  With comma
    #                                 Or...
    #                                  Optional signl
    #                                             No comma
    num = '[\\+-]{0,1}[0-9]+[.,][0-9]+|[\\+-]{0,1}[0-9]+'
    matches = re.match(f'({num})\\.+({num})', expr)
    if matches is None or matches.lastindex != 2:
        raise ValueError(f'Failed to read range expression: {expr}')
    min_, max_ = map(float, [matches.group(1), matches.group(2)])

    return min_, max_

def _is_valid_id(id: str):
    """Check if ``id`` is a valid id in the sense of the pylab specification.

    Args:
        id: The id to check
    """
    return '.' not in id
