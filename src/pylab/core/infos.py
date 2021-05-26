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
import re
from typing import Any, Optional


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


@dataclasses.dataclass(frozen=True)
class CommandInfo:
    """Info for creating a command.

    Attributes:
        time: Time of execution during phase
        command: The commands fully qualified name
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
        period: The period with which the signal is logged
        kind: The kind of interpolation
        description: For documentation purposes

    The kind of interpolation may be any value specified in the scipy
    documentation of interp1d
    (https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.interp1d.html):
    ``linear``, ``nearest``, ``nearest-up``, ``zero``, ``slinear``,
    ``quadratic``, ``cubic`` and will have the same meaning.
    """
    target: str
    signal: str
    period: Optional[float] = None
    kind: str = 'previous'
    description: Optional[str] = ''

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

    The ``flags`` attribute may or may not be used by the driver to
    improve performance or raise errors which may otherwise not have
    been spotted.

    The ``__init__`` may be called with either ``range`` or *both*
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
        if range is not None:
            if not (self.min is None and self.max is None):
                raise ValueError(
                    'failed to init SignalInfo: SignalInfo.range '
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
