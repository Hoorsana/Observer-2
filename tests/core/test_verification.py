# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from pylab.core import infos
from pylab.core import verification
from pylab.core import timeseries


class TestLoadInfo:

    def test_success(self, mocker):
        mock = mocker.Mock()
        mock.return_value = mocker.Mock(return_value=123)
        mocker.patch('pylab.core.utils.module_getattr', mock)
        info = infos.AssertionInfo(
            type='this.module.does.exist',
            data={'foo': 'bar'})
        result = verification.load_info(info)
        assert result == 123
        mock.assert_called_once_with('this.module.does.exist')
        mock.return_value.assert_called_once_with(foo='bar')

    def test_failure(self):
        info = infos.AssertionInfo(
            type='this.module.does.not.exist',
            data={'foo': 'bar'})
        with pytest.raises(ModuleNotFoundError):
            verification.load_info(info)


@pytest.mark.xfail
class TestAlmostEverywhereClose:

    def test_verify_success(self, mocker):
        result = mocker.Mock(name='result')
        expected = mocker.Mock(name='expected')
        rtol = mocker.Mock(name='rtol')
        atol = mocker.Mock(name='atol')

        mock = mocker.Mock()
        mocker.patch('pylab.core.timeseries.assert_almost_everywhere_close', mock)
        v = verification.AlmostEverywhereClose('result', expected, rtol, atol)
        result_dict = {'result': result, 'foo': 'bar'}
        check = v.verify(result_dict)
        mock.assert_called_once_with(result, expected, rtol=rtol, atol=atol)
        assert not check.failed
        assert not check.what

    def test_verify_failure(self, mocker):
        result = mocker.Mock(name='result')
        expected = mocker.Mock(name='expected')
        rtol = mocker.Mock(name='rtol')
        atol = mocker.Mock(name='atol')

        mock = mocker.Mock()
        mocker.patch('pylab.core.timeseries.assert_almost_everywhere_close', mock)
        mock.side_effect = AssertionError('foo')
        v = verification.AlmostEverywhereClose('result', expected, rtol, atol)
        result_dict = {'result': result, 'foo': 'bar'}
        check = v.verify(result_dict)
        mock.assert_called_once_with(result, expected, rtol=rtol, atol=atol)
        assert check.failed
        assert check.what == 'foo'


@pytest.mark.xfail
class TestIsCloseAtTime:

    def test_verify_success(self, mocker):
        result = mocker.Mock(name='result')
        result.return_value = 1
        expected = 5
        time = 2
        rtol = 3
        atol = 4

        mock = mocker.Mock()
        mocker.patch('numpy.testing.assert_allclose', mock)
        v = verification.IsCloseAtTime('result', expected, time, rtol, atol)
        result_dict = {'result': result, 'foo': 'bar'}
        check = v.verify(result_dict)
        mock.assert_called_once_with(1, expected, rtol, atol)
        result.assert_called_once_with(time)
        assert not check.failed
        assert not check.what

    def test_verify_failure(self, mocker):
        result = mocker.Mock(name='result')
        result.return_value = 1
        expected = 5
        time = 2
        rtol = 3
        atol = 4

        mock = mocker.Mock()
        mocker.patch('numpy.testing.assert_allclose', mock)
        mock.side_effect = AssertionError('foo')
        v = verification.IsCloseAtTime('result', expected, time, rtol, atol)
        result_dict = {'result': result, 'foo': 'bar'}
        check = v.verify(result_dict)
        mock.assert_called_once_with(1, expected, rtol, atol)
        result.assert_called_once_with(time)
        assert check.failed
        assert check.what == 'foo'
