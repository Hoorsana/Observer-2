# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import csv
import dataclasses
import re
from typing import IO

from pylab.core import timeseries


def from_file(path: str, data: list[tuple[int, str, float]]) -> ...:
    with open(path, "r") as f:
        reader = csv.reader(f, delimiter=",")  # , quoting=csv.QUOTE_NONNUMERIC)
        header = next(reader)
        available_channels = _get_available_channels(header)
        requests = []
        for number, type, period in data:
            channel = next(
                elem
                for elem in available_channels
                if elem.number == number and elem.type == type
            )
            requests.append(_Request(channel, period))
        job = Job(requests)
        result = job.deploy(f)
    return result


class Job:
    def __init__(self, requests: list[_Request]):
        self._requests = requests

    def deploy(self, f: IO) -> ...:
        reader = csv.reader(f, delimiter=",")
        for line in reader:
            self._handle(line)
        return {elem.channel: elem.result for elem in self._requests}

    def _handle(self, line: list[str]) -> None:
        line = [float(x) if x != " " else None for x in line]
        for request in self._requests:
            request.update(line)


class _Request:
    def __init__(self, channel: _Channel, period: float) -> None:
        self._channel = channel
        self._period = period
        self._time = []
        self._values = []

    @property
    def channel(self) -> tuple[int, str]:
        return (self._channel.number, self._channel.type)

    @property
    def result(self) -> list[float]:
        return self._time, self._values

    def update(self, line: list[Optional[float]]) -> None:
        time, values = self._channel.extract_data_from_line(line)
        if time is None and values is None:
            return
        assert time is not None
        assert values is not None
        while True:
            if not self._time:
                current = 0.0
            else:
                last = self._time[-1]
                current = last + self._period
            # Note that if (request period) << (logger period), then
            # this will result in may superfluous samples, but this will
            # probably never happen.
            if time >= current:
                self._time.append(current)
                self._values.append(values)
            else:
                break
        assert len(self._time) == len(self._values)


def _get_available_channels(header: list[str]) -> list[_Channel]:
    channels = []
    for index, elem in enumerate(header):
        elem = elem.strip()
        if elem == "Time [s]":
            time = index
        elif elem.startswith("Channel"):
            number, type = _parse_channel_info(elem)
            channel = _Channel(number, type, time, index)
            channels.append(channel)
        else:
            raise ValueError(
                'Expected header field of the following form: "Time [s]"\n'
                'or "Channel [0-9]-(Analog|Digital)". Instead received the\n'
                f"following: {header}"
            )
    return channels


def _parse_channel_info(entry: str) -> tuple[int, str]:
    """Parse a header entry of the form ``'Channel
    [0-9]-(Analog|Digital)'``.

    Args:
        entry: The entry to parse

    Returns:
        The number of the channel and its type (``'analog'`` or
        ``'digital'``)
    """
    match = re.match("Channel ([0-9])-(Analog|Digital)", entry)
    number = int(match.group(1))
    type = match.group(2).lower()
    return number, type


@dataclasses.dataclass
class _Channel:
    """Class that shows where in the numerical data the channel data is
    stored.

    Attributes:
        number: The channel number
        type: 'analog' or 'digital'
        time: The index of the column where time is stored
        data: The index of the column where measurements are stored
    """

    number: int
    type: str
    time: int
    data: int

    def extract_data_from_line(
        self, line: list[float]
    ) -> tuple[list[float], list[float]]:
        # Make sure to only read available data by checking for
        # ``None``.
        return line[self.time], line[self.data]
