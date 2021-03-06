# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""MATLAB/Simulink implementation of the pylab specification.

Requirements:
    - MathWork's MATLAB/Simulink python engine: ``matlab>=R2020a``.

In the documentation of this module, by the _handle_ of an object, we
shall always mean the MATLAB/Simulink handle (type ``float``), unless
stated otherwise. Furthermore, we shall identify an object's handle with
the object itself in an attempt to prevent excessive use of phrases like
"the model with handle ``model``".

Every device corresponds to a block in the _root system_, which is the
basis of the simulation. Connections defined in the details file
correspond to lines drawn between the blocks representing the devices.
The details file must satisfy the following specification.

1 There must be a ``devices`` field, which is a list whose elements
  *must* have the following fields:

  - ``name`` (str): The unique identifier of the device.
  - ``type`` (str): A Python function which returns an object of a
    subclass of ``AbstractBlock``.
  - ``interface`` (map): A list of data from which ``pylab.shared.infos.PortInfo``
    objects can be created.

  If the device implements a target, then it *must* carry the same
  ``name`` as the target and map the target's interface.

  If ``type`` is not a fully qualified name, then pylab tries to look it
  up in ``simulink.blocks``.

  The elements *may* also have a ``data`` field, which must satisfy the
  following condition: After loading ``data``, its contents may be
  passed as keyworded arguments to the function of the class given by
  the ``type`` field.

  Note that ``type`` may be a Python class.

  For more details, see the documentation of ``simulink.blocks``.

2 There must be a ``connections`` field, whose elements are 4-tuples of
  the following form:

    (sender, sender_port, receiver, receiver_port)

  Specifying a device or a port that doesn't exist is undefined
  behavior.

  Every port that is stimulated and every port that is logged *must* be
  connected to a device with the respective stimulating and logging
  capability.
"""

from __future__ import annotations

import abc
import collections
import dataclasses
import importlib.resources
import io
import json
import math
import os
import shutil
import tempfile

import matlab
import pydantic
import yaml
from typing import Any, Dict, List, Optional

from pylab._private import utils as privateutils
from pylab.shared import testobject
from pylab.shared import infos as sharedinfos
from pylab.shared import loader
from pylab.core.typing import ArrayLike
from pylab.simulink import _engine
from pylab.core import timeseries
from pylab.core import utils
from pylab.core import transform
from pylab.core import infos
from pylab.core import report

PREFIX = "PYLAB"
PREFIX_LOWER = "pylab"
DELIM_LEFT = "%{"
DELIM_RIGHT = "%}"
SYSTEM = PREFIX + "_SYSTEM"
SIMOUT = PREFIX + "_SIMOUT"
OUTPUT = PREFIX + "_OUTPUT"
LOGBOOK = PREFIX + "_LOGBOOK"
WHAT = PREFIX + "_WHAT"
ERROR = PREFIX + "_ERROR"
OPERATING_POINT = PREFIX + "_OPERATING_POINT"
FILENAME = PREFIX + "_SCRIPT.m"
EXTRACT = PREFIX_LOWER + "_extract"
DOT = PREFIX + "DOT"
RESOURCES = "pylab.simulink._resources"
TOOLBOX = [f"{EXTRACT}.m"]
BINARIES = ["pylab_mini_generator.slx"]
INDEX0 = PREFIX + "_INDEX0"

MARKER = "-->"  # Marks lines in script that cause MATLAB errors

BLOCKS = "pylab.simulink.blocks"
COMMANDS = "pylab.simulink.commands"
GRAIN = 0.1

# FIXME Raise correct error when executing commands on devices which
# don't support them

# FIXME Raise correct error when converting physical/electrical values
# that are out-of-bounds

# FIXME The ``Test`` class and logging should be decoupled from the
# concept of `signal`. In other words, ``Test`` and ``_LoggingRequest``
# should work just based on variable names, not on mangled names. This
# will make unit-testing ``Test`` easier.


# frontend {{{


def create(info: infos.TestInfo, details: Details) -> Test:
    """Create and return a ``Test`` object from info and device details.

    Raises:
        core.errors.LogicError: If ``info`` violates the specification
    """
    test_object = TestObject(details, info.targets)
    pull = [test_object.create_logging_request(each) for each in info.logging]
    code = _head()
    code += test_object.setup()
    print(code)

    logging = [test_object.start_logging(each) for each in info.logging]
    code += sum([each.execute() for each in logging], [])

    offset = 0.0
    commands: list[Command] = []
    for phase in info.phases:
        commands += [
            test_object.create_command(each, offset) for each in phase.commands
        ]
        offset += phase.duration
    total_duration = offset
    commands.sort(key=lambda cmd: cmd.time)
    commands = collections.OrderedDict(
        sorted(utils.split_by_attribute(commands, "time").items())
    )

    last = 0.0
    for time, sublist in commands.items():
        if not math.isclose(time, 0.0, abs_tol=GRAIN, rel_tol=0.0):
            code += _simulate(time)
            last = time
        for each in sublist:
            code += each.execute()
    if not math.isclose(last, total_duration, abs_tol=GRAIN, rel_tol=0.0):
        code += _simulate(total_duration)

    for each in info.logging:
        code += _concat_output(each)

    code += _catch_block()

    test = Test("\n".join(code), pull)
    return test


class Test:
    """Test object representing a pylab test in the form of a MATLAB .M
    file.
    """

    def __init__(self, code: str, logging_requests: list[_LoggingRequest]) -> None:
        """Initialize ``Test`` object.

        Args:
            code: MATLAB source code
            logging_requests: Signal logging requests
        """
        self._code = code
        self._logging_requests = logging_requests

    def execute(self) -> report.Report:
        """Execute the test and return a report including logged data.

        The .M file is called from a temporary directory, so there
        should be no side-effects for the file system. The temporary
        directory will contain copies of the .M files listed in
        ``TOOLBOX`` and found in ``pylab.simulink._resources``.
        """
        engine = _engine.Engine()
        with tempfile.TemporaryDirectory() as tmpdir:
            for each in TOOLBOX:
                raw = importlib.resources.read_text(RESOURCES, each)
                with open(os.path.join(tmpdir, each), "w") as f:
                    f.write(raw)

            for each in BINARIES:
                raw = importlib.resources.read_binary(RESOURCES, each)
                with open(os.path.join(tmpdir, each), "wb") as f:
                    f.write(raw)

            path = os.path.join(tmpdir, FILENAME)
            with open(path, "w") as f:
                f.write(self._code)

            engine.run_script_from_file(path)

        logbook = engine.workspace()[LOGBOOK]
        logbook = _pull_logbook(logbook)
        failed = any(each.failed for each in logbook)

        if failed:
            results = {}  # FIXME Try to pull as much information as possible.
            code = self._code
            for log in logbook:
                stack = log.data.get("stack")
                if stack is not None:
                    line = int(stack[0]["line"])
                    code = _mark_line(code, line)
            data = {"script": code, "requests": self._logging_requests}
        else:
            results = {
                each.path(): each.result(engine) for each in self._logging_requests
            }
            data = {}

        return report.Report(logbook, results, data)


@pydantic.dataclasses.dataclass(frozen=True)
class DeviceDetails:
    name: str
    interface: sharedinfos.ElectricalInterface
    type: str
    data: Optional[Dict] = pydantic.Field(default_factory=dict)  # TODO Rename to args!


@pydantic.dataclasses.dataclass(frozen=True)
class Details:
    devices: List[DeviceDetails]
    connections: List[sharedinfos.ConnectionInfo]


def load_details(path: str) -> Details:
    """Load testbed details from filesystem path ``path``.

    The file must be a valid YAML file with the following fields:

        - ``devices`` (see ``DeviceDetails`` for details)
        - ``connections`` (see ``pylab.shared.infos.ConnectionInfo`` for details)

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
    data = privateutils.yaml_safe_load_from_file(path)
    return _load_details(path, data)


# }}} frontend


# logging {{{


class _LoggingRequest:
    """Utility class for logging requests.

    Each instance contains a ``infos.LoggingInfo`` and a transformation
    from electrical to physical values of the logged signal.
    """

    def __init__(
        self, info: infos.LoggingInfo, transform: Callable[[ArrayLike], ArrayLike]
    ) -> None:
        """Initialize logging request from info and electric to physical
        transform.

        Args:
            info: Wrapped logging info
            transform: Electrical-physical transform
        """
        self._info = info
        self._transform = transform

    def path(self):
        """Return namespace qualified name of the logged signal."""
        return f"{self._info.target}.{self._info.signal}"

    def result(self, engine: _engine.Engine) -> timeseries.TimeSeries:
        """Pull logged result from MATLAB workspace.

        Should only be called from inside ``Test.execute`` after the
        test was run.

        Raises:
            matlab.engine.MatlabExecutionError:
                If the logged data cannot be found in the MATLAB
                workspace.
        """
        # TODO The result should be allowed to be something other than a
        # timeseries.
        ts = engine.timeseries_to_python(engine.workspace()[self._mangled_name()])
        ts.kind = self._info.kind
        ts.transform(self._transform)
        return ts

    def _mangled_name(self):
        """Return the variable name of logged data in MATLAB
        workspace.
        """
        return f"{OUTPUT}_{_unpack_log_entry(self._info)}"


def _pull_logbook(logbook: Union[list[str], str]) -> list[report.LogEntry]:
    """Pull the logbook from the MATLAB namespace.

    Should only be called from inside ``Test.execute`` after the test
    was run.

    Raises:
        matlab.engine.MatlabExecutionError:
            If the logged data cannot be found in the MATLAB
            workspace.
    """
    if isinstance(logbook, str):
        logbook = [logbook]
    logbook = [report.LogEntry(**json.loads(each)) for each in logbook]
    # Replace string with ``report._Severity`` object.
    for elem in logbook:
        elem.severity = utils.getattr_from_module(
            "pylab.core.report." + elem.severity.upper()
        )
    return logbook


def _unpack_log_entry(info: infos.LoggingInfo) -> str:
    """Return the mangled version of the namespace qualified name of the
    signal in ``info`` for use in MATLAB .M files.
    """
    return f"{info.target}{DOT}{info.signal}"


def _pack_log_entry(var: str) -> str:
    """Return the unmangled version of the mangled signal name ``var``.

    Args:
        var:
            A mangled signal name of the form
            ``OUTPUT_{target}DOT{signal}``.
    """
    var = var[len(f"{OUTPUT}_") :]
    var = var.replace(DOT, ".")
    return var


# }}} logging


# .M files {


def _head() -> list[str]:
    """Return the standard .M file header."""
    result = []
    result.append(f"{LOGBOOK} = []")
    result.append(f"{OUTPUT} = []")
    result.append(f'{WHAT} = ""')

    result.append(f"try")  # noqa: F541

    result.append(f'{WHAT} = "Initializing root system"')
    result.append(f"new_system('{SYSTEM}')")
    result.append(f"set_param('{SYSTEM}', ...")
    result.append(f"          'SaveFinalState', 'on', ...")  # noqa: F541
    result.append(f"          'FinalStateName', '{OPERATING_POINT}', ...")
    result.append(f"          'SaveOperatingPoint', 'on')")  # noqa: F541
    result.append(f"{LOGBOOK} = [{LOGBOOK}; ...")
    result.append(
        '  "{""what"": """ + '
        + WHAT
        + ' + """, ""severity"": ""info"", ""data"": {}}"]'
    )

    return result


def _catch_block() -> list[str]:
    """Return the standard .M file catch block."""
    result = []
    result.append(f"catch {ERROR}")
    result.append('data = "{"')

    result.append(f"identifier = strrep({ERROR}.identifier, '\"', '''')")
    result.append(
        f'data = data + """identifier"": """ + identifier + """, "'
    )  # noqa: F541

    result.append(f"message = strrep({ERROR}.message, '\"', '''')")
    result.append(f'data = data + """message"": """ + message + """, "')  # noqa: F541

    result.append(f'data = data + """stack"": ["')  # noqa: F541
    result.append(f"for {INDEX0} = 1:length({ERROR}.stack)")
    result.append(f"  item = {ERROR}.stack({INDEX0})")
    result.append('  data = data + "{"')
    result.append(f'  data = data + """file"": """ + item.file + """, "')  # noqa: F541
    result.append(f'  data = data + """name"": """ + item.name + """, "')  # noqa: F541
    result.append(f'  data = data + """line"": """ + item.line + """"')  # noqa: F541
    result.append('  data = data + "}"')  # noqa: F541

    result.append(f"  if {INDEX0} ~= length({ERROR}.stack)")
    result.append(f'    data = data + ", "')  # noqa: F541
    result.append(f"  end")  # noqa: F541
    result.append(f"end")  # noqa: F541
    result.append(f'data = data + "]"')  # noqa: F541

    result.append('data = data + "}"')  # noqa: F541

    result.append(f"{LOGBOOK} = [{LOGBOOK}; ...")
    result.append(
        '  "{""what"": """ + '
        + WHAT
        + ' + """, ""severity"": ""panic"", ""data"": " + data + "}"]'
    )

    result.append(f"end")  # noqa: F541

    return result


def _simulate(time: float) -> list[str]:
    """Return code snippet running a simulation on the root system for
    ``time`` seconds.
    """
    result = []
    result.append(f"{SIMOUT} = sim('{SYSTEM}', 'StopTime', '{time}')")
    result.append(f"{OPERATING_POINT} = {SIMOUT}.{OPERATING_POINT}")
    result.append(f"set_param('{SYSTEM}', 'LoadInitialState', 'on', ...")
    result.append(f"          'InitialState', '{OPERATING_POINT}')")
    result.append(f"{OUTPUT} = [{OUTPUT} {SIMOUT}]")
    return result


def _concat_output(info: infos.LoggingInfo) -> list[str]:
    """Return code snippet for concatenating the list of output
    timeseries associated with ``info``.
    """
    var = _unpack_log_entry(info)
    return [f"{OUTPUT}_{var} = {EXTRACT}({OUTPUT}, '{var}')"]


# }}} .M files


# commands {


class Command:
    """Class for internally representing pylab commands as MATLAB code
    snippets.
    """

    def __init__(self, time: float, code: str, what: str = "") -> None:
        """Initialize ``Command`` with MATLAB code snippet.



        def _find_nth(text: str, pattern: str, n: int) -> int:
            index = -1
            for _ in range(n):
                offset = index + 1
                index = text[offset:].find(pattern) + offset
            return index


        def _mark_line(text: str, line: int) -> str:
            if line == 0:
                return MARKER + text
            index = _find_nth(text, '\n', line-1)
            return text[:index+1] + MARKER + text[index+1:]
                Args:
                    time: Time at which the command should be executed
                    code: MATLAB code snippet
                    what: Log message
        """
        self._time = time
        self._code = code
        self._what = what

    def __repr__(self) -> str:
        return f"Command(time={self._time}, code={self._code}, what={self._what})"

    @property
    def time(self) -> float:
        """The time at which the command is run."""
        return self._time

    def execute(self) -> list[str]:
        """Return the code snippet for running the command ``self``."""
        result = []
        result.append(f'{WHAT} = "{self._what}"')
        result += self._code
        result.append(f"{LOGBOOK} = [{LOGBOOK}; ...")
        result.append(
            '  "{""what"": """ + '
            + WHAT
            + ' + """, ""severity"": ""info"", ""data"": {}}"]'
        )
        return result


# }}} commands


# models {{{


class AbstractBlock(abc.ABC):
    """ABC for Simulink blocks in the root system.

    Third-party libraries should implement this interface to add their
    custom blocks to the pylab ecosystem.
    """

    def setup(self) -> list[str]:
        """Return code snippet for adding ``self`` to the root
        system.
        """
        pass

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """The name of the underlying Simulink block."""
        pass

    @property
    @abc.abstractmethod
    def absolute_path(self) -> str:
        """The absolute path of the underlying Simulink block."""
        pass


# }}} models


# details {{{


@dataclasses.dataclass(frozen=True)
class Device:
    """Wrapper that wraps a Simulink block and electrical interface."""

    name: str
    block: AbstractBlock
    interface: pylab.shared.infos.ElectricalInterface

    @classmethod
    def from_details(cls, details: DeviceDetails) -> Device:
        if "." in details.type:
            type_ = utils.getattr_from_module(details.type)
        else:  # No absolute path specified, use local block module!
            type_ = utils.getattr_from_module(BLOCKS + "." + details.type)
        block = type_(details.name, **details.data)
        return Device(details.name, block, details.interface)

    def find_port(self, signal: str) -> infos.PortInfo:
        return self.interface.get_port(signal)


class TestObject(testobject.TestObjectBase):
    """Utility class for managing the test setup."""

    def __init__(self, details: Details, targets: list[infos.TargetInfo]) -> None:
        super().__init__(
            [Device.from_details(each) for each in details.devices], details.connections
        )
        print(details.connections)
        self._targets = targets

    @property
    def devices(self) -> list[Device]:
        """The devices/blocks in the testbed/root system.

        This property is considered **read-only**.
        """
        return self._devices

    @property
    def targets(self) -> list[infos.TargetInfo]:
        """The target infos of the test.

        This property is considered **read-only**.
        """
        return self._targets

    def create_logging_request(self, info: infos.LoggingInfo) -> _LoggingRequest:
        """Convert a logging info into a logging request.

        Essentially this methods computes electric-to-physical transform
        and wraps it into a ``_LoggingRequest`` object, along side the
        original ``info``.
        """
        signal = self.get_signal(info.target, info.signal)
        device = next(each for each in self._devices if each.name == info.target)
        port = device.interface.get_port(info.signal)
        tf = transform.AffineMap.affine_range_transform(port.range, signal.range)
        return _LoggingRequest(info, tf)

    def start_logging(self, info: infos.LoggingInfo) -> Command:
        """Create a ``Command`` objects which initiates logging by
        configuring the logger.
        """
        print(info)
        # FIXME Why is this a _Command_? Shouldn't it just be a code block?
        var = _unpack_log_entry(info)
        period = info.period
        what = str(info)

        this_port = self.find_device(info.target).find_port(info.signal)
        if "input" in this_port.flags:
            print("Input")
            # If we're trying to log an input, then try to log the source instead.
            device, port = next(self.trace_back(info.target, info.signal))
            target = device.name
            signal = port.signal
            print(target)
            print(signal)
        else:
            print("output")
            target = info.target
            signal = info.signal

        device, port = next(
            (
                (device, port)
                for device, port in self.trace_forward(target, signal)
                if hasattr(device.block, "log_signal")
            ),
            (None, None),
        )
        if device is None:
            raise 
        code = device.block.log_signal(var, port.channel, period)
        return Command(None, code, what)

    def create_command(self, command_info: infos.CommandInfo, offset: float) -> Command:
        """Create pylab command from command info.

        Note that the execution time is shifted from local (phase) time
        to global (test) time.
        """
        time = command_info.time + offset

        if "." in command_info.command:
            factory = utils.getattr_from_module(command_info.command)
        else:
            factory = utils.getattr_from_module(COMMANDS + "." + command_info.command)
        code, what = factory(self, command_info, time)

        return Command(time, code, what)

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

    def setup(self):
        """Return code snippet for creating the referenced blocks and
        links.
        """
        result = []
        result += sum([each.block.setup() for each in self._devices], [])
        result += sum([self._setup_line(each) for each in self._connections], [])
        return result

    def _setup_line(self, connection: sharedinfos.ConnectionInfo) -> list[str]:
        # TODO This needs to be fixed when the specification how
        # connections are specified is changed
        sender = self.find_device(connection.sender)
        sender_channel = sender.find_port(connection.sender_port).channel
        receiver = self.find_device(connection.receiver)
        receiver_channel = receiver.find_port(connection.receiver_port).channel
        result = [
            f"add_line('{SYSTEM}', '{connection.sender}/{sender_channel}', "
            f"'{connection.receiver}/{receiver_channel}', 'autorouting', 'on')"
        ]
        return result


def _find_nth(text: str, pattern: str, n: int) -> int:
    """Find `n`th occurence of `pattern` in `text`.

    Returns:
        The index at which the `n`th occurence starts
    """
    index = -1
    for _ in range(n):
        offset = index + 1
        index = text[offset:].find(pattern) + offset
    return index


def _mark_line(text: str, line: int) -> str:
    """Mark line `line` in `text` with a marker."""
    if line == 0:
        return MARKER + text
    index = _find_nth(text, "\n", line - 1)
    return text[: index + 1] + MARKER + text[index + 1 :]


def _load_details(path: str, data: dict) -> Details:
    device_data = data.get("devices", {})
    # If this is not available, we're not throwing an error just yet

    # If an interface info is a string, use it as a filesystem path to
    # find the file which holds the actual interface info data. If
    # ``data`` is a relative path, view it as relative to ``path``.
    for elem in device_data:
        inf = elem["interface"]
        if isinstance(inf, str):
            interface_path = loader.find_relative_path(path, inf)
            elem["interface"] = privateutils.yaml_safe_load_from_file(interface_path)
    return Details(**data)


# }}} details
