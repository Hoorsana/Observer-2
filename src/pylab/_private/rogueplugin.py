from __future__ import annotations

import dataclasses
import threading

from numpy.typing import ArrayLike
import rogue

from pylab.core import infos
from pylab.core import report
from pylab.core import timeseries
from pylab.live import live


class Server(rogue.Server):

    def __init__(self):
        super().__init__(grain=0.01)
        self._lazy_data = None

    @property
    def lazy_data(self):
        if self._lazy_data is None:
            self.kill()
            self._lazy_data = self.data()
        return self._lazy_data

    def reset(self):
        self._lazy_data = None
        self.kill()


_server = Server()


def init(info: infos.TestInfo, details: live.Details) -> None:
    # Note that we do not require that all device be rogue devices. For
    # example, a rogue device may communicate with a different type of
    # device using a socket. We do, however, require that every
    # connection that start/ends in a rogue device also ends/starts in a
    # rogue device (connections between rogue and non-rogue devices will
    # be ignored).
    del info
    devices = [item for item in details.devices if item.module.endswith('rogueplugin')]
    for dev in devices:
        # Note that no ``Device`` objects are created here!
        channels = [info.channel for info in dev.interface.ports]
        ports = {channel: dev.extension['defaults'][channel] for channel in channels}
        loop = dev.data.get('loop')
        _server.add_client(dev.name, ports, loop)
    connections = [
        item for item in _init_connections(details)
        if item.sender in [each.name for each in devices]
           and item.receiver in [each.name for each in devices]
    ]
    for con in connections:
        _server.connect( (con.sender,   con.sender_port),
                         (con.receiver, con.receiver_port) )


def _init_connections(details: live.Details) -> list[infos.ConnectionInfo]:
    """Translate connection on abstract level to driver liver.

    Args:
        details: The driver details
    """
    # TODO This is another type of logic that occurs in multiple drivers
    # and should probably be provided in a central toolbox.
    result = []
    for conn in details.connections:
        sender = next(dev for dev in details.devices if dev.name == conn.sender)
        sender_port = sender.interface.get_port(conn.sender_port)
        receiver = next(dev for dev in details.devices if dev.name == conn.receiver)
        receiver_port = receiver.interface.get_port(conn.receiver_port)
        c = infos.ConnectionInfo(conn.sender, sender_port.channel, conn.receiver, receiver_port.channel)
        result.append(c)
    return result


def post_init(info: infos.TestInfo,
              details: live.Details,
              test_object: live._TestObject
              ) -> None:
    del info, details, test_object
    _server.exec()


def reset():
    _server.reset()


@dataclasses.dataclass
class LoggingRequest:
    port: str
    period: float
    future: Future


class Future:

    def __init__(self,
                 what: str,
                 severity: report._Severity = report.INFO,
                 result: Optional[Any] = None
                 ) -> None:
        self._what = what
        self._log = report.LogEntry(severity, what)
        self._result = result
        self._done_event = threading.Event()

    @property
    def what(self) -> str:
        return self._what

    @property
    def log(self) -> report.LogEntry:
        return self._log

    def set_result(self, value) -> None:
        self._result = value
        self._done_event.set()

    def get_result(self) -> Any:
        return self._result

    def wait(self, timeout: Optional[float] = None) -> bool:
        return self._done_event.wait(timeout)

    def done(self) -> bool:
        return self._done_event.is_set()


# TODO Add live.NoOpDevice which implements open, close, etc. with NoOpFutures! (The message can use `__name__` to insert the module name?)
class Device:

    def __init__(self, id: str, ports: list[str]) -> None:
        self._id = id
        self._ports = list(ports)
        self._requests = {}

    def open(self) -> live.AbstractFuture:
        return live.NoOpFuture(report.LogEntry('open rogue device'))

    def close(self) -> live.AbstractFuture:
        return live.NoOpFuture(report.LogEntry('close rogue device'))

    def setup(self) -> live.AbstractFuture:
        return live.NoOpFuture(report.LogEntry('setup rogue device'))

    def log_signal(self,
                   port: str,
                   period: float
                   ) -> tuple[live.AbstractFuture, live.AbstractFuture]:
        future = Future('log signal')
        try:
            _server.listen(self._id, port)
        except rogue.RogueException as e:
            return live.NoOpFuture(report.LogEntry(f'rogue: failed to log signal {self._id}.{port} with the following error: {e}', report.FAILED)), future
        self._requests[port] = LoggingRequest(port, period, future)
        return live.NoOpFuture(report.LogEntry(f'begin log signal')), future

    def end_log_signal(self, port: str) -> live.AbstractFuture:
        try:
            data = _server.lazy_data[self._id][port]
            # TODO Use correct period on timeseries.
            # This could be done in parallel, but we want to use rogueplugin
            # for testing purposes, so we try to avoid multiple threads as
            # much as possible.
            self._requests[port].future.set_result(timeseries.TimeSeries(data.time, data.values))
        except KeyError as e:
            return live.NoOpFuture(f'rogue: failed to find data for signal {self._id}.{port}: {e}')
        return live.NoOpFuture('end log signal')

    def set_signal(self, port: str, value: ArrayLike) -> live.AbstractFuture:
        try:
            _server.set_value(self._id, port, value)
        except rogue.RogueException as e:
            return live.NoOpFuture(report.LogEntry(str(e), severity=report.FAILED))
        return live.NoOpFuture(report.LogEntry(f'set {port} to {value}'))
