# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from pylab._private import utils


@pytest.mark.parametrize('expr, expected', [
    pytest.param('1..2', (1, 2)),
    pytest.param('  1.2  .......3.4 ', (1.2, 3.4), id='Extra dots and whitespaces'),
    pytest.param('+1.2..-3.4', (1.2, -3.4), id='With sign')
])
def test_load_range_success(expr, expected):
    assert utils.load_range(expr) == expected


@pytest.mark.parametrize('expr', [
    pytest.param('1.2', id='Only one number, missing dots'),
    pytest.param('1.2..', id='Only one number'),
    pytest.param('1.2..x', id='Illegal chars')
])
def test_load_range_failure(expr):
    with pytest.raises(ValueError):
        utils.load_range(expr)
