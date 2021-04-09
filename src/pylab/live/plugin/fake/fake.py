# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Fake plugin module for testing purposes."""

from __future__ import annotations

import dataclasses
import threading
import time
from typing import Callable, Optional

from pylab.core import report
from pylab.core import timeseries
from pylab.live import live


class PluginFake:
    """User interface for fake plugin."""
    DEFAULT_TIC = 0.001

    def __init__(self, manager: DeviceManager):
        self._manager = manager
        self._stop_event = threading.Event()
        self._worker = WorkerThread(self._stop_event, self._manager)

    def start(self) -> None:
        self._worker.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._worker.join()


@dataclasses.dataclass
class DeviceManager:
    devices: Optional[list[Device]] = dataclasses.field(default_factory=list)
    connections: Optional[list[Connection]] = dataclasses.field(default_factory=list)

    def connect(self,
                sender: str,
                sender_channel: str,
                receiver: str,
                receiver_channel: str) -> None:
        sender = next(elem for elem in self.devices if elem.name == sender)
        receiver = next(elem for elem in self.devices if elem.name == receiver)
        connection = Connection(sender, sender_channel, receiver, receiver_channel)
        self.connections.append(connection)


class WorkerThread(threading.Thread):
    DEFAULT_TIC = 0.001

    def __init__(self, stop_event: threading.Event, manager: DeviceManager):
        super().__init__()
        self.daemon = True
        self._stop_event = stop_event
        self._manager = manager
        self._tic = self.DEFAULT_TIC

    def run(self) -> None:
        while not self._stop_event.is_set():
            self._run()
            time.sleep(self._tic)

    def _run(self) -> None:
        for elem in self._manager.connections:
            elem.receiver.set_value(
                elem.receiver_channel,
                elem.sender.get_value(elem.sender_channel))
        for elem in self._manager.devices:
            elem.update()


@dataclasses.dataclass
class Port:
    channel: str
    value: Any = 0.0
    flags: set[str] = dataclasses.field(default_factory=set)


class Future(live.AbstractFuture):

    def __init__(self, what: str) -> None:
        self._what = what
        self._result = None
        self._log = None
        self._done_event = threading.Event()

    @classmethod
    def create_noop(cls, what: str, result: Optional[Any] = None) -> Future:
        future = cls(what)
        future.set_result(result)
        return future

    def get_result(self) -> Any:
        return self._result

    def set_result(self, result: Any = None) -> None:
        self._result = result
        self._log = report.LogEntry(what=self._what, severity=report.INFO)
        self._done_event.set()

    def set_error(self, severity: report.Severity = report.PANIC) -> None:
        self._log = report.LogEntry(what=self._what, severity=severity)
        self._done_event.set()

    @property
    def what(self) -> str:
        return self._what

    @property
    def log(self) -> report.LogEntry:
        return self._log

    @property
    def done(self) -> bool:
        return self._done_event.is_set()

    def wait(self, time: float) -> bool:
        return self._done_event.wait(time)


class Device:

    def __init__(self,
                 name: str,
                 ports: list[dict]) -> None:
        self._name = name
        self._ports = [Port(**elem) for elem in ports]
        self._open = False
        self._lock = threading.Lock()

    @property
    def name(self) -> str:
        return self._name

    def update(self) -> None:
        pass

    def open(self) -> Future:
        with self._lock:
            self._open = True
        return Future.create_noop(f'Open device {self._name}')

    def close(self) -> Future:
        with self._lock:
            self._open = False
        return Future.create_noop(f'Close device {self._name}')

    def setup(self) -> Future:
        return Future.create_noop(f'Setup device {self._name}')

    # FIXME The methods below should raise if device is not open!
    def set_signal(self, channel: str, value: ArrayLike) -> Future:
        what = f'Set value of channel {channel} for device {self._name} to {value}',
        try:
            self.set_value(channel, value)
        except ValueError:
            future = Future(what)
            future.set_error(report.PANIC)
            return future
        return Future.create_noop(what)

    def set_value(self, channel: str, value: Any) -> None:
        port = next((elem for elem in self._ports if elem.channel == channel), None)
        if port is None:
            raise ValueError(f'Device {self._name} has no port {channel}')
        with self._lock:
            port.value = value

    def get_value(self, channel: str) -> None:
        what = f'Get value of channel {channel} for device {self._name}',
        port = next((elem for elem in self._ports if elem.channel == channel), None)
        if port is None:
            raise ValueError(f'Device {self._name} has no port {channel}')
        with self._lock:
            return port.value


class LoggingRequest:

    def __init__(self, channel: str, period: int) -> None:
        self._future = Future('Done logging {channel}')
        self._channel = channel
        self._time = []
        self._values = []
        self._period = period
        self._last_tic = -2*period
        self._start_time = time.time()

    @property
    def channel(self) -> str:
        return self._channel

    @property
    def future(self) -> Future:
        return self._future

    @property
    def ready(self) -> bool:
        diff = time.time() - self._last_tic
        return diff > self._period

    def update(self, value) -> None:
        t = time.time()
        self._time.append(t - self._start_time)
        self._values.append(value)
        self._last_tic = t

    def end(self) -> None:
        self._future.set_result(timeseries.TimeSeries(self._time, self._values))


class Logger(Device):

    def __init__(self, name: str, ports: list[Port]) -> None:
        super().__init__(name, ports)
        self._requests = []

    def log_signal(self, channel: str, period: int) -> tuple[Future, Future]:
        request = LoggingRequest(channel, period)
        self._requests.append(request)
        return Future.create_noop(f'Accepted logging request for {channel}@{period}'), request.future

    def end_log_signal(self, channel: str) -> Future:
        what = f'End logging of channel {channel}'
        request = next((elem for elem in self._requests if elem.channel == channel), None)
        if request is None:
            future = Future(what)
            future.set_error(report.PANIC)
            return future
        request.end()
        return Future.create_noop(what)

    def update(self) -> None:
        for elem in [elem for elem in self._requests if elem.ready]:
            value = self.get_value(elem.channel)
            elem.update(value)


@dataclasses.dataclass
class Connection:
    sender: Device
    sender_channel: str
    receiver: Device
    receiver_channel: str
