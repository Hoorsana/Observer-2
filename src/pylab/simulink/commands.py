# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Module with implementations of basic pylab commands."""

from __future__ import annotations

import math

from pylab.simulink import simulink
from pylab.core import infos
from pylab.core import utils


# FIXME Add checks if physical/eletric values are out-of-bounds.


def set_signal(test_object: simulink.TestObject,
               command_info: infos.CommandInfo,
               time: float) -> tuple[str, str]:
    del time

    device, port = test_object.trace_back(
        command_info.target, command_info.data['signal'])
    signal = test_object.get_signal(command_info.target, command_info.data['signal'])

    physical_value = command_info.data['value']
    value = utils.transform(signal.min, signal.max,
                            port.min, port.max,
                            physical_value)

    code = device.block.set_signal(port.channel, value)
    what = str(command_info)
    return code, what


def set_signal_ramp(test_object: simulink.TestObject,
                    command_info: infos.CommandInfo,
                    time: float) -> tuple[str, str]:
    device, port = test_object.trace_back(
        command_info.target, command_info.data['signal'])
    signal = test_object.get_signal(command_info.target, command_info.data['signal'])

    slope = utils.linear_transform(signal.min, signal.max,
                                   port.min, port.max,
                                   command_info.data['slope'])
    time = time + command_info.data['time']
    initial_output = utils.transform(signal.min, signal.max,
                                     port.min, port.max,
                                     command_info.data['initial_output'])

    code = device.block.set_signal_ramp(
        port.channel, slope, time, initial_output)
    what = str(command_info)
    return code, what


def set_signal_sine(test_object: simulink.TestObject,
                    command_info: infos.CommandInfo,
                    time: float) -> tuple[str, str]:
    _default_bias = 0.0
    _default_phase = 0.0

    device, port = test_object.trace_back(
        command_info.target, command_info.data['signal'])
    signal = test_object.get_signal(command_info.target, command_info.data['signal'])

    amplitude = utils.linear_transform(signal.min, signal.max,
                                       port.min, port.max,
                                       command_info.data['amplitude'])
    bias = utils.transform(signal.min, signal.max,
                           port.min, port.max,
                           command_info.data.get('bias', _default_bias))
    frequency = command_info.data['frequency'] * 2 * math.pi
    phase = 2 * math.pi * \
        command_info.data.get('phase', _default_phase) - frequency * time

    code = device.block.set_signal_sine(
        port.channel, amplitude, frequency, phase, bias)
    what = str(command_info)
    return code, what


def set_param(test_object: simulink.TestObject,
              command_info: infos.CommandInfo,
              time: float) -> tuple[str, str]:
    device = next(each for each in test_object.devices
                  if each.name == command_info.target)
    code = device.block.set_param(
        command_info.data['param'], command_info.data['value'])
    what = str(command_info)
    return code, what


# dispatch {{{


CmdSetSignal = set_signal
CmdSetSignalRamp = set_signal_ramp
CmdSetSignalSine = set_signal_sine
CmdSetParam = set_param


# }}} dispatch
