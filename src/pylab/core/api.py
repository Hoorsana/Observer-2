# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""API details for driver."""

from __future__ import annotations

import abc
import typing

# typing:
from pylab.core import infos
from pylab.core import report


class AbstractDriver:

    class Test(abc.ABC):

        @abc.abstractmethod
        def execute(self) -> report.Report:
            """Execute the test and return a report including logged
            data.
            """
            pass

    class Details:
        """Class for storing test setup data.

        This class should hold, for instance, device details and the
        connections between the devices.
        """
        pass

    def create(info: infos.TestInfo, details: Details) -> Test:
        """Create and return a ``Test`` object from info and device details.

        Raises:
            pylab.core.errors.LogicError:
                If ``info`` violates the specification

        May also raise implementation specific errors.
        """
        pass

    def load_details(path: str) -> Details:
        """Load details from file ``path``.

        Raises:
            FileNotFoundError: If ``path`` doesn't exist
        """
        pass
