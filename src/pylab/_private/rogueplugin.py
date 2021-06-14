import rogue

import dataclasses
from pylab import live
from numpy.typing import ArrayLike


class Server(rogue.Server):

    def __init__(self):
        super().__init__()
        self._lazy_data = None

    @property
    def lazy_data(self):
        if self._lazy_data is None:
            self.kill()
            self._lazy_data = self.data()
        return self._lazy_data

    def reset(self):
        self._lazy_data = None


_server = Server()


def init(info: infos.TestInfo, details: live.Details) -> None:
    # Note that we do not require that all device be rogue devices. For
    # example, a rogue device may communicate with a different type of
    # device using a socket. We do, however, require that every
    # connection that start/ends in a rogue device also ends/starts in a
    # rogue device (connections between rogue and non-rogue devices will
    # be ignored).
    del info
    devices = [item in details.devices if item.module == 'rogueplugin']
    for dev in devices:
        channels = [info.channel for info in dev.interface.ports]
        ports = {channel: dev.data.defaults[channel] for channel in channels}
        loop = dev.data.get('loop')
        _server.add_client(dev.name, ports, loop)
    connections = [
        item for item in details.connections
        if item.sender in [each.name for each in devices]
           and item.receiver in [each.name for each in devices]
    ]
    for con in connections:
        _server.connect( (con.sender,   con.sender_port),
                         (con.receiver, con.receiver_port) )


def post_init(info: infos.TestInfo,
              details: live.Details,
              test_object: live._TestObject
              ) -> None:
    del info, details, test_object
    _server.run()


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
                 serverity: report._Severity,
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

    def get_result(self) -> Any:
        return self._result

    def wait(self, timeout: Optional[float] = None) -> bool:
        return self._done_event.wait(timeout)

    def done(self) -> bool:
        return self._done_event.is_set()


# TODO Add live.NoOpDevice which implements open, close, etc. with NoOpFutures! (The message can use `__name__` to insert the module name?)
class Device:

    def __init__(self,
                 id: str,
                 ports: dict[str, ArrayLike],
                 ) -> None:
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
        if not port in self._ports:
            return live.NoOpFuture(report.LogEntry(f'Device {id} has no port {port}', report.FAILED)), None
        future = Future()
        self._requests[port] = LoggingRequest(port, period, future)
        return live.NoOpFuture(report.LogEntry(f'begin log signal')), future

    def end_log_signal(self, port: str) -> live.AbstractFuture:
        data = _server.lazy_data[self._id][port]
        # This could be done in parallel, but we want to use rogueplugin
        # for testing purposes, so we try to avoid multiple threads as
        # much as possible.
        # TODO Cleanup the timeseries...
        self._requests[port].set_result(timeseries.TimeSeries(data.time, data.values))
        return live.NoOpFuture('end log signal')

    def set_signal(self, port: str, value: ArrayLike) -> live.AbstractFuture:
        try:
            _server.set_value(port, value)
        except rogue.RogueException as e:
            return live.NoOpFuture(report.LogEntry(str(e), severity=report.FAILURE))
        return live.NoOpFuture(report.LogEntry(f'set {port} to {value}'))

