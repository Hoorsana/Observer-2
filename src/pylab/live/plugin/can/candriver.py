# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import copy
import queue
import sys
import threading
from typing import Optional

import can
import cantools
import json
import yaml

from pylab.core import report
from pylab.live import live


class CanError(Exception):
    """Wrapper for errors occuring in ``can`` and ``cantools``."""


class Database(yaml.YAMLObject):
    """CAN database object for en- and decoding messages."""
    yaml_tag = u'!Database'
    yaml_loader = yaml.SafeLoader

    def __init__(self, path: str, encoding: Optional[str] = None) -> None:
        """Args:
            path: The absolute or relative path to the database file
            encoding: The encoding of the database file

        The file at ``path`` must be of type ``.arxml``, ``.dbc``,
        ``.kcd``, ``.sym``, ``.cdd``. The type is extrapolated from the
        file extension. For details, see the documentation of cantools.

        Make sure to use the correct encoding. Default encodings are
        based on file type and found in the documentation of cantools.
        """
        self._db = cantools.database.load_file(path, encoding=encoding)

    @classmethod
    def from_yaml(cls, loader, node) -> None:
        d = loader.construct_mapping(node, deep=True)
        return cls(**d)

    def decode(self, msg: can.Message) -> dict:
        """Decode a message to dictionary. 

        Args:
            msg: The message to decode

        Returns:
            A dict containing the data of the message

        Raises:
            ???
        """
        try:
            return self._db.decode_message(msg.arbitration_id, msg.data)
        except cantools.database.DecodeError as e:
            raise CanError from e

    def encode(self, name: str, data: dict) -> can.Message:
        """Encode a message.

        Args:
            name: The message name
            data: The data to encode

        Raises:
            CanError: If encoding failed
        """
        try:
            msg = self._db.get_message_by_name(name)
        except KeyError as e:
            raise CanError from e
        try:
            encoded_data = msg.encode(data)
        except cantools.database.EncodeError as e:
            raise CanError from e
        return can.Message(arbitration_id=msg.frame_id, data=encoded_data)


# FIXME Write own YamlObject class with default from_yaml!
# FIXME Only CanPort should be a YamlObject!
class BusConfig(yaml.YAMLObject):
    """Class for platform dependent bus configuration."""
    yaml_tag = u'!BusConfig'
    yaml_loader = yaml.SafeLoader

    def __init__(self, args: dict[str, dict]) -> None:
        """Args:
            args:
                Maps OS identifiers to a dict of keyworded arguments
                for creating a ``can.interface.Bus``
        """
        self._args = args

    @classmethod
    def from_yaml(cls, loader, node) -> None:
        d = loader.construct_mapping(node, deep=True)
        return cls(**d)

    def get_args(self) -> tuple[dict]:
        """Get the arguments for the current platform."""
        return self._args[sys.platform]


class CanDevice:
    """Implementation of ``live.AbstractDevice`` for devices with CAN
    capability.

    This device also has logging capabilities. There's no real need to
    separate logging capabilities from sending capabilities.
    """

    def __init__(self, buses: list[CanBus]) -> None:
        """Args:
            buses: Maps signal names to their CAN bus
        """
        self._buses = buses
        self._logging_requests: dict[str, Future] = {}

    def open(self):
        # FIXME Move report.Severity to its own  module?
        return live.NoopFuture(report.LogEntry(report.INFO))

    # FIXME This is a synchronous call that might take some time. It may
    # be necessary to start a separate thread and kill the bus there.
    def close(self) -> live.AbstractFuture:
        for elem in self._buses:
            elem.kill()
        return live.NoopFuture(report.LogEntry(report.INFO))

    def setup(self) -> live.AbstractFuture:
        return live.NoopFuture(report.LogEntry(report.INFO))

    def send_message(self, signal: str, name: str, data: dict) -> live.AbstractFuture:
        bus = next(elem for elem in self._buses if elem.name == signal)
        bus.send_message(name, data)
        return live.NoopFuture(report.LogEntry(report.INFO))

    def log_signal(self,
                   bus: str,
                   _: Any
                  ) -> tuple[live.AbstractFuture, live.AbstractFuture]:
        """Log a CAN signal.

        Args:
            signal: The port to log
            _: null parameter

        Returns:
            A noop future and a future which will contain the results.
        """
        future = Future(f'Logging request for {bus}')
        self._logging_requests[bus] = future
        return live.NoopFuture(report.LogEntry(report.INFO)), future

    def end_log_signal(self, bus: str) -> live.AbstractFuture:
        bus_obj = next(elem for elem in self._buses if elem.name == bus)
        result = bus_obj.take_received()
        self._logging_requests.pop(bus).set_result(result)
        return live.NoopFuture(report.LogEntry(report.INFO))


class Future:

    def __init__(self, what: str):
        self._result = None
        self._what = what
        self._log = report.LogEntry(report.INFO, what)
        self._done_event = threading.Event()

    def get_result(self) -> Any:
        return self._result

    def set_result(self, result: Any) -> None:
        self._result = result
        self._done_event.set()

    @property
    def what(self) -> str:
        return self._what

    @property
    def log(self) -> report.LogEntry:
        return self._log

    def wait(self, timeout: Optional[float] = None) -> bool:
        return self._done_event.wait(timeout)

    def done(self) -> bool:
        return self._done_event.is_set()


# FIXME Only CanBus should be a YamlObject!
class CanBus(yaml.YAMLObject):
    """Class for representing a CAN bus."""
    yaml_tag = u'!CanBus'
    yaml_loader = yaml.SafeLoader

    def __init__(self,
                 name: str,
                 db: Database,
                 bus: can.interface.Bus) -> None:
        self._name = name
        self._db = db
        self._bus = bus
        self._listener = _Listener(db, bus)

    @classmethod
    def from_yaml(cls, loader, node) -> None:
        d = loader.construct_mapping(node, deep=True)
        return cls.from_config(**d)

    @property
    def name(self) -> str:
        return self._name

    def take_received(self) -> list[dict]:
        return self._listener.take_received()

    def kill(self, timeout: Optional[float] = None):
        self._listener.kill(timeout)

    @classmethod
    def from_config(cls, signal: str, db: Database, config: BusConfig) -> CanBus:
        kwargs = config.get_args()
        bus = can.interface.Bus(**kwargs)
        return cls(signal, db, bus)

    def send_message(self, name: str, data: dict) -> live.NoopFuture:
        try:
            frame = self._db.encode(name, data)
            self._bus.send(frame)
        except (CanError, can.CanError) as e:
            return live.NoopFuture(report.LogEntry(severity=report.PANIC, what=str(e)))
        return live.NoopFuture(report.LogEntry(severity=report.PANIC, what='...'))

    # TODO (In the live driver) For synchronous execution, it may be
    # better to let ``execute`` return ``None`` and consider this as the
    # "noop future" case


class _Listener:

    def __init__(self, db: Database, bus: can.interface.Bus) -> None:
        self._db = db
        self._queue = []
        self._lock = threading.Lock()
        self._notifier = can.Notifier(bus, listeners=[self._put])

    def pop(self):
        with self._lock:
            return self._queue.pop()

    def take_received(self):
        """Return the queued received messages and reset the queue."""
        with self._lock:
            result = self._queue
            self._queue = []
            return result

    def kill(self, timeout: Optional[float] = None) -> None:
        if timeout is None:
            self._notifier.stop()  # Use default timeout of python-can.
        else:
            self._notifier.stop(timeout)

    def _put(self, msg: can.Message) -> None:
        self._queue.append(self._db.decode(msg))


class CmdCanMessage(live.AbstractCommand):

    def __init__(self, time: float, target: str,
                 signal: str, name: str, data: dict, description: str = '') -> None:
        """Args:
            time: The time of execution
            target: The receiving device
            name: The message name
            data: The message data
            description: A description of the command
        """
        super().__init__(time, description)
        self._target = target
        self._signal = signal
        self._name = name
        self._data = data

    def execute(self, test_object: _TestObject) -> live.AbstractFuture:
        device, port = test_object.trace_back(self._target, self._signal)
        return device.execute('send_message', port.channel, self._name, self._data)
