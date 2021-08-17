# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from pylab.core import report


class Test_Severity:
    @pytest.mark.parametrize(
        "lhs, rhs",
        [
            (report.INFO, report.WARNING),
            (report.INFO, report.FAILED),
            (report.INFO, report.PANIC),
            (report.WARNING, report.FAILED),
            (report.WARNING, report.PANIC),
            (report.FAILED, report.PANIC),
        ],
    )
    def test_lt(self, lhs, rhs):
        assert lhs < rhs


class TestLogEntry:
    @pytest.mark.parametrize(
        "what, severity, expected",
        [
            ("foo", report.INFO, False),
            ("bar", report.WARNING, False),
            ("spam", report.FAILED, True),
            ("eggs", report.PANIC, True),
        ],
    )
    def test_failed(self, what, severity, expected):
        log_entry = report.LogEntry(what, severity)
        assert log_entry.failed == expected


@pytest.mark.skip
class TestReport:
    ...
