# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""pylab live plugin for Saleae Logic 1 Legacy.

Requirements:

    - Saleae Logic 1.1.x Legacy
    - saleae-python

The details are loaded from file. File *may* have an extension field
`saleae`, which *may* contain the following fields:

* host (str): The host running Logic
* port (int): The port of the socket API
* performance (str): One of the following: 'Full', 'Half', 'Third',
  'Quarter', 'Low'
* grace (float): The grace period used for the recording length
  heuristics (see below)
* triggers (dict[int, str]): A dict mapping digital channels to their
  trigger setting. An undefined trigger leave the setting at default.
  Allowed settings are: 'NoTrigger', 'High', 'Low', 'Posedge',
  'Negedge'. At least one of the settings must be 'Posedge' or 'Negedge'
  or all must be 'NoTrigger' (but that's the default setting anyways)

If so, then these are used to configure the Saleae Logic client. If not,
the following defaults are used: ``host='localhost'``, ``port=10429``,
``performance='Full'``, ``grace=5.0``.

The plugin currently suffers from serious restrictions:

- At most one logic analyzer may be operated at the same time. Creating
  more than a single ``Device`` object will result in a
  ``RuntimeError``.

- The time the recording starts cannot be determined using the Socket
  API and recording cannot be stopped manually, which is why the plugin
  uses a heuristic grace period to determine when recording starts, thus
  creating quite long recordings, even for short tests. Note that this
  may lead to excessive memory consumption and long wait times _after_
  the test.

Both of these are caused by limitations of the API. Indeed, the Logic
Socket API is, by nature, synchronous, i.e. you send a command and then
wait for the ACK, then send another command, etc. (there are exceptions
to this, see below). Sending messages out-of-turn will result in
undefined behavior. Furthermore, the ``capture`` command only ACKs
_after_ the recording is done. So it is not possible to know when a
recording has started. For details, see:

* https://discuss.saleae.com/t/is-there-a-way-to-get-ack-when-the-capture-starts/1023

* https://ideas.saleae.com/b/feature-requests/application-api/

* https://github.com/ppannuto/python-saleae/issues/18

The exception mentioned above is detailed in
github.com/ppannuto/python-saleae/issues/18, which uses a trick to
circumvent a certain problem found in C# API Docs. The C# API docs say:

  Socket Command: stop_capture

  This command stops the current capture. This command will return
  ``NAK`` if no capture is in progress.

  If a capture is in progress, it does not return a response. Instead,
  it initiates the end of the capture, and then the active capture
  command will send it's reply, either a ``ACK`` if any data is
  recorded, or a ``NAK`` if the capture was terminated before the
  trigger condition was found.

  Use this function with care, as a race condition determines if one or
  two responses will be returned. This will be improved in future
  versions of the socket API and C# wrapper.

  Specifically, if the stop_capture command is issued near
  simultaneously with the normal end of the capture, it is possible to
  get a single ``ACK`` response or two responses, ``ACK`` followed by
  ``NAK``. The first is the case where the stop command ends the capture
  early, and the second case is when the stop command is applied after
  the capture has already completed, returning ``NAK``.
  [https://github.com/saleae/SaleaeSocketApi/blob/master/Doc/Logic%20Socket%20API%20Users%20Guide.md]

To summarize: When issued while a capture in progress, *the
``stop_capture`` command may be issued out-of-turn*.

The python-saleae API exploits this as follows. Like the Socket
API, it is synchronous, so issueing a command to the socket API by
calling ``Saleae._cmd`` usually means that ``_cmd`` blocks until a reply
is received. However, ``Saleae.capture_start`` does not wait for an
``ACK`` from the Socket API, but returns immediately instead. This
allows ``Saleae.capture_stop``, which issues the ``stop_capture``
command to the Socket API, to read the reply to the ``start_capture``
command, which, according to the quote above, will be ``ACK`` if data
was recorded and ``NAK`` otherwise. This way, a capture in progress may
be stopped, even using the synchronous API, but failing to ensure that
``stop_capture`` is issued while a capture is in progress will result in
undefined behavior. To ensure this is this plugin's job.

Of course, due to the many moving parts of the live driver, no absolute
guarantee can be given, but using the grace period, the following
fashion gives reasonable safety:

- The future which signals success or failure in starting a recording
  will wait for ``_grace`` seconds until done. The larger ``_grace`` is
  the higher the probability that the capture is, in fact, in progress.

- The recording length is set to ``GRACE + _grace + 2*total_duration_of_test``.
  Given that the ``GRAIN`` of the live driver is a fraction of a second,
  we expect ``GRACE`` (the internal grace period constant) to be
  sufficient if ``>1.0``, even if the user uses more liberal grace
  period themselves and/or the test is suprisingly short.

These should guarantee that, when the ``end_log_signal`` command is
issued to the Saleae plugin at the end of the test (after roughly
``total_duration_of_test + epsilon`` seconds have passed), the capture
is still in progress.
"""

# TODO Is there any disadvantage to setting ``GRACE`` to ``1_000_000``
# and just be done with the problem?

from __future__ import annotations

import csv
import dataclasses
import os
import tempfile
import threading
import time

import saleae
from numpy.typing import ArrayLike

from pylab.live import live
from pylab.core import report
from pylab.core import timeseries
from pylab.live.plugin.saleae import _parser

_logic = None
_grace = None  # Grace period in seconds, set by the user
_triggers = None

GRAIN = 0.1
GRACE = 1.0


def init(info: infos.TestInfo, details: live.Details) -> None:
    duration = sum(phase.duration for phase in info.phases)
    args = _parse_args(details)
    _initialize_saleae(duration, **args)


def _parse_args(details: live.Details) -> dict:
    ext_saleae = details.extension.get('saleae')
    if ext_saleae is None:
        return {}
    args = ext_saleae.get('init', {})
    # Replace performance string with enum supplied by `saleae` module
    performance = args.get('performance')
    if performance is not None:
        args['performance'] = getattr(saleae.PerformanceOption, performance)
    # Replace trigger string with enum supplied by `saleae` module
    args['triggers'] = {
        channel: getattr(saleae.Trigger, trigger)
        for channel, trigger in args.get('triggers', {}).items()
    }
    return args


def kill():
    saleae.Saleae.kill_logic(kill_all=True)


def _capture_duration(duration: float) -> float:
    """Calculate the total duration of capture to guarantee correct
    Socket API behavior.

    Args:
        duration: The duration of the current test

    Returns:
        The total duration of capture
    """
    return GRACE + _grace + 2 * duration


def _initialize_saleae(duration: float,
                       host: str = 'localhost',
                       port: int = 10429,
                       performance: saleae.PerformanceOption = saleae.PerformanceOption.Full,
                       grace: float = 5.0,
                       triggers: Optional[dict[int, saleae.Trigger]] = None
                       ) -> None:
    """Lazily create global Logic API object.

    Args:
        duration: Duration of the test
        host: The host running Logic
        port: The port for the socket API
        performance: Performance option for Logic
        grace:
            The grace period for recording length heuristics in seconds
        triggers: A dict mapping channels to their Trigger setting
    """
    global _logic
    global _grace
    global _triggers
    _logic = saleae.Saleae(host, port)
    _logic.set_performance(performance)
    _grace = grace
    _logic.set_capture_seconds(_capture_duration(duration))
    _triggers = triggers  # For later use! We cannot set triggers without an active device!


def from_config(path: str) -> Device:
    pass


# TODO How to guarantee that there is only one device?
class Device:
    """Handle object for pylab usage."""
    device_exists = False

    def __init__(self, details: saleae.ConnectedDevice) -> None:
        if Device.device_exists:
            raise RuntimeError(
                'Attempting to created multiple saleae.logic.Device objects')
        Device.device_exists = True
        self._details = details
        self._manager = _LoggingManager()
        self._capture_in_progress = False

    def open(self) -> live.AbstractFuture:
        """No-op ``open`` method to satisfy live.AbstractDevice
        interface requirements."""
        return live.NoOpFuture(report.LogEntry('open logic'))

    def close(self) -> live.AbstractFuture:
        """No-op ``close`` method to satisfy live.AbstractDevice
        interface requirements."""
        return live.NoOpFuture(report.LogEntry('close logic'))

    def setup(self) -> live.AbstractFuture:
        """No-op ``setup`` method to satisfy live.AbstractDevice
        interface requirements."""
        return live.NoOpFuture(report.LogEntry('close logic'))

    @classmethod
    def from_id(cls,
                id: int,
                digital: Optional[list[int]] = None,
                analog: Optional[list[int]] = None,
                sample_rate_digital: int = 50_000,
                sample_rate_analog: int = 100) -> Device:
        """Create a Logic device from id.

        Args:
            id: The saleae id
            digital: The active digital channels
            analog: The active analog channels
            sample_rate_digital:
                The minimum digital sample rate in MS/s (0 to disable
                sampling method)
            sample_rate_analog:
                The minimum analog sample rate in S/s (0 to disable
                sampling method)

        Raises:
            RuntimeError: If ``_initialize`` was not yet called
            StopIteration: If no device with id ``id`` is found
            saleae.ImpossibleSetting:
                If the sample rate settings are invalid
        """
        try:
            index, device = next(
                (index, elem) for index, elem
                in enumerate(_logic.get_connected_devices(), start=1)
                if elem.id == id
            )
        except StopIteration:
            raise ValueError(
                f'Failed to find Saleae device with id {id} ({type(id)}). Available devices are:\n'
                + '\n'.join('\t' + str(elem.id) + f' ({type(elem.id)})' + ': ' + str(elem)
                            for elem in _logic.get_connected_devices())
            )
        _logic.select_active_device(index)

        # Logic and default values based on ``saleae.demo()``.
        if device.type not in {'LOGIC_4_DEVICE', 'LOGIC_DEVICE'}:
            if digital is None:
                digital = [0, 1, 2, 3, 4]
            if analog is None:
                analog = [0, 1]
            _logic.set_active_channels(digital, analog)
        rate = _logic.set_sample_rate_by_minimum(sample_rate_digital, sample_rate_analog)
        assert rate[0] >= sample_rate_digital
        assert rate[1] >= sample_rate_analog
        # if _triggers is not None:
        #     triggers = [_triggers.get(channel, saleae.Trigger.NoTrigger)
        #                 for channel in _triggers]
        #     _logic.set_triggers_for_all_channels(triggers)
        return cls(device)

    @property
    def details(self) -> saleae.ConnectedDevice:
        return self._details

    # TODO This would be easier to do if all logging requests could be
    # issued at the same time.
    def log_signal(self,
                   channel: tuple[int, str],
                   period: float) -> tuple[live.AbstractFuture, live.AbstractFuture]:
        """Submit a logging request.

        Args:
            channel:
                The type of the channel (``'digital'`` or ``'analog'``)
                and the channel number
            period:
                The logging period in seconds
        """
        if not self._capture_in_progress:
            _logic.capture_start()
            self._capture_in_progress = True
        future = self._manager.push(channel, period)
        return DelayFuture('log_signal', _grace), future

    def end_log_signal(self, channel: tuple[int, str]) -> live.AbstractFuture:
        del channel
        self._manager.end()
        return live.NoOpFuture(log=report.LogEntry('saleae: end_log_signal'))


class _LoggingManager:

    def __init__(self) -> None:
        self._requests: list[_LoggingRequest] = []
        self._ended = False

    def push(self, channel: dict[tuple[int, str]], period: int) -> live.AbstractFuture:
        request = _LoggingRequest(channel, period)
        self._requests.append(request)
        return request.future

    def end(self) -> None:
        """End logging for this session.

        With Logic, it's either all or nothing, so it's fine to not even
        check the channel name.
        """
        if self._ended:
            return

        def worker():
            result = self._export_data()
            # TODO This will result in a dead thread if the wrong
            # channel is provided - the error handling must be
            # improved!
            for elem in self._requests:
                # FIXME It could happen that result[elem.channel][0] has
                # length 1, for example if the digital input is not
                # connected. We should check for that error.
                ts = timeseries.TimeSeries(*result[elem.channel])
                elem.future.set_result(ts)
        thread = threading.Thread(target=worker)
        thread.start()
        self._ended = True

    def _export_data(self):
        _logic.capture_stop()
        while not _logic.is_processing_complete():
            time.sleep(GRAIN)
        # There is apparently no better way to do this. In fact, Saleae
        # themselves suggest this approach:
        # https://support.saleae.com/faq/technical-faq/extract-data-using-socket-api
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'data.csv')
            _logic.export_data2(path, delimiter='comma')
            data = [(*elem.channel, elem.period / 1000) for elem in self._requests]
            return _parser.from_file(path, data)


@dataclasses.dataclass
class _LoggingRequest:
    channel: tuple[int, str]
    period: int
    future: live.AbstractFuture = dataclasses.field(init=False)

    def __post_init__(self):
        self.future = Future(f'Saleae Logic {self.channel}@{self.period}')


class BaseFuture:

    def __init__(self, what: str) -> None:
        self._what = what
        self._log = report.LogEntry(report.INFO, what)

    def get_result(self) -> None:
        return None

    @property
    def what(self) -> str:
        return self._what

    @property
    def log(self) -> report.LogEntry:
        return self._log


class DelayFuture(BaseFuture):
    """A future for delaying a result for a fixed amount of time."""

    def __init__(self, what: str, delay: float):
        """Args:
            what: The future's description
            delay: The duration of the delay in seconds
        """
        super().__init__(what)
        self._start = time.time()
        self._delay = delay

    def _seconds_until_done(self) -> float:
        return max(self._start + self._delay - time.time(), 0)

    def wait(self, timeout: Optional[float] = None) -> bool:
        result = True
        if timeout is None:
            wait_for = self._seconds_until_done()
        else:
            if timeout > self._seconds_until_done():
                wait_for = self._seconds_until_done()
            else:
                wait_for = timeout
                result = False
        time.sleep(wait_for)
        return result

    def done(self) -> bool:
        return time.time() >= self._start + self._delay


# FIXME This can probably be refactored out. Also: code-duplication?
class Future(BaseFuture):
    """Primitive future object for logging requests."""

    def __init__(self, what: str):
        super().__init__(what)
        self._result = None
        self._done_event = threading.Event()

    def get_result(self) -> Any:
        return self._result

    def set_result(self, result: Any) -> None:
        self._result = result
        self._done_event.set()

    def wait(self, timeout: Optional[float] = None) -> bool:
        return self._done_event.wait(timeout)

    def done(self) -> bool:
        return self._done_event.is_set()
