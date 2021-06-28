# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

import pylab
from pylab.shared import infos


class TestPortInfo:

    @pytest.mark.parametrize('kwargs, expected', [
        pytest.param(
            {'signal': 'foo', 'channel': 'ch1', 'min': 1.2, 'max': 3.4},
            infos.PortInfo(signal='foo', channel='ch1', min=1.2, max=3.4),
            id='From min/max'
        ),
        pytest.param(
            {'signal': 'bar', 'channel': 'ch2', 'range': '1.2..3.4'},
            infos.PortInfo(signal='bar', channel='ch2', min=1.2, max=3.4),
            id='From range expression'
        )
    ])
    def test___init__success(self, kwargs, expected):
        info = infos.PortInfo(**kwargs)
        assert info == expected

    @pytest.mark.parametrize('kwargs', [
        pytest.param(
            {'signal': 'foo', 'channel': 'ch1', 'min': 1.2, 'range': '1.2..3.4'},
            id='range and min specified'
        ),
        pytest.param(
            {'signal': 'bar', 'channel': 'ch1', 'max': 3.4, 'range': '1.2..3.4'},
            id='range and max specified'
        ),
        pytest.param(
            {'signal': 'bar', 'channel': 'ch1', 'min': 1.2, 'max': 3.4, 'range': '1.2..3.4'},
            id='range and min/max specified'
        ),
        pytest.param(
            {'signal': 'foo', 'channel': 'ch1', 'min': 1.2},
            id='No max specified'
        ),
        pytest.param(
            {'signal': 'bar', 'channel': 'ch1', 'max': 3.4},
            id='No min specified'
        ),
        pytest.param(
            {'signal': 'bar', 'channel': 'ch1', 'min': 1.2},
            id='No min specified'
        ),
        pytest.param(
            {'signal': 'bar', 'channel': 'ch1', 'min': 3.4, 'max': 1.2},
            id='min > max'
        ),
        pytest.param(
            {'signal': 'bar', 'channel': 'ch1'},
            id='No range specified' # ,
            # marks=pytest.mark.xfail
        )
    ])
    def test__init__failure(self, kwargs):
        with pytest.raises(ValueError):
            infos.PortInfo(**kwargs)


class TestElectricalInterface:

    @pytest.fixture
    def inf(self):
        return infos.ElectricalInterface(
            [infos.PortInfo('foo', 'ch1', 0, 1), infos.PortInfo('bar', 'ch2', 3, 4)],
            'baz'
        )

    def test_from_dict(self, inf):
        data = {
            'ports': [
                {'signal': 'foo', 'channel': 'ch1', 'min': 0, 'max': 1},
                {'signal': 'bar', 'channel': 'ch2', 'min': 3, 'max': 4},
            ],
            'description': 'baz'
        }
        info = infos.ElectricalInterface.from_dict(data)
        assert info == inf

    @pytest.mark.parametrize('data', [
        pytest.param({'foo': 'bar'}, id='Unexpected field')
    ])
    def test_from_dict_failure(self, data):
        with pytest.raises(AssertionError):
            infos.ElectricalInterface.from_dict(data)

    def test_get_port_success(self, inf):
        assert inf.get_port('foo') == inf.ports[0]
        assert inf.get_port('bar') == inf.ports[1]

    def test_get_port_failure(self, inf):
        with pytest.raises(ValueError):
            inf.get_port('baz')
