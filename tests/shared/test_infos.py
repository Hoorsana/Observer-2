# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

import pylab
from pylab.core import infos as coreinfos
from pylab.shared import infos


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
