# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import dataclasses
import functools
import pickle
import traceback
from typing import Any, Optional


@functools.total_ordering
class _Severity:
    def __init__(self, text: str, value: int) -> None:
        self._text = text
        self._value = value

    def __repr__(self) -> str:
        return self._text

    def __lt__(self, other) -> bool:
        if not isinstance(other, _Severity):
            return False
        return self._value < other._value


INFO = _Severity("INFO", 0)
WARNING = _Severity("WARNING", 1)
FAILED = _Severity("FAILED", 2)
PANIC = _Severity("PANIC", 3)


# FIXME Do error reporting using a global logger object. That makes it
# unnecessary to pass the LogEntries all across the call stack.


# FIXME It would be prudent to make this frozen, but this will cause a
# FrozenInstanceError in the simulink driver.
@dataclasses.dataclass
class LogEntry:
    what: str
    severity: _Severity = INFO
    data: Optional[dict[str, Any]] = dataclasses.field(default_factory=dict)

    def __str__(self):
        return f"{self.severity}: {self.what}; {self.data}"

    @property
    def failed(self):
        return self.severity >= FAILED

    @property
    def msg(self):  # TODO Rename?
        return f"{self.severity}: {self.what}; {self.data}"

    def expect(self, severity: _Severity = INFO) -> None:
        """Raise an assertion error if the severity is not as expected.

        Args:
            severity: The expected severity
        """
        if self.severity != severity:
            raise AssertionError(
                f'Log has severity "{self.severity}", expected severity "{severity}". Logbook: {self.what}'
            )


@dataclasses.dataclass(frozen=True)
class Report:
    """Basic report class.

    Attributes:
        failed: True if the execution of the test failed
        what: A complete log of the test
    """

    logbook: list[LogEntry]  # Contains everything that happened during the test.
    results: dict[str, Any] = dataclasses.field(default_factory=dict)
    data: Optional[dict[str, Any]] = dataclasses.field(default_factory=dict)
    # map: name -> logged_data

    @property
    def failed(self):
        return any(each.failed for each in self.logbook)

    @property
    def what(self) -> str:
        result = "\n".join(each.msg for each in self.logbook)
        if self.data:
            result += "\n\nDATA:\n\n" + "\t\n".join(
                f"{k}: {str(v)}" for k, v in self.data.items()
            )
        return result

    def dump(self, PathLike: str) -> None:
        """Dump the results to file.

        Args:
            path: The path to dump to

        Raises:
            OSError: If writing to ``path`` fails
        """
        data = self.serialize()
        with open(path, "wb") as f:
            f.write(data)

    def dump_log(self, PathLike: str) -> None:
        """Dump the raw log to file.

        Args:
            path: The path to dump to

        Raises:
            OSError: If writing to ``path`` fails
        """
        with open(path, "w") as f:
            f.write(self.what)

    def serialize(self) -> bytes:
        return pickle.dumps(self)


def load(path: PathLike) -> Report:
    with open(path, "rb") as f:
        return pickle.load(f)
