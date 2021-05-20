# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
# 
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from pylab.live.plugin.saleae import _parser


CHANNELS = [(0, 'analog'), (3, 'analog'), (7, 'digital')]
PERIODS = [0.5, 0.3, 0.2]
REQUESTS = [channel + (period,) for channel, period in zip(CHANNELS, PERIODS)]

@pytest.fixture
def data():
    return _parser.from_file('resources/tests/live/plugin/saleae/data.csv', REQUESTS)


@pytest.mark.parametrize('channel, expected',
    list(zip(
        CHANNELS,
        [
            ([0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0], [-7.1072089960680245, -6.772661054318528, -1.6480623329175152, 7.1112037477048915, -3.5119249461033997, 8.158335143350428, 8.933143926485684]),
            ([0.0, 0.3, 0.6, 0.9, 1.2, 1.5, 1.8, 2.1, 2.4, 2.7, 3.0], [8.30263257841262, -5.938874937026086, 1.6491158536998167, -7.088705167610336, 2.8062254470375727, 2.2508901830396173, -7.405233535156215, -9.122895823088184, -5.419698496204819, 0.5634000821141516, 0.5634000821141516]),
            ([0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8], [1, 1, 1, 1, 1, 0, 0, 0, 1, 1])
        ]
    ))
)
def test_from_file(data, channel, expected):
    request = next(elem for elem in data if elem.channel == channel)
    assert request.result[0] == pytest.approx(expected[0])
    assert request.result[1] == pytest.approx(expected[1])
