# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""CAN plugin for pylab live driver."""

from __future__ import annotations

import abc
import concurrent.futures
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
from pylab.tools import yamltools


class CanError(Exception):
    """Wrapper for errors occuring in ``can`` and ``cantools``."""


@yamltools.yaml_object
class Database:
    """CAN database object for en- and decoding messages."""

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

    def decode(self, msg: can.Message) -> dict:
        """Decode a message to dictionary.

        Args:
            msg: The message to decode

        Returns:
            A dict containing the data of the message

        Raises:
            CanError:
                If ``cantools`` raises a ``cantools.database.DecodeError``
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
            CanError:
                If ``cantools`` raises a ``cantools.database.EncodeError``
                or the message ``name`` is not found in ``self._db``
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


@yamltools.yaml_object
class BusConfig:
    """Class for platform dependent bus configuration.

    Example:
        >>> conf = BusConfig({
            'linux': {
                'bustype': 'socketcan',
                'channel': 'can0',
                'bitrate': 125000,
            },
            'win32': {
                'bustype': 'pcan',
                'channel': 'PCAN_USBBUS1',
                'bitrate': 125000,
            }
        )
        >>> conf.get()  # On Linux
        {'bustype': 'socketcan', 'channel': 'can0', 'bitrate': 125000}
    """

    def __init__(self, **kwargs: dict) -> None:
        """Args:
            **kwargs:
                Maps OS identifiers to a dict of keyworded arguments
                for creating a ``can.interface.BusABC``

        Identifiers for common OS's are the following (see
        https://docs.python.org/3/library/sys.html#sys.platform for
        details): ``aix``, ``linux``, ``win32``, ``cygwin``, ``darwin``.
        """
        self._kwargs = kwargs

    def get(self) -> dict:
        """Get the arguments for the current platform.

        Raises:
            RuntimeError:
                If no configuration for this systems' OS is available
        """
        args = next(
            (v for k, v in self._kwargs.items() if sys.platform.startswith(k)), None
        )
        if args is None:
            raise RuntimeError(f"No bus configuration provided for OS {sys.platform}")
        return args


# FIXME Mimic the interface of concurrent.futures.Future with the
# interface of the futures! In particular, make `get_result` wait with a
# timeout and then raise on failure. This should simplify alot of our
# code.


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
        # We have one thread pool executor for each bus (the mapping
        # from bus to executor is determined by the order of the lists).
        # Thread-safety is guaranteed by using only one worker per bus,
        # provided that _all_ calls to the bus are submitted to the TPE.
        self._executors = [
            ThreadPoolExecutor(max_workers=1, thread_name_prefix=elem.name + "-thread")
            for elem in self._buses
        ]
        self._logging_requests: dict[str, live.AbstractFuture] = {}

    def __del__(self):
        for elem in self._executors:
            elem.shutdown(wait=False)

    def open(self):
        # FIXME Move report.Severity to its own  module?
        return live.NoOpFuture(report.LogEntry(report.INFO))

    # FIXME This is a synchronous call that might take some time. It may
    # be necessary to start a separate thread and kill the bus there.
    def close(self) -> live.AbstractFuture:
        futures = []
        for bus, executor in zip(self._buses, self._executors):
            futures.append(executor.submit(lambda: bus.kill(), "something"))
        # TODO We need to shutdown the executor! This is currently done in ``__del__``, but should maybe be placed in this function?
        return FutureCollection(futures)

    def setup(self) -> live.AbstractFuture:
        return live.NoOpFuture(report.LogEntry(report.INFO))

    def send_message(self, signal: str, name: str, data: dict) -> live.AbstractFuture:
        bus, executor = next(
            (bus, executor)
            for bus, executor in zip(self._buses, self._executors)
            if bus.name == signal
        )
        return executor.submit(
            lambda: bus.send_message(name, data), f"send_message({name}, {data})"
        )

    def log_signal(
        self, bus: str, _: Any
    ) -> tuple[live.AbstractFuture, live.AbstractFuture]:
        """Log a CAN signal.

        Args:
            signal: The port to log
            _: null parameter

        Returns:
            A noop future and a future which will contain the results.
        """
        future = Future(f"Logging request for {bus}")
        self._logging_requests[bus] = future
        return live.NoOpFuture(report.LogEntry(report.INFO)), future

    def end_log_signal(self, bus: str) -> live.AbstractFuture:
        bus_obj = next(elem for elem in self._buses if elem.name == bus)
        result = bus_obj.listener.take_received()
        self._logging_requests.pop(bus).set_result(result)
        return live.NoOpFuture(report.LogEntry(report.INFO))


class ThreadPoolExecutor:
    def __init__(
        self,
        max_workers: Optional[int] = None,
        thread_name_prefix: str = "",
        initializer: Optional[Callable] = None,
        initargs: tuple = (),
    ):
        self._tpe = concurrent.futures.ThreadPoolExecutor(
            max_workers, thread_name_prefix, initializer, initargs
        )

    def submit(self, fn: Callable, what: str, *args, **kwargs) -> None:
        future = self._tpe.submit(fn, *args, **kwargs)
        return FutureWrap(future, what)

    def shutdown(self, wait: bool = True) -> None:
        self._tpe.shutdown(wait)


class FutureWrap:
    def __init__(self, future: concurrent.futures.Future, what: str) -> None:
        self._future = future
        self._what = what
        self._result = None
        self._log = report.LogEntry(what)
        self._done_event = threading.Event()

        self._future.add_done_callback(self._finish)

    def _finish(self, _: concurrent.futures.Future):
        """

        Shall only be used as done callback for the wrapped future.

        We use this method to save all data
        """
        try:
            result = self._future.result()
            self._result = result
            self._log.severity = report.INFO
        except Exception as e:
            self._log.what = (
                self._what + "; failed with the following error: " + str(self._error)
            )
            self._log.severity = report.PANIC
            self._log.data["error"] = e
        self._done_event.set()

    @property
    def what(self) -> str:
        return self._what

    @property
    def log(self) -> str:
        return self._log

    def get_result(self) -> Any:
        return self._result

    def wait(self, timeout: Optional[float] = None) -> bool:
        # We cannot just do the following:
        # try:
        #     self._future.result(timeout)
        #     return True
        # except concurrent.futures.TimeoutError:
        #     return False
        # (This would result in a raise in case the job raised an
        # exception.) We have to use a seperate event.
        return self._done_event.wait(timeout)

    @property
    def done(self) -> bool:
        # Note: This method also requires us to use the seperate event
        # to ensure that ``_finish`` has finished.
        return self._done_event.is_set()


# FIXME This can probably be refactored out. Also: code-duplication?
class Future:
    """Primitive future object for logging requests."""

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


@yamltools.yaml_object(replace_from_yaml=False)
class CanBus:
    """Class for representing a CAN bus."""

    def __init__(
        self,
        name: str,
        db: Database,
        bus: can.interface.BusABC,
        listener: Optional[AbstractListener] = None,
    ) -> None:
        self._name = name
        self._db = db
        self._bus = bus
        if listener is None:
            self._listener = _Listener(db, bus)
        else:
            self._listener = listener

    # This is an override of the default `from_yaml` method!
    @classmethod
    def from_yaml(cls, loader, node) -> None:
        d = loader.construct_mapping(node, deep=True)
        return cls.from_config(**d)

    @property
    def name(self) -> str:
        return self._name

    @property
    def listener(self) -> AbstractListener:
        return self._listener

    def kill(self, timeout: Optional[float] = None):
        self._listener.kill(timeout)

    @classmethod
    def from_config(cls, signal: str, db: Database, config: BusConfig) -> CanBus:
        kwargs = config.get()
        bus = can.interface.Bus(**kwargs)
        return cls(signal, db, bus)

    def send_message(self, name: str, data: dict) -> live.NoOpFuture:
        try:
            frame = self._db.encode(name, data)
            self._bus.send(frame)
        except (CanError, can.CanError) as e:
            return live.NoOpFuture(report.LogEntry(severity=report.PANIC, what=str(e)))
        return live.NoOpFuture(report.LogEntry(severity=report.PANIC, what="..."))


class AbstractListener:
    @abc.abstractmethod
    def kill(self) -> None:
        """Stop listening."""
        pass


class _Listener:
    def __init__(self, db: Database, bus: can.interface.BusABC) -> None:
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
    def __init__(
        self,
        time: float,
        target: str,
        signal: str,
        name: str,
        data: dict,
        description: str = "",
    ) -> None:
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
        device, port = next(test_object.trace_back(self._target, self._signal))
        return device.execute("send_message", port.channel, self._name, self._data)


# FIXME code duplication: live.plugin.controllino
class FutureCollection(live.AbstractFuture):
    """Class for joining multiple futures under a single interface.

    May be used as noop futures if the list of futures is empty.
    """

    def __init__(self, futures: Optional[list[live.AbstractFuture]] = None):
        if futures is None:
            futures = []
        self._futures = futures

    def get_result(self) -> list[Any]:
        return [elem.get_result() for elem in self._futures]

    @property
    def what(self) -> str:
        return "\n".join(each.what for each in self._futures)

    @property
    def log(self) -> report.LogEntry:
        futures = [elem for elem in self._futures if elem.done]
        severity = max(elem.log.severity for elem in futures)
        return report.LogEntry("\n".join(each.log.what for each in futures), severity)

    @property
    def done(self) -> bool:
        return all(each.done for each in self._futures)

    def wait(self, timeout: Optional[float] = None) -> bool:
        if timeout is None:
            return all(elem.wait() for elem in self._futures)
        else:
            deadline = time.time() + timeout
            while time.time() < deadline:
                if all(each.done for each in self._futures):
                    return True
                time.sleep(GRAIN)
            return False
