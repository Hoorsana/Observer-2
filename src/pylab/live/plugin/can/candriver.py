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

from pylab.core import report
from pylab.live import live


class CanError(Exception):
    """Wrapper for errors occuring in ``can`` and ``cantools``."""


class Database:

    def __init__(self, path: str, encoding: Optional[str] = None) -> None:
        """

        Make sure to use the correct encoding. Default encodings are found
        in the documentation of cantools.
        """
        self._db = cantools.database.load_file(path, encoding=encoding)

    def decode(self, msg: can.Message) -> dict:
        decoded_msg = self._db.decode_message(msg.arbitration_id, msg.data)
        return json.dumps(decoded_msg)

    def encode(self, name: str, data: dict) -> can.Message:
        try:
            msg = self._db.get_message_by_name(name)
        except KeyError as e:
            raise CanError from e
        try:
            encoded_data = msg.encode(data)
        except cantools.database.DecodeError as e:
            raise CanError from e
        return can.Message(arbitration_id=msg.frame_id, data=encoded_data)


# FIXME Replace this with a free function
class BusConfig:
    """Class for platform dependent bus configuration."""

    def __init__(self, args: dict[str, dict]) -> None:
        """Args:
            args:
                Maps OS identifiers to a dict of keyworded arguments
                for creating a ``can.interface.Bus``
        """
        self._args = args

    def get_args(self) -> tuple[dict]:
        """Get the arguments for the current platform."""
        return self._args[sys.platform]


class Can:

    def __init__(self, db: Database, bus: can.interface.Bus):
        self._db = db
        self._bus = bus
        self._listener = _Listener(db, bus)

    def take_received(self) -> list[dict]:
        return self._listener.take_received()

    def kill(self, timeout: Optional[float] = None):
        self._listener.kill(timeout)

    @classmethod
    def from_config(cls, db: Database, config: BusConfig) -> Can:
        kwargs = config.get_args()
        bus = can.interface.Bus(**kwargs)
        return cls(db, bus)

    def send_message(self, name: str, data: dict) -> live.NoopFuture:
        try:
            frame = self._db.encode(name, data)
        except CanError as e:
            return live.NoopFuture(report.LogEntry(severity=report.PANIC, what=str(e)))
        try:
            self._bus.send(frame)
        except can.CanError as e:
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
        decoded_msg = self._db.decode(msg)
        data = json.loads(decoded_msg)
        self._queue.append(data)


class CmdSendMessage(live.AbstractCommand):

    def __init__(self, time: float, target: str,
                 name: str, data: dict, description: str = '') -> None:
        """Args:
            time: The time of execution
            target: The receiving device
            name: The message name
            data: The message data
            description: A description of the command
        """
        super().__init__(time, description)
        self._target = target
        self._name = name
        self._data = data

    def execute(self, test_object: _TestObject) -> live.AbstractFuture:
        device, port = test_object.trace_back(self._target, self._signal)
        return device.execute('send_message', self._name, self._data)
