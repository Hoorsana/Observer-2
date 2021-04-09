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

    def __str__(self) -> str:
        return self._text

    def __lt__(self, other) -> bool:
        if not isinstance(other, _Severity):
            return False
        return self._value < other._value


INFO = _Severity('info', 0)
WARNING = _Severity('warning', 1)
FAILED = _Severity('failed', 2)
PANIC = _Severity('panic', 3)


# FIXME Do error reporting using a global logger object. That makes it
# unnecessary to pass the LogEntries all across the call stack.


# FIXME It would be prudent to make this frozen, but this will cause a
# FrozenInstanceError in the simulink driver.
@dataclasses.dataclass
class LogEntry:
    what: str
    severity: _Severity = INFO
    data: Optional[Any] = None

    @property
    def failed(self):
        return self.severity in {FAILED, PANIC}

    @property
    def msg(self):  # TODO Rename?
        return f'{self.severity}: {self.what}; {self.data}'


@dataclasses.dataclass(frozen=True)
class Report:
    """Basic report class.

    Attributes:
        failed: True if the execution of the test failed
        what: A complete log of the test
    """
    logbook: list[LogEntry]  # Contains everything that happened during the test.
    results: dict[str, Any] = dataclasses.field(default_factory=dict)
    # map: name -> logged_data

    @property
    def failed(self):
        return any(each.failed for each in self.logbook)

    @property
    def what(self) -> str:
        return '\n'.join(each.msg for each in self.logbook)

    def dump(self, path: str) -> None:
        """Dump the results to file.

        Args:
            path: The path to dump to

        Raises:
            OSError: If writing to ``path`` fails
        """
        data = self.serialize()
        with open(path, 'wb') as f:
            f.write(data)

    def serialize(self) -> bytes:
        return pickle.dumps(self)


def load(path: str) -> Report:
    with open(path, 'rb') as f:
        return pickle.load(f)
