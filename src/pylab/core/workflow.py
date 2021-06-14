# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Module for combining the individual core components of pylab into a
single workflow.
"""

from __future__ import annotations

import abc
import importlib
from typing import Any, Optional

from pylab.core import api  # For typing only...
from pylab.core import loader
from pylab.core import infos
from pylab.core import verification
from pylab.core import report
from pylab.core import utils

# TODO Rename verification -> asserts?


class AbstractLoader(abc.ABC):

    def load_test(self, path: str) -> infos.TestInfo:
        pass

    def load_asserts(self, path: str) -> infos.AssertionInfo:
        pass


def run_from_files(driver: Union[str, api.AbstractDriver],
                   test: str,
                   details: str,
                   asserts: Optional[str] = None,
                   loader: AbstractLoader = loader,
                   dump: Optional[str] = None) -> report.Report:
    """Load, create and execute test, and assert results.

    Use this method to load a test from file, create and execute it, and
    check the results. If ``dump`` is specified, the results are saved
    in the specified path and can be loaded another time without
    executing the test again.

    Args:
        driver:
            Driver module on which to deploy the test or the fully
            qualified name of the driver module
        test: Path to test file
        details: Path to details file
        asserts: Pat hto assertions file
        load: Loader for test and assertion data
        dump: Filesystem path for dumping test results

    Raises:
        RuntimeError: If the test fails to execute correctly
        AssertionError: If any of the assertions fail
    """
    if isinstance(driver, str):
        driver = importlib.import_module(driver)
    info = loader.load_test(test)
    details = driver.load_details(details)
    if asserts is not None:
        asserts = loader.load_asserts(asserts)
    else:
        asserts = []
    return run(driver, info, details, asserts, dump)


def run(driver: api.AbstractDriver,
        info: infos.TestInfo,
        details: Any,
        asserts: Optional[list[verification.AbstractVerification]] = None,
        dump: Optional[str] = None) -> report.Report:
    """Create and execute test, and assert results.

    Use this method to create a test, execute the test and check the
    results. If ``dump`` is specified, the results are saved in the
    specified path and can be loaded another time without executing the
    test again.

    Args:
        driver: Driver on which to deploy the test
        info: Test info object
        details: Device details
        asserts: Assertions which are tested on the results
        dump: Filesystem path for dumping test results

    Returns:
        A report of the test execution

    Raises:
        RuntimeError: If the test fails to execute correctly
        AssertionError: If any of the assertions fail
    """
    if asserts is None:
        asserts = []

    test = driver.create(info, details)

    report = test.execute()
    if dump is not None:
        report.dump(dump)
    if report.failed:
        raise RuntimeError('Test execution failed. Logbook:\n\n' + report.what)

    check_report(report, asserts)
    return report


def check_report(report: report.Report,
                 asserts: list[verification.AbstractVerification]) -> None:
    """Assert results.

    Raises:
        AssertionError: If any of the assertions fail
    """
    checks = [each.verify(report.results) for each in asserts]
    failed = [each for each in checks if each.failed]
    if not failed:
        return

    msg = '\n\n'.join(each.what for each in failed)
    raise AssertionError(
        'Test failed due to the following assertions:\n\n' + msg
        + '\n\nLogbook:\n\n' + report.what)
