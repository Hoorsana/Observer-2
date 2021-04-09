import pytest

import pylab.commandline
from pylab.core import errors
from pylab.core import workflow


def test_success(monkeypatch, mocker, script_runner):
    driver = 'path.to.driver',
    test = '/path/to/test',
    details = '/path/to/details',
    asserts = '/path/to/asserts',
    dump = '/path/to/dump',
    args = {
        'driver': driver,
        'test': test,
        'details': details,
        'asserts': asserts,
        'dump': dump,
    }
    monkeypatch.setattr(pylab.commandline, 'parse', mocker.Mock(return_value=args))
    monkeypatch.setattr(workflow, 'run_from_files', mocker.Mock())
    ret = script_runner.run('pylab-cli', test, details, f'-a {asserts}', f'-d {dump}')
    assert ret.success
    assert workflow.run_from_files.called_once_with(driver, test, details, asserts, dump=dump)


@pytest.mark.parametrize('exception, return_code', [
    pytest.param(AssertionError, 8, id='Test failed'),
    pytest.param(errors.PylabError, 9, id='Test execution failed'),
    pytest.param(Exception, 1, id='Unexpected raise')
])
def test_failure(exception, return_code, monkeypatch, mocker, script_runner):
    driver = 'path.to.driver',
    test = '/path/to/test',
    details = '/path/to/details',
    asserts = '/path/to/asserts',
    dump = '/path/to/dump',
    args = {
        'driver': driver,
        'test': test,
        'details': details,
        'asserts': asserts,
        'dump': dump,
    }
    monkeypatch.setattr(pylab.commandline, 'parse', mocker.Mock(return_value=args))
    monkeypatch.setattr(workflow, 'run_from_files', mocker.Mock(side_effect=exception()))
    ret = script_runner.run('pylab-cli', test, details, f'-a {asserts}', f'-d {dump}')
    assert not ret.success
    assert ret.returncode == return_code
