# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
# 
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import csv
import dataclasses
import re

from pylab.core import timeseries


def from_file(path: str) -> timeseries.TimeSeries:
    with open(path, 'r') as f:
        reader = csv.reader(f, delimiter=',')  # , quoting=csv.QUOTE_NONNUMERIC)
        data = list(reader)
    return _to_list(data)


def _to_list(data: list[list[str]]) -> timeseries.TimeSeries:
    """Convert raw .csv data to tuple of time and value vectors.
    
    Args:
        data: The data to parse

    Returns:
        A dict mapping the channel to the corresponding time series
    """
    header = [elem.strip() for elem in data[0]]
    data = [[float(x) if x != ' ' else None for x in line] for line in data[1:]]

    channels = []
    for index, elem in enumerate(header):
        if elem == 'Time [s]':
            time = index
        elif elem.startswith('Channel'):
            number, type = _parse_channel_info(elem)
            channel = _Channel(number, type, time, index)
            channels.append(channel)
        else:
            raise ValueError(
                'Expected header field of the following form: "Time [s]"'
                ' or "Channel [0-9]-(Analog|Digital)"'
            )
    return {(each.number, each.type): each.deploy(data) for each in channels}


def _parse_channel_info(entry: str) -> tuple[int, str]:
    """Parse a header entry of the form ``'Channel
    [0-9]-(Analog|Digital)'``.

    Args:
        entry: The entry to parse

    Returns:
        The number of the channel and its type (``'analog'`` or
        ``'digital'``)
    """
    match = re.match('Channel ([0-9])-(Analog|Digital)', entry)
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

    def deploy(self, data: list[list[float]]) -> tuple[list[float], list[float]]:
        # Make sure to only read available data by checking for
        # ``None``.
        time = [elem[self.time] for elem in data
                if elem[self.time] is not None]
        values = [elem[self.data] for elem in data
                  if elem[self.data] is not None]
        return time, values
