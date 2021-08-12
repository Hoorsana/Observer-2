# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Module for ``*Info`` classes commonly used in implementations of the
standard.
"""

from __future__ import annotations

import dataclasses
import pydantic
from typing import Any, List, Optional

from pylab._private import utils
from pylab.core import infos


@pydantic.dataclasses.dataclass(frozen=True)
class DetailInfo:
    devices: List[DeviceInfo]
    connections: List[ConnectionInfo]


@pydantic.dataclasses.dataclass(frozen=True)
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
    sender_port: Any
    receiver: str
    receiver_port: Any
    description: Optional[str] = ''


@pydantic.dataclasses.dataclass(frozen=True)
class PortInfo:
    """Physical to electrical interface of a port on a device

    Attributes:
        signal: The physical signal
        channel: The electrical channel represented by the port
        flags: A list of additional info
        description: For documentation purposes

    The ``flags`` attribute may or may not be used by the driver to
    improve performance or raise errors which may otherwise not have
    been spotted.
    """
    signal: str
    channel: str
    flags: List[str] = pydantic.Field(default_factory=list)
    range: infos.RangeInfo = None
    description: Optional[str] = ''


@pydantic.dataclasses.dataclass(frozen=True)
class ElectricalInterface:
    """Info class for the electrical interface of a device.

    Attributes:
        ports: The electrical ports of the device
        description: For documentation purposes
    """
    ports: List[PortInfo] = dataclasses.field(default_factory=list)
    description: Optional[str] = ''

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


@pydantic.dataclasses.dataclass(frozen=True)
class DeviceInfo:
    name: str
    interface: ElectricalInterface = pydantic.Field(default_factory=ElectricalInterface)
