# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
# 
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from pylab.core import timeseries
from pylab.core import loader
from pylab.core import verification
from pylab.core import report
from pylab.core import workflow
from pylab.simulink import simulink
from pylab.live import live


@pytest.mark.parametrize('driver, details', [
    pytest.param(
        simulink,
        'resources/examples/adder/matlab_details.yml',
        marks=pytest.mark.skip
    ),
    pytest.param(
        live,
        'resources/examples/adder/arduino_details.yml',
        marks=[]
    )
])
def test_adder(driver, details):
    report = workflow.run_from_files(
        driver=driver,
        test='resources/examples/adder/test.yml',
        details=details,
        asserts='resources/examples/adder/asserts.yml',
        dump='result'
    )
