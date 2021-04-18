# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""pylab driver for just-in-time execution of tests.

This driver works by issueing commands to the provided devices
*just-in-time*. Devices could be serial devices, service daemons running
on the host, etc.

The details file must satisfy the following specification:

* There mus tbe a ``devices`` field, which is a list whose elements
  **must** have the following fields:

  - ``name`` (str): The unique identifier of the device.
  - ``type`` (str): A python function which returns an object of a
    subclass of ``AbstractDevice``
  - ``interface`` (map): A list of data from which
    :meth:`PortInfo <pylab.core.infos.PortInfo>` objects can be created.

  If the device implements a target, then it *must* carry the same
  ``name`` as the target and map the target's interface.

  The elements **may** also have a ``data`` field, which must satisfy the
  following condition: After loading ``data``, its contents may be
  passed as keyworded arguments to the function of the class given by
  the ``type`` field.

  Note that ``type`` may be a Python class.

* The **must** be a ``connection`` field, whose elements are 4-tuples of the
  following form:

    (sender, sender_port, receiver, receiver_port)

  Specifying a device or a port that doesn't exist is undefined
  behavior.

  Every port that is stimulated and every port that is logged *must* be
  connected to a device with the respective stimulating and logging
  capability.

Adding new device types will likely require a rather complex wrapping
method by which the new device's asynchronous behavior is managed by
``AbstractFuture`` objects.
"""

from __future__ import annotations

import abc
import dataclasses
import time
from typing import ContextManager
import yaml

from pylab.core import errors
from pylab.core import infos
from pylab.core import timeseries
from pylab.core import report
from pylab.core import utils as coreutility
from pylab.live import utility as liveutility

HEARTBEAT = 0.001

# FIXME Before executing the test for real, do a "dry run" checks all
# devices for compatability with the commands executed on them (dry run
# fails if `set_signal_sine` is run on a device without sinus
# capability), correct connections (for example, fail if a command would
# fail due to trace_back raising a StopIteration), etc.


# frontend {{{


def create(info: infos.TestInfo, details: Details) -> Test:
    """Implementation of :meth:`core.api.create
    <pylab.core.api.create>`.
    """
    test_object = _TestObject(details, info.targets)

    commands: list[AbstractCommand] = []
    duration = 0.0
    for phase in info.phases:
        commands += [_create_command(each, duration) for each in phase.commands]
        duration += phase.duration

    return Test(test_object, commands, info.logging, duration)


class Test:
    """Implementation of :meth:`core.api.Test <pylab.core.api.Test>`."""

    def __init__(self,
                 test_object: _TestObject,
                 commands: list[AbstractCommand],
                 logging_infos: list[infos.LoggingInfo],
                 duration: float) -> None:
        """Args:
            test_object: The underlying test object
            commands: The commands to execute during the test
            logging_infos: The signals to log during the test
            duration: The total duration of the test in seconds

        Note that the list need not be sorted by time.
        """
        self._test_object = test_object
        self._commands = commands
        self._duration = duration
        self._controller = _FutureController()
        self._logging_handler = _LoggingHandler(self._test_object, logging_infos)

    def execute(self) -> report.Report:
        logbook = []

        with _DeviceContextManager(self._test_object, logbook):
            if _panic(logbook):
                return report.Report(logbook, {})

            logbook += self._test_object.setup()
            if _panic(logbook):
                return report.Report(logbook, {})

            logbook += self._logging_handler.begin()
            if _panic(logbook):
                return report.Report(logbook, {})

            start_time = time.time()
            while True:  # TODO Replace with while time.time() < dead:
                current_time = time.time() - start_time
                if current_time > self._duration:
                    break
                commands = [each for each in self._commands if current_time >= each.time]
                # Remove commands.
                self._commands = [
                    each for each in self._commands if each not in commands]
                for cmd in commands:
                    future = cmd.execute(self._test_object)
                    self._controller.put(future, timeout=1)
                logbook += self._controller.run()
                if _panic(logbook):
                    return report.Report(logbook, {})
                time.sleep(HEARTBEAT)

            new, results = self._logging_handler.end()
            logbook += new
            if _panic(logbook):
                return report.Report(logbook, results)

        # TODO Put post-processing here!
        return report.Report(logbook, results)


# FIXME code-duplication: simulink.load_details
def load_details(path: str) -> Details:
    """Load testbed details from filesystem path ``path``.

    The file must be a valid YAML file with the following fields:

        - ``devices`` (see ``DeviceDetails`` for details)
        - ``connections`` (see ``infos.ConnectionInfo`` for details)

    Args:
        path: A filesystem path to a YAML file which contains

    Raises:
        OSError: If reading ``path`` fails
        FileNotFoundError: If ``path`` doesn't exist
        KeyError:
            Is the fields ``devices`` or ``connections`` are not defined
        yaml.YAMLError: If the file is not a valid YAML file

    Returns:
        A ``Details`` object which contains the loaded information
    """
    with open(path, 'r') as f:
        content = f.read()
    data = yaml.safe_load(content)

    return _load_details(path, data)


# FIXME code-duplication: pylab.simulink.simulink.Details
@dataclasses.dataclass(frozen=True)
class Details:
    devices: list[DeviceDetails]
    connections: list[infos.ConnectionInfo]

    @classmethod
    def from_dict(cls, data: dict) -> Details:
        details = [DeviceDetails.from_dict(each) for each in data['devices']]
        print(data['connections'])
        connections = [infos.ConnectionInfo(*each)
                       for each in data['connections']]
        return cls(details, connections)


# FIXME code-duplication: pylab.simulink.simulink.DeviceDetails
@dataclasses.dataclass(frozen=True)
class DeviceDetails:
    name: str
    type: str
    interface: infos.ElectricalInterface
    data: dict = dataclasses.field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> DeviceDetails:
        name = data['name']
        type = data['type']
        interface = infos.ElectricalInterface.from_dict(data['interface'])
        args = data.get('data', {})  # FIXME This is awkward...!
        return cls(name, type, interface, args)


# }}} frontend


# command {{{


# FIXME Add __subclasshook__
class AbstractCommand(abc.ABC):
    """ABC for just-in-time commands."""

    def __init__(self, time: float, description: str = ''):
        self._time = time
        self._description = description

    @property
    def time(self) -> float:
        """The (absolute) time of execution of the command."""
        return self._time

    def execute(self, test_object: _TestObject) -> AbstractFuture:
        """Execute the command.

        Args:
            test_object: The ``_TestObject`` to execute the command on.
        """
        pass


class CmdSetSignal(AbstractCommand):

    def __init__(self, time: float, target: str, signal: str,
                 value: ArrayLike, description: str = '') -> None:
        super().__init__(time, description)
        self._target = target
        self._signal = signal
        self._value = value

    def execute(self, test_object: _TestObject) -> AbstractFuture:
        device, port = test_object.trace_back(self._target, self._signal)
        signal = test_object.get_signal(self._target, self._signal)
        value = coreutility.transform(
            signal.min, signal.max, port.min, port.max, self._value)
        return device.execute('set_signal', port.channel, value)


def _create_command(info: infos.CommandInfo, offset: float) -> AbstractCommand:
    """Create ``AbstractCommand`` from info.

    The function will try to look up a command where ``info.type`` is
    not a fully qualified name in *this* module. The ``time`` of the
    newly created command will be the *absolute* time of execution, i.e.
    ``info.time`` shifted by the starting point of the phase that the
    command belongs to.

    Args:
        info: The info to create the command from
        offset:
            The starting point of the phase that the command belongs to
    """
    if '.' in info.command:
        type_ = coreutility.module_getattr(info.command)
    else:
        type_ = globals()[info.command]
    return type_(offset + info.time,
                 info.target,
                 **info.data,
                 description=info.description)


# }}} command


# devices {{{


class AbstractFuture(abc.ABC):
    """Class for managing asynchronous behavior of devices.

    ``AbstractFuture`` objects are the default return values of all
    calls made to devices controlled by the driver.
    """

    @abc.abstractmethod
    def get_result(self) -> Any:
        """Get the result of the computation.

        Shall only be called if the future is done. Calling
        ``get_result`` before done is undefined behavior.
        """
        pass

    @property
    @abc.abstractmethod
    def what(self) -> str:
        """Information on the future.

        This property holds information which may be gathered at any
        point during execution in a thread-safe manner. It should be
        used to assemble an error report if the future times out.
        """
        pass

    @property
    @abc.abstractmethod
    def log(self) -> report.LogEntry:
        """A logbook entry describing the future.

        Shall only be called if the future is done. Calling before done
        is undefined behavior.
        """
        pass

    @property
    @abc.abstractmethod
    def done(self) -> bool:
        """Thread-safely check if the future is done."""
        pass

    @abc.abstractmethod
    def wait(self, timeout: Optional[float] = None) -> bool:
        """Wait for ``timeout`` seconds or until the future is done.

        Args:
            timeout:
                The timeout duration in seconds; ``None`` means no
                timeout

        Returns:
            ``False`` is the operation timed out; ``True`` otherwise

        Raises:
            Implementation-defined exception:
                If the timeout was caused by an internal error
        """
        pass


class NoopFuture(AbstractFuture):
    """Class for synchronous commands or commands without callback.

    This future is always done, and may have any logbook entry or
    result. The purpose of this class is to allow return values to
    synchronous calls to devices or asynchronous calls to devices
    without callback.
    """

    def __init__(self, log: report.LogEntry, result: Optional[Any] = None) -> None:
        self._log = log
        self._result = result

    def get_result(self) -> Any:
        return self._result

    @property
    def what(self) -> str:
        return self._log.what

    @property
    def log(self) -> report.LogEntry:
        return self._log

    def done(self) -> bool:
        return True

    def wait(self, _: Optional[float] = None) -> bool:
        return True


# FIXME Add __subclasshook__!
class AbstractDevice(abc.ABC):
    """ABC for implementation of controlled devices.

    Most of the time, a device will require other methods to function
    properly (depending on what commands are executed).
    """

    @abc.abstractmethod
    def open(self) -> AbstractFuture:
        """Open the device.

        Returns:
            A future which **may** report on the success of the call
        """
        pass

    @abc.abstractmethod
    def close(self) -> AbstractFuture:
        """Close the device.

        Returns:
            A future which **may** report on the success of the call
        """
        pass

    @abc.abstractmethod
    def setup(self) -> AbstractFuture:
        """Setup the device.

        Returns:
            A future which **may** report on the success of the call
        """
        pass


class _Device:
    """Wrapper class for plugin-specific implementation of device."""

    def __init__(self, info: DeviceDetails) -> None:
        self._name = info.name
        cls = coreutility.getattr_from_module(info.type)
        self._implementation: AbstractDevice = cls(**info.data)
        self._interface = info.interface

    @property
    def name(self) -> str:
        """The identifier of the device."""
        return self._name

    @property
    def interface(self) -> info.ElectricalInterface:
        """The device's physical-electrical interface."""
        return self._interface

    def open(self) -> AbstractFuture:
        """Open the wrapped device."""
        return self._implementation.open()

    def close(self) -> AbstractFuture:
        """Close the wrapped device."""
        return self._implementation.close()

    def setup(self) -> AbstractFuture:
        """Setup the wrapped device.

        This method just
        """
        return self._implementation.setup()

    def execute(self, cmd: str, *args, **kwargs) -> AbstractFuture:
        """Execute a command on the wrapped device.

        Args:
            cmd: The command to execute
            *args: Arguments passed to the command call
            **kwargs: Keyworded arguments passed to command call

        We need this method to wrap the AttributeError caused by
        unimplemented methods into a ``LogicError``.
        """
        func = getattr(self._implementation, cmd, None)
        if func is None:
            raise errors.LogicError(f'Failed to execute command {cmd} on device {self._name}')  # TODO
        result = func(*args, **kwargs)
        return result


class UsbSerialDevice(AbstractDevice):
    """Base class for USB serial devices with no other properties.

    Although this class may be used as ``AbstractDevice`` for targets,
    it is better to provide a tailor-made class. The reason for this is
    that, for example, ``open()`` doesn't provide any feedback on the
    success of the execution of the command.
    """

    def __init__(self, ser: serial.Serial) -> None:
        self._serial = ser

    @classmethod
    def from_serial_number(cls, serial_number: str) -> UsbSerialDevice:
        return cls(liveutility.create_serial_device_from_serial_number(serial_number))

    def open(self):
        return NoopFuture(
            report.LogEntry('open', severity='info'))

    def close(self):
        self._serial.close()
        return NoopFuture(
            report.LogEntry('close', severity='info'))

    def setup(self):
        return NoopFuture(
            report.LogEntry('setup', severity='info'))


class _DeviceContextManager:
    """Open/close devices automatically.

    Use to ensure graceful close of devices on panic at any point during
    the execution of the test.
    """

    def __init__(self, test_object: _TestObject, logbook: list[LogEntry]) -> None:
        """Args:
            test_object: The underlying test object
            logbook: A logbook that the manager's activity is written to
        """
        self._test_object = test_object
        self._logbook = logbook

    @property
    def logbook(self) -> list[LogEntry]:
        """The context manager's logbook."""
        return self._logbook

    def __enter__(self):
        self._logbook += self._test_object.open()

    def __exit__(self, type, value, traceback):
        del type, value, traceback
        self._logbook += self._test_object.close()


# }}} devices


# details {{{


# FIXME code-duplication: pylab.simulink.simulink._TestObject
class _TestObject:
    """Utility class for managing the test setup."""

    def __init__(self,
                 details: Details,
                 targets: list[infos.TargetInfo]) -> None:
        self._devices = [_Device(each) for each in details.devices]
        self._connections = [self._create_solid_connection(each)
                             for each in details.connections]
        self._targets = targets

    @property
    def devices(self) -> list[_Device]:
        """The devices in the testbed.

        This property is considered **read-only**.
        """
        return self._devices

    @property
    def connections(self) -> list[_SolidConnection]:
        """The connections between the devices in the testbed.

        This property is considered **read-only**.
        """
        return self._connections

    @property
    def targets(self) -> list[infos.TargetInfo]:
        """The targets in the testbed.

        This property is considered **read-only**.
        """
        return self._targets

    def trace_back(self, target: str, signal: str) -> Tuple[_Device, infos.PortInfo]:
        """Return the output that is connected to the input ``signal``
        of ``target``.

        Raises:
            StopIteration: If ``target`` or ``signal`` are not found
        """
        device = next(each for each in self._devices if each.name == target)
        channel = device.interface.get_port(signal).channel
        line = next(each for each in self._connections
                    if each.receiver.name == target
                    and each.receiver_port.channel == channel)
        return line.sender, line.sender_port

    def trace_forward(self, target: str, signal: str) -> Tuple[_Device, infos.PortInfo]:
        """Return the output that is connected to ``signal`` of
        ``target``.

        Raises:
            StopIteration: If ``target`` or ``signal`` are not found
        """
        print(target)
        print(self._devices)
        print([each.name for each in self._devices])
        device = next(each for each in self._devices if each.name == target)
        channel = device.interface.get_port(signal).channel
        line = next(each for each in self._connections
                    if each.sender.name == target
                    and each.sender_port.channel == channel)
        return line.receiver, line.receiver_port

    def get_signal(self, target: str, signal: str) -> infos.SignalInfo:
        """Return the info of ``signal`` from ``target``.

        Raises:
            ValueError: If ``target`` or ``signal`` are not found
        """
        target_obj = next((each for each in self._targets if each.name == target), None)
        if target_obj is None:
            raise ValueError(f'Target "{target}" not found')
        signal_obj = next(each for each in target_obj.signals if each.name == signal)
        if signal_obj is None:
            raise ValueError(f'Target "{target}" has no signal "{signal}"')
        return signal_obj

    def make_logging_request(self, info: infos.LoggingInfo) -> _LoggingRequest:
        """Create a logging request from info.

        Args:
            info: The info used for creation

        Raises:
            StopIteration: If ``target`` or ``signal`` are not found
        """
        device, port = self.trace_forward(info.target, info.signal)
        signal = self.get_signal(info.target, info.signal)

        def transform(value):
            return coreutility.transform(port.min, port.max,
                                         signal.min, signal.max, value)
        return _LoggingRequest(info, transform)

    def _execute_for_all_and_wait(self,
                                  attr: str,
                                  *args,
                                  timeout: Optional[float] = None,
                                  **kwargs) -> list[report.LogEntry]:
        """Execute a call on all devices and wait until done.

        Args:
            attr: The name of the method to call
            *args: Positional arguments passed to method
            timeout: Timeout for wait in seconds
            **kwargs: Keyworded arguments passed to method
        """
        futures = [getattr(each, attr)(*args, **kwargs) for each in self._devices]
        return _wait_for_all(futures, timeout)

    def open(self, timeout: Optional[float] = None) -> list[report.LogEntry]:
        """Open all devices in the testbed and wait until done.

        Args:
            timeout: Timeout for wait in seconds
        """
        return self._execute_for_all_and_wait('open', timeout=timeout)

    def close(self, timeout: Optional[float] = None) -> list[report.LogEntry]:
        """Close all devices in the testbed and wait until done.

        Args:
            timeout: Timeout for wait in seconds
        """
        return self._execute_for_all_and_wait('close', timeout=timeout)

    def setup(self, timeout: Optional[float] = None) -> list[report.LogEntry]:
        """Setup all devices in the testbed and wait until done.

        Args:
            timeout: Timeout for wait in seconds
        """
        return self._execute_for_all_and_wait('setup', timeout=timeout)

    def _create_solid_connection(self, info: infos.ConnectionInfo) -> _SolidConnection:
        """Create a solid connection from ``info``.

        Raises:
            StopIteration:
                If ``info.sender`` and ``info.receiver`` are
                not found in the list of devices
        """
        sender = next(each for each in self._devices
                      if each.name == info.sender)
        sender_port = sender.interface.get_port(info.sender_port)
        receiver = next(each for each in self._devices
                        if each.name == info.receiver)
        receiver_port = receiver.interface.get_port(info.receiver_port)
        return _SolidConnection(sender, sender_port, receiver, receiver_port)


class _LoggingRequest(AbstractFuture):
    """Utility class for logging requests.

    Each instance contains a ``infos.LoggingInfo`` and a transformation
    from electrical to physical values of the logged signal.
    """

    def __init__(self,
                 info: infos.LoggingInfo,
                 transform: Callable[[ArrayLike], ArrayLike]) -> None:
        """Initialize logging request from info and electric to physical
        transform.

        Args:
            info: Wrapped logging info
            transform: Electrical-physical transform
        """
        self._info = info
        self._transform = transform
        self._future: AbstractFuture = None

    def begin(self, test_object: _TestObject) -> AbstractFuture:
        """Begin logging the signal.

        Args:
            test_object: The underlying TestObject

        Returns:
            A future which is done if the logging request is accepted
        """
        device, port = test_object.trace_forward(self._info.target, self._info.signal)
        future, self._future = device.execute(
            'log_signal', port.channel, self._info.period)
        return future

    def end(self, test_object: _TestObject) -> AbstractFuture:
        """End logging the signal.

        Args:
            test_object: The underlying TestObject

        Returns:
            A future which is done when the request for closing the
            logging request is accepted

        Note that if the returned future is done only the *request* for
        closing the request was accepted. It does not mean that the
        logging request is done.
        """
        device, port = test_object.trace_forward(self._info.target, self._info.signal)
        return device.execute('end_log_signal', port.channel)

    @property
    def what(self) -> str:
        return self._future.what

    @property
    def log(self) -> LogEntry:
        return self._future.log

    def wait(self, timeout: Optional[float] = None) -> None:
        self._future.wait(timeout)

    @property
    def done(self) -> bool:
        """Check if the logging request is done."""
        return self._future.done

    @property
    def full_name(self):
        """The namespace qualified name of the logged signal."""
        return self._info.full_name()

    def get_result(self) -> Tuple[report.LogEntry, timeseries.TimeSeries]:
        """Return logged result.

        Shall only be called if the logging request is done.
        """
        assert self.done
        ts = self._future.get_result()
        ts.kind = self._info.kind
        ts.transform(self._transform)
        return ts


class _DeadlineFuture:
    """Class for futures whose underlying computation may timeout.

    Note that ``_DeadlineFuture`` isn't a subclass of ``AbstractFuture``,
    as ``_DeadlineFuture.log`` may be called even if the Future isn't
    done.
    """

    def __init__(self, future: AbstractFuture, timeout: Optional[float] = None) -> None:
        self._future = future
        if timeout is not None:
            self._deadline = time.time() + timeout
        else:
            self._deadline = None

    @property
    def timed_out(self) -> bool:
        """Check if the future is timed out."""
        return self._deadline is not None and time.time() > self._deadline

    @property
    def done(self) -> bool:
        return self._future.done

    @property
    def log(self) -> report.LogEntry:
        if self.timed_out:
            return _timed_out_report(self._future)
        return self._future.log

    def force_wait(self):
        """Trigger side-effect of ``wait`` after timeout."""
        self._future.wait(0.0)


class _FutureController:
    """Utility class for managing a collection of futures."""

    def __init__(self):
        self._futures = []

    def put(self, future: AbstractFuture, timeout: Optional[float] = None) -> None:
        """Pass ownership of future to the controller and imbue it with
        a timeout.

        Args:
            future: The future to take control of
            timeout: The timeout in seconds
        """
        if timeout is not None:
            timeout = time.time() + timeout
        self._futures.append(_DeadlineFuture(future, timeout))

    def run(self) -> list[report.LogEntry]:
        """Check all controlled futures for completion.

        This method will remove any controlled futures that are done and
        return a logbook detailing the results. If any of the futures
        timed out *with proper cause* then this method will raise that
        error.

        Returns:
            The log entries of the completed futures

        Raises:
            Implementation-defined error:
                If any of the futures timed out
        """
        # TODO Abstract these pairs into a class, with a timeout method
        logbook = [elem.log for elem in self._futures if elem.done]
        self._futures[:] = [elem for elem in self._futures if not elem.done]
        timed_out = [elem for elem in self._futures if elem.timed_out]
        for elem in timed_out:
            elem.force_wait(0.0)
            # FIXME This is really ugly, but this forces a raise on a
            # timed out future (if available)! Design-wise, this seems
            # stange, as well. Why would we only raise if we know
            # exactly what's going on?
        logbook += [elem.log for elem in timed_out]
        return logbook


def _wait_for_all(futures: list[AbstractFuture],
                  timeout: Optional[float] = None) -> list[report.LogEntry]:
    """Wait for specified futures.

    Args:
        futures: The futures to wait on
        timeout: A timeout in seconds

    Returns:
        A list of log reports for the futures (even on timeout)
    """
    done = [elem.wait(timeout) for elem in futures]
    # FIXME This is incorrect. You're warning about _all_ futures, not
    # just those that actually timed out - Separate timed out futures
    # from the rest!
    if not all(done):
        return [_timed_out_report(elem) for elem in futures]
    return [each.log for each in futures]


def _timed_out_report(future: AbstractFuture) -> report.LogEntry:
    return report.LogEntry(
        what='Timed out waiting for the following future: ' + future.what,
        severity=report.PANIC
    )


class _LoggingHandler:
    """Utility class for handeling ``_LoggingRequest`` objects."""

    def __init__(self,
                 test_object: _TestObject,
                 infos: list[infos.LoggingInfo]) -> None:
        """Args:
            test_object: The underlying test object
            infos: Infos for the handled logging requests
        """
        self._test_object = test_object
        self._requests = [self._test_object.make_logging_request(each) for each in infos]

    def begin(self, timeout: Optional[float] = None) -> list[report.LogEntry]:
        """Begin submitting the managed logging requests.

        Args:
            timeout: A timeout for the successfull submission in seconds

        Returns:
            A list of log reports for the futures (even on timeout)
        """
        futures = [elem.begin(self._test_object) for elem in self._requests]
        return _wait_for_all(futures, timeout)

    def end(self) -> Tuple[list[report.LogEntry], dict[str, timeseries.TimeSeries]]:
        """End the submitted logging requests.

        Returns:
            A logbook detailing the success or failure and a dictionary
            of the logged results
        """
        # FIXME Implement timeouts!
        futures = [each.end(self._test_object) for each in self._requests]
        logbook = _wait_for_all(futures)

        for elem in self._requests:
            elem.wait()
        logbook += [elem.log for elem in self._requests]
        results = {elem.full_name: elem.get_result() for elem in self._requests}

        return logbook, results


# FIXME Abstract this using a LogBook class
def _panic(logbook: list[report.LogEntry]) -> bool:
    return any(elem.severity == report.PANIC for elem in logbook)


@dataclasses.dataclass(frozen=True)
class _SolidConnection:
    sender: _Device
    sender_port: infos.PortInfo
    receiver: _Device
    receiver_port: infos.PortInfo


# FIXME code-duplication: simulink._load_details
def _load_details(path: str, data: dict) -> Details:
    device_data = data.get('devices', {})
    # If this is not available, we're not throwing an error just yet

    # If an interface info is a string, use it as a filesystem path to
    # find the file which holds the actual interface info data. If
    # ``data`` is a relative path, view it as relative to ``path``.
    for elem in device_data:
        inf = elem['interface']
        if isinstance(inf, str):
            interface_path = _find_interface_path(path, inf)
            elem['interface'] = _yaml_safe_load_from_file(interface_path)
    return Details.from_dict(data)


# FIXME core-duplication: pylab.core.loader._find_phase_path
def _find_interface_path(root: str, path: str) -> str:
    """Find an interface file.

    Args:
        root: Path to the test file which contains a reference to the
              interface file
        path: Absolute or relative path to a interface file

    We try to interpret ``path`` as filesystem path and find the file it
    is pointing to. If ``path`` is relative, the function searches the
    folder containing the original test file (``root``).

    Note that this function does not check if any of the candidates is
    in fact a valid interface file (i.e. has the correct fields, etc.).

    Returns:
        A path to an existing file

    Raises:
        ValueError:
            If none of the viable interpretations leads to an
            existing file
    """
    if posixpath.isabs(path):
        if posixpath.exists(path):
            return path
        raise ValueError(f'File {path} not found')

    paths = [posixpath.join(posixpath.dirname(root), path)]  # Candidates for path.
    for each in paths:
        if posixpath.exists(each):
            return each

    raise ValueError(f'File {path} not found')


# FIXME code-duplication: pylab.core.loader._yaml_safe_load_from_file
def _yaml_safe_load_from_file(path: str) -> dict:
    with open(path, 'r') as f:
        content = f.read()
    return yaml.safe_load(content)


# }}} details
