# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Pylab live driver device wrapper for python implementation of 8tronix
controllino protocol.
"""

from __future__ import annotations

import copy
import time

import serial

# FIXME Rename this module or the controllino serial module.
from controllino import controllino as controllino_serial
from pylab.core import report
from pylab.core import timeseries
from pylab.live import live
from pylab.live import utility

GRAIN = 0.001


class PylabControllino:
    """Plugin device for Controllino serial driver."""

    def __init__(self,
                 ser: serial.Serial,
                 pin_modes: Optional[dict[str, str]] = None) -> None:
        """Initialize from socket.

        Args:
            ser: The underlying serial object
            pin_modes: A ``dict`` mapping pins to their input/output mode
        """
        self._controllino = controllino_serial.Controllino(ser)
        if pin_modes is None:
            pin_modes = {}
        else:
            self._pin_modes = pin_modes

    @classmethod
    def from_serial_number(cls,
                           serial_number: str,
                           pin_modes: Optional[dict[str, str]] = None,
                           **kwargs) -> controllino_serial.PylabControllino:
        """Create from device serial number.

        Args:
            serial_number: The device's serial number
            pin_modes: A ``dict`` mapping pins to their input/output mode

        Raises:
            StopIteration: If the device is not found
        """
        return cls(
            utility.create_serial_device_from_serial_number(serial_number, **kwargs),
            pin_modes
        )

    # FIXME This method should that ``pin: PortInfo`` as arg.
    def log_signal(
        self, pin: str, period: float) -> Tuple[live.AbstractFuture, live.AbstractFuture]:
        """Submit a logging request.

        Args:
            pin: The pin to log
            period: The logging period in seconds

        Returns:
            A future which is done when the request is accepted or
            rejected and a future which is done if the request is closed
            and then holds the results
        """
        period = int(1000 * period)  # Convert from sec to ms
        accepted, future = self._controllino.log_signal(pin, period)
        accepted_wrapper = Future(
            self._controllino,
            accepted,
            f'CmdLogSignal({pin}, {period}) - accepted'
        )
        future_wrapper = Future(
            self._controllino,
            future,
            f'CmdLogSignal({pin}, {period}) - results'
        )
        return accepted_wrapper, future_wrapper

    # FIXME This method should that ``pin: PortInfo`` as arg.
    def end_log_signal(self, pin: str) -> Future:
        """Submit a command to end a logging request.

        Args:
            pin: The pin of the logging request to close

        Returns:
            A future which is done when the request is accepted or
            rejected
        """
        return Future(
            self._controllino,
            self._controllino.end_log_signal(pin),
            f'CmdEndLogSignal({pin})'
        )

    # FIXME This method should that ``pin: PortInfo`` as arg.
    def set_signal(self, pin: str, value: ArrayLike) -> live.AbstractFuture:
        """Submit a SetSignal command.

        Args:
            pin: The pin to stimulate
            value: The value to stimulate with

        Returns:
            A future which is done when the request is accepted or
            rejected
        """
        return Future(
            self._controllino,
            self._controllino.set_signal(pin, value),
            f'CmdSetSignal({pin}, {value})'
        )

    def open(self) -> live.AbstractFuture:
        """Open the device.

        Returns:
            A future which is done when the request is accepted or
            rejected
        """
        return Future(
            self._controllino,
            self._controllino.open(),
            'CmdReady()'
        )

    def close(self) -> live.AbstractFuture:
        """Kill the device (not a grace-full close).

        Returns:
            A noop future
        """
        self._controllino.kill()
        return FutureCollection()

    def setup(self) -> live.AbstractFuture:
        """Setup the pin modes.

        Returns:
            A future which is done when the pin mode changes are
            accepted or rejected
        """
        # TODO Set pin modes
        return FutureCollection()


class Future(live.AbstractFuture):
    """Wrapper for ``controllino_serial.Future``."""

    def __init__(self,
                 api: controllino_serial.Controllino,
                 future: controllino_serial.Future,
                 what: str) -> None:
        """Args:
            api: A reference to the issuieing ``Controllino`` object
            future: The wrapped future
            what: A description of the future for a log entry
        """
        self._api = api
        self._future = future
        self._what = what

    # TODO Just return a timeseries here!
    def get_result(self) -> timeseries.TimeSeries:
        """Get results from wrapped future.

        Shall only be called if the future represents the data of a
        logging request.
        """
        result = self._future.result()
        time = [t / 1000 for t in result.time]
        return timeseries.TimeSeries(time, result.values)

    @property
    def what(self) -> str:
        return self._what

    @property
    def log(self):
        # FIXME It is unclear whether or not a controllino logic error
        # should be raised here or just cause a panic.
        try:
            self._future.result()
        except controllino_serial.ControllinoError as e:
            return report.LogEntry(
                self._what + ' failed with the following exception:\n\n' + str(e),
                report.PANIC
            )
        return report.LogEntry(self._what, report.INFO)

    @property
    def done(self) -> bool:
        return self._future.done()

    def wait(self, timeout: Optional[float] = None) -> bool:
        ok = self._future.wait(timeout)
        self._api.process_errors()
        return ok


class FutureCollection(live.AbstractFuture):
    """Class for joining multiple futures under a single interface.

    May be used as noop futures if the list of futures is empty.
    """

    def __init__(self, futures: Optional[list[Future]] = None):
        if futures is None:
            futures = []
        self._futures = futures

    def get_result(self) -> list[Any]:
        return [elem.get_result() for elem in self._futures]

    @property
    def what(self) -> str:
        return '\n'.join(each.what for each in self._futures)

    @property
    def log(self) -> report.LogEntry:
        futures = [each for each in self._futures if each.done]
        if futures:
            severity = max(elem.severity for elem in futures)
        else:
            severity = report.INFO
        return report.LogEntry('\n'.join(each.log for each in futures), severity)

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
