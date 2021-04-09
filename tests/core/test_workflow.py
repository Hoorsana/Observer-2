# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
import unittest.mock

from pylab.core import workflow
from pylab.core import report
from pylab.core import verification


# FIXME This test needs 1) less mocking; 2) more cases [no dump, etc.]
def test_run_from_files(mocker):
    run = mocker.Mock()
    mocker.patch('pylab.core.workflow.run', run)
    driver = mocker.Mock(name='driver')
    driver.load_details = mocker.Mock(return_value=mocker.Mock(name='details'))
    test = '/path/to/test'
    details = '/path/to/details'
    asserts = '/path/to/asserts'
    loader = mocker.Mock()
    info = mocker.Mock(name='info')
    loader.load_test.return_value = info
    asserts_ = mocker.Mock(name='asserts_')
    loader.load_asserts.return_value = asserts_
    dump = '/path/to/dump'
    workflow.run_from_files(driver, test, details, asserts, loader, dump)
    loader.load_test.assert_called_once_with(test)
    loader.load_asserts.assert_called_once_with(asserts)
    driver.load_details.assert_called_once_with(details)
    run.assert_called_once_with(
    driver,
    info,
    driver.load_details.return_value,
    asserts_,
     dump)


@pytest.mark.parametrize('dump', [None, '/path/to/dump'])
def test_run_success(mocker, dump):
    check_report = mocker.Mock()
    mocker.patch('pylab.core.workflow.check_report', check_report)

    dump_mock = mocker.Mock()
    test = mocker.Mock(name='test')
    test.execute.return_value = mocker.Mock(failed=False, what='what', dump=dump_mock)

    driver = mocker.Mock(name='driver')
    driver.create = mocker.Mock(return_value=test)

    info = mocker.Mock(name='test')
    details = mocker.Mock(name='details')
    asserts = ['foo', 'bar']

    report = workflow.run(driver, info, details, asserts, dump)
    if dump:
        dump_mock.assert_called_once_with(dump)
    else:
        dump_mock.assert_not_called()
    driver.create.assert_called_once_with(info, details)
    check_report.assert_called_once_with(report, asserts)


@pytest.mark.parametrize('dump', [None, '/path/to/dump'])
def test_run_failure(mocker, dump):
    check_report = mocker.Mock()
    mocker.patch('pylab.core.workflow.check_report', check_report)

    dump_mock = mocker.Mock()
    test = mocker.Mock(name='test')
    test.execute.return_value = mocker.Mock(failed=True, what='what', dump=dump_mock)

    driver = mocker.Mock(name='driver')
    driver.create = mocker.Mock(return_value=test)

    info = mocker.Mock(name='test')
    details = mocker.Mock(name='details')
    asserts = ['foo', 'bar']

    with pytest.raises(RuntimeError) as e:
        workflow.run(driver, info, details, asserts, dump)
    if dump:
        dump_mock.assert_called_once_with(dump)
    else:
        dump_mock.assert_not_called()
    driver.create.assert_called_once_with(info, details)
    assert str(e.value) == 'Test execution failed. Logbook:\n\nwhat'
    check_report.assert_not_called()


def test_check_report_success(mocker):
    report = mocker.Mock(name='report')
    checks = [verification.Check(),
              verification.Check(),
              verification.Check()]
    asserts = [mocker.Mock(verify=mocker.Mock(return_value=each)) for each in checks]

    workflow.check_report(report, asserts)

    for each in asserts:
        each.verify.assert_called_once_with(report.results)


def test_check_report_failure(mocker):
    report = mocker.Mock(name='report', what='report.what')
    checks = [verification.Check(),
              verification.Check(),
              verification.Check(True, 'what')]
    asserts = [mocker.Mock(verify=mocker.Mock(return_value=each))
               for each in checks]

    with pytest.raises(AssertionError) as e:
        workflow.check_report(report, asserts)
    assert str(e.value) == \
        'Test failed due to the following assertions:\n\nwhat\n\nLogbook:\n\nreport.what'

    for each in asserts:
        each.verify.assert_called_once_with(report.results)
