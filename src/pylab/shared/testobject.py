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

        Raises:
            StopIteration: If the device is not found

        """
        return next(elem for elem in self._devices if elem.name == device)

    def trace_forward(self, device: str, signal: str) -> tuple[Device, Port]:
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
            (device, device.find_port(elem.receiver_port))
            for elem in self._connections
            if elem.sender == device and elem.sender_port == signal
            if (device := self.find_device(elem.receiver))
        )

    def trace_back(self, device: str, signal: str) -> tuple[Device, Port]:
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
            (device, device.find_port(elem.sender_port))
            for elem in self._connections
            if elem.receiver == device and elem.receiver_port == signal
            if (device := self.find_device(elem.sender))
        )
