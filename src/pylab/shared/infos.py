# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Module for ``*Info`` classes commonly used in implementations of the
standard.
"""

from __future__ import annotations

import dataclasses
from dataclasses import InitVar

from pylab._private import utils


@dataclasses.dataclass(frozen=True)
class DetailInfo:
    devices: list[DeviceInfo]
    connections: list[ConnectionInfo]

    def __post_init__(self):
        # TODO Check for inconsistencies between devices and connections!
        pass

    @classmethod
    def from_dict(cls, data: dict):
        utils.assert_keys(
            data, set(), {'devices', 'connections'},
            'Error when loading DetailInfo: '
        )
        devices = [DeviceInfo(**elem) for elem in data['devices']]
        connections = [ConnectionInfo(**elem) for elem in data['connections']]
        return cls(devices, connections)

    def trace_forward(self, device: str, signal: str) -> tuple[str, str]:
        """Return all device/ports connected via outgoing connections.

        Args:
            device: The device from which to track the connections
            signal: The signal from which to track the connections

        Returns:
            A generator which holds all matching device/ports

        Raises:
            StopIteration: If ``target`` or ``signal`` is not found
        """
        return (
            (elem.receiver, elem.receiver_port)
            for elem in self.connections
            if elem.sender == device and elem.sender_port == signal
        )

    def trace_back(self, device: str, signal: str) -> tuple[str, str]:
        """Return all device/ports connected via ingoing connections.

        Args:
            device: The device from which to track the connections
            signal: The signal from which to track the connections

        Returns:
            A generator which holds all matching device/ports

        Raises:
            StopIteration: If ``target`` or ``signal`` is not found
        """
        return (
            (elem.sender, elem.sender_port)
            for elem in self.connections
            if elem.receiver == device and elem.receiver_port == signal
        )


@dataclasses.dataclass(frozen=True)
class DeviceInfo:
    name: str
    interface: ElectricalInterface

    @classmethod
    def from_dict(cls, data: dict) -> cls:
        utils.assert_keys(
            data, {'name', 'interface'}, set(),
            'Error when loading DetailInfo: '
        )
        name = data['name']
        interface = ElectricalInterface(**data['interface'])
        return cls(name, interface)


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
    # FIXME Make range/min/max optional and handle conversion using
    # transition function.
    def __post_init__(self, range: str):
        """Args:
            range:
                A string of the form ``'{lo}..{hi}'``, where ``lo`` and
                ``hi`` are floats with ``lo < hi``

        Raises:
            ValueError: If ``range`` is not correctly formatted
        """
        if not utils.is_valid_id(self.signal):
            raise ValueError(f'Invalid PortInfo: signal "{self.signal}" is not valid.')
        if range is not None:
            if self.min is not None:
                raise ValueError('Failed to initialize PortInfo: range and min specified')
            if self.max is not None:
                raise ValueError('Failed to initialize PortInfo: range and max specified')
            self._set_range(range)
        if self.min is None:
            raise ValueError('Failed to initialize PortInfo: missing range/min not specified')
        if self.max is None:
            raise ValueError('Failed to initialize PortInfo: missing range/max not specified')
        if self.min > self.max:
            raise ValueError(
                f'Invalid Port: min {self.min} exceeds max {self.max}.'
            )

    def _set_range(self, range):
            min_, max_ = utils.load_range(range)
            object.__setattr__(self, 'min', min_)
            object.__setattr__(self, 'max', max_)


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
        utils.assert_keys(
            data, set(), {'ports', 'description'},
            'Error when loading ElectricalInterface: '
        )
        ports = [PortInfo(**each) for each in data.get('ports', [])]
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
