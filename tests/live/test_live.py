# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os

import pytest

from pylab.core import infos
from pylab.shared import infos as sharedinfos
from pylab.core import timeseries
from pylab.core import workflow
from pylab.core import testing
from pylab.live import live
from pylab._private import rogueplugin


STEP_SIZE = 0.1


def test_load_details(details):
    result = live.load_details("resources/tests/live/details.yml")
    lhs = result.devices[0]
    rhs = result.devices[0]
    assert lhs.name == rhs.name
    assert lhs.type == rhs.type
    assert lhs.module == rhs.module
    assert lhs.interface.ports == rhs.interface.ports
    assert result.connections == details.connections


@pytest.fixture
def assertion():
    a = testing.TimeseriesAlmostEqual(
        timeseries.TimeSeries(
            [t * STEP_SIZE for t in range(10)],
            [[100], [125], [100], [50], [0], [100], [200], [100], [0], [0]],
        ),
        rtol=0.01,
    )
    return a.wrap_in_dispatcher({"actual": "adder.sum"})


@pytest.mark.timeout(20.0)
def test_functional(adder, details, assertion):
    report = workflow.run(live, adder, details)
    print("\n".join(str(each) for each in report.logbook))
    ts = report.results["adder.sum"]
    timeseries.pretty_print(ts)
    assertion.assert_(report.results)


@pytest.fixture
def adder():
    return infos.TestInfo(
        [
            infos.TargetInfo(
                name="adder",
                signals=[
                    infos.SignalInfo(
                        name="val1",
                        flags=["input", "analog"],
                        range=infos.RangeInfo(min=0, max=100),
                    ),
                    infos.SignalInfo(
                        name="val2",
                        flags=["input", "analog"],
                        range=infos.RangeInfo(min=0, max=100),
                    ),
                    infos.SignalInfo(
                        name="sum",
                        flags=["output", "analog"],
                        range=infos.RangeInfo(min=0, max=200),
                    ),
                ],
            )
        ],
        [infos.LoggingInfo(target="adder", signal="sum", period=0.1)],
        [
            infos.PhaseInfo(
                duration=5.0 * STEP_SIZE,
                commands=[
                    infos.CommandInfo(
                        time=0.0,
                        command="CmdSetSignal",
                        target="adder",
                        data={"signal": "val1", "value": 50},
                    ),
                    infos.CommandInfo(
                        time=0.0,
                        command="CmdSetSignal",
                        target="adder",
                        data={"signal": "val2", "value": 50},
                    ),
                    infos.CommandInfo(
                        time=1.0 * STEP_SIZE,
                        command="CmdSetSignal",
                        target="adder",
                        data={"signal": "val1", "value": 75},
                    ),
                    infos.CommandInfo(
                        time=2.0 * STEP_SIZE,
                        command="CmdSetSignal",
                        target="adder",
                        data={"signal": "val2", "value": 25},
                    ),
                    infos.CommandInfo(
                        time=3.0 * STEP_SIZE,
                        command="CmdSetSignal",
                        target="adder",
                        data={"signal": "val1", "value": 25},
                    ),
                    infos.CommandInfo(
                        time=4.0 * STEP_SIZE,
                        command="CmdSetSignal",
                        target="adder",
                        data={"signal": "val1", "value": 0},
                    ),
                    infos.CommandInfo(
                        time=4.0 * STEP_SIZE,
                        command="CmdSetSignal",
                        target="adder",
                        data={"signal": "val2", "value": 0},
                    ),
                ],
            ),
            infos.PhaseInfo(
                duration=4.0 * STEP_SIZE,
                commands=[
                    infos.CommandInfo(
                        time=0.0,
                        command="CmdSetSignal",
                        target="adder",
                        data={"signal": "val1", "value": 0},
                    ),
                    infos.CommandInfo(
                        time=0.0,
                        command="CmdSetSignal",
                        target="adder",
                        data={"signal": "val2", "value": 100},
                    ),
                    infos.CommandInfo(
                        time=1.0 * STEP_SIZE,
                        command="CmdSetSignal",
                        target="adder",
                        data={"signal": "val1", "value": 100},
                    ),
                    infos.CommandInfo(
                        time=2.0 * STEP_SIZE,
                        command="CmdSetSignal",
                        target="adder",
                        data={"signal": "val2", "value": 0},
                    ),
                    infos.CommandInfo(
                        time=3.0 * STEP_SIZE,
                        command="CmdSetSignal",
                        target="adder",
                        data={"signal": "val1", "value": 0},
                    ),
                ],
            ),
        ],
    )


@pytest.fixture
def details():
    return live.Details(
        devices=[
            live.DeviceDetails(
                name="adder",
                module="pylab._private.rogueplugin",
                type="Device",
                data={
                    "id": "adder",
                    "ports": ["A0", "A1", "DAC0"],
                },
                extension={
                    "defaults": {
                        "A0": 0.0,
                        "A1": 0.0,
                        "DAC0": 0.0,
                    },
                    "loop": lambda d: d.set_value(
                        "DAC0", d.get_value("A0") + d.get_value("A1")
                    ),
                },
                interface=sharedinfos.ElectricalInterface(
                    ports=[
                        sharedinfos.PortInfo(
                            "val1",
                            "A0",
                            range=infos.RangeInfo(min=0, max=100),
                            flags=["input", "analog"],
                        ),
                        sharedinfos.PortInfo(
                            "val2",
                            "A1",
                            range=infos.RangeInfo(min=0, max=100),
                            flags=["input", "analog"],
                        ),
                        sharedinfos.PortInfo(
                            "sum",
                            "DAC0",
                            range=infos.RangeInfo(min=0, max=200),
                            flags=["output", "analog"],
                        ),
                    ]
                ),
            ),
            live.DeviceDetails(
                name="gpio",
                module="pylab._private.rogueplugin",
                type="Device",
                data={
                    "id": "gpio",
                    "ports": ["A0", "DAC0", "DAC1"],
                },
                extension={
                    "defaults": {
                        "A0": 0.0,
                        "DAC0": 0.0,
                        "DAC1": 0.0,
                    },
                },
                interface=sharedinfos.ElectricalInterface(
                    ports=[
                        sharedinfos.PortInfo(
                            "out1",
                            "DAC0",
                            range=infos.RangeInfo(min=0, max=100),
                            flags=["output", "analog"],
                        ),
                        sharedinfos.PortInfo(
                            "out2",
                            "DAC1",
                            range=infos.RangeInfo(min=0, max=100),
                            flags=["output", "analog"],
                        ),
                        sharedinfos.PortInfo(
                            "sum",
                            "A0",
                            range=infos.RangeInfo(min=0, max=200),
                            flags=["input", "analog"],
                        ),
                    ]
                ),
            ),
        ],
        connections=[
            sharedinfos.ConnectionInfo(
                sender="gpio",
                sender_port="out1",
                receiver="adder",
                receiver_port="val1",
            ),
            sharedinfos.ConnectionInfo(
                sender="gpio",
                sender_port="out2",
                receiver="adder",
                receiver_port="val2",
            ),
            sharedinfos.ConnectionInfo(
                sender="adder", sender_port="sum", receiver="gpio", receiver_port="sum"
            ),
        ],
    )
