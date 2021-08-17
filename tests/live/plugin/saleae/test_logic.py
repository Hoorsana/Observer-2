# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import time

import pytest

from pylab.core import verification
from pylab.core import infos
from pylab.core import workflow
from pylab.live import live
from pylab.live.plugin.saleae import logic


def test_basic(pulsar, details):
    logic.init(pulsar, details)
    time.sleep(0.1)


def test_functional(pulsar, details):
    report = workflow.run(live, pulsar, details)
    asserts = [
        verification.IntegralAlmostEqualTo(
            "pulsar.analog", 0.5, atol=0.01, lower=1, upper=2
        ),
        verification.IntegralAlmostEqualTo(
            "pulsar.digital", 0.5, atol=0.01, lower=1, upper=2
        ),
    ]
    workflow.check_report(report, asserts)


@pytest.fixture
def pulsar():
    return infos.TestInfo(
        [
            infos.TargetInfo(
                name="pulsar",
                signals=[
                    infos.SignalInfo(
                        name="analog", flags=["output", "analog"], min=0, max=1
                    ),
                    infos.SignalInfo(
                        name="digital", flags=["output", "digital"], min=0, max=1
                    ),
                ],
            )
        ],
        [
            infos.LoggingInfo(target="pulsar", signal="analog", period=1),
            infos.LoggingInfo(target="pulsar", signal="digital", period=1),
        ],
        [infos.PhaseInfo(duration=1.0, commands=[])],
    )


@pytest.fixture
def details():
    return live.Details(
        devices=[
            live.DeviceDetails(
                name="pulsar",
                module="pylab.live.live",
                type="UsbSerialDevice.from_serial_number",
                data={"serial_number": os.environ["PYLAB_USB_SERIAL_NUMBER_DEVICE"]},
                interface=infos.ElectricalInterface(
                    ports=[
                        infos.PortInfo(
                            "analog", "DAC1", min=0, max=255, flags=["output", "analog"]
                        ),
                        infos.PortInfo(
                            "digital", "D45", min=0, max=1, flags=["output", "digital"]
                        ),
                    ]
                ),
            ),
            live.DeviceDetails(
                name="logger",
                module="pylab.live.plugin.saleae.logic",
                type="Device.from_id",
                data={
                    "id": int(os.environ["PYLAB_SALEAE_DEVICE_ID_LOGIC_PRO_8"]),
                    "digital": [2],
                    "analog": [0, 1, 2, 3],
                    "sample_rate_digital": 4_000_000,
                    "sample_rate_analog": 100,
                },
                interface=infos.ElectricalInterface(
                    ports=[
                        infos.PortInfo(
                            "analog",
                            (3, "analog"),
                            min=0.53315,
                            max=2.734,
                            flags=["input", "analog"],
                        ),
                        infos.PortInfo(
                            "digital",
                            (2, "digital"),
                            min=0,
                            max=1,
                            flags=["input", "digital"],
                        ),
                    ]
                ),
            ),
        ],
        connections=[
            infos.ConnectionInfo(
                sender="pulsar",
                sender_port="analog",
                receiver="logger",
                receiver_port="analog",
            ),
            infos.ConnectionInfo(
                sender="pulsar",
                sender_port="digital",
                receiver="logger",
                receiver_port="digital",
            ),
        ],
        extension={
            "saleae": {
                "init": {
                    "host": "localhost",
                    "performance": "Full",
                    "port": 10429,
                    "grace": 5.0,
                }
            }
        },
    )
