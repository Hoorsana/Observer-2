# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import dataclasses
import pytest

import pylab
from pylab.core import infos as coreinfos
from pylab.shared import infos
from pylab.shared import testobject


@dataclasses.dataclass
class Port:
    signal: str
    channel: int


@dataclasses.dataclass
class Device:
    name: str
    ports: list[Port]

    def find_port(self, signal: str) -> Port:
        return next(p for p in self.ports if p.signal == signal)


class TestTestObjectBase:
    @pytest.fixture
    def test_object(self):
        return testobject.TestObjectBase(
            [
                Device("x", [Port("out", 0)]),
                Device(
                    "y",
                    [
                        Port("in0", 0),
                        Port("in1", 1),
                    ],
                ),
            ],
            [
                infos.ConnectionInfo("x", "out", "y", "in0"),
                infos.ConnectionInfo("x", "out", "y", "in1"),
            ],
        )

    def test_trace_forward(self, test_object):
        x = test_object.trace_forward("x", "out")
        assert [a[1] for a in x] == [Port("in0", 0), Port("in1", 1)]


class TestPortInfo:
    @pytest.mark.parametrize(
        "kwargs, expected",
        [
            pytest.param(
                {"signal": "bar", "channel": "ch2", "range": {"min": 1.2, "max": 3.4}},
                infos.PortInfo(
                    signal="bar",
                    channel="ch2",
                    range=coreinfos.RangeInfo(min=1.2, max=3.4),
                ),
                id="From range expression",
            )
        ],
    )
    def test__init__success(self, kwargs, expected):
        info = infos.PortInfo(**kwargs)
        assert info == expected


class TestElectricalInterface:
    @pytest.fixture
    def inf(self):
        return infos.ElectricalInterface(
            [
                infos.PortInfo("foo", "ch1", range=coreinfos.RangeInfo(0, 1)),
                infos.PortInfo("bar", "ch2", range=coreinfos.RangeInfo(3, 4)),
            ],
            "baz",
        )

    def test_get_port_success(self, inf):
        assert inf.get_port("foo") == inf.ports[0]
        assert inf.get_port("bar") == inf.ports[1]

    def test_get_port_failure(self, inf):
        with pytest.raises(ValueError):
            inf.get_port("baz")
