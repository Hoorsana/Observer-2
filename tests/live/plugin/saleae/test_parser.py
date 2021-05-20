# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
# 
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from pylab.live.plugin.saleae import _parser


def test_from_file():
    result = _parser.from_file('resources/tests/live/plugin/saleae/data.csv')
    time = [0.0, 0.00000128, 1.02399872]
    assert result == {
        (0, 'analog'): (time, [7.06471,  7.59707,  1.72161]),
        (1, 'analog'): (time, [-10.0,    10.0,     10.0]),
        (2, 'analog'): (time, [-4.00244, -3.60684, 4.88156]),
        (3, 'analog'): (time, [-5.00366, -4.83761, -0.36874]),
        (4, 'analog'): (time, [7.06471,  7.59707,  1.72161]),
        (5, 'analog'): (time, [-10.0,    10.0,     10.0]),
        (6, 'analog'): (time, [-4.00244, -3.60684, 4.88156]),
        (7, 'analog'): (time, [-5.00366, -4.83761, -0.36874]),
        (0, 'digital'): ([0.0, 0.00092896], [1, 0]),
        (1, 'digital'): ([0.0, 0.0011648],  [1, 0]),
        (2, 'digital'): ([0.0, 0.00116976], [1, 0]),
        (3, 'digital'): ([0.0, 0.00011728], [0, 1]),
        (4, 'digital'): ([0.0, 0.00412608], [1, 0]),
        (5, 'digital'): ([0.0, 0.00197264], [0, 1]),
        (6, 'digital'): ([0.0, 0.0023864],  [0, 1]),
        (7, 'digital'): ([0.0, 0.000072],   [0, 1]),
    }
