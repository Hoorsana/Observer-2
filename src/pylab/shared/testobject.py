# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import abc


class Port(abc.ABC):
    @property
    @abc.abstractmethod
    def signal(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def channel(self) -> str:
        pass


class Device(abc.ABC):
    @property
    @abc.abstractmethod
    def name(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def ports(self) -> list[Port]:
        pass

    @property
    @abc.abstractmethod
    def find_port(self, signal: str) -> Port:
        pass


class Connection(abc.ABC):
    @property
    @abc.abstractmethod
    def sender(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def sender_port(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def receiver(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def receiver_port(self) -> str:
        pass


class TestObjectBase:
    """Base object for the test object pattern which is used in many
    drivers.
    """

    def __init__(self, devices: list[Device], connections: list[Connections]) -> None:
        """Args:
        devices: The devices in the test setup
        connections: The devices between the connections
        """
        self._devices = devices
        self._connections = connections

    def find_device(self, device: str) -> Device:
        """Return the device with id ``device``.

        Args:
            device: The id of the device to find

        Returns:
            The device (if found) or ``None``
        """
        return next((elem for elem in self._devices if elem.name == device), None)

    def trace_forward(self, device: str, signal: str) -> Generator[tuple[Device, Port]]:
        """Return all device/ports connected via outgoing connections.

        Args:
            device: The device from which to track the connections
            signal: The signal from which to track the connections

        Returns:
            A generator which holds all matching device/ports
        """
        for c in [
            c
            for c in self._connections
            if c.sender == device and c.sender_port == signal
        ]:
            d = self.find_device(c.receiver)
            p = d.find_port(c.receiver_port)
            yield (d, p)

    def trace_back(self, device: str, signal: str) -> Generator[tuple[Device, Port]]:
        """Return all device/ports connected via ingoing connections.

        Args:
            device: The device from which to track the connections
            signal: The signal from which to track the connections

        Returns:
            A generator which holds all matching device/ports
        """
        for c in [
            c
            for c in self._connections
            if c.receiver == device and c.receiver_port == signal
        ]:
            d = self.find_device(c.sender)
            p = d.find_port(c.sender_port)
            yield (d, p)
