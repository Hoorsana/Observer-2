# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Command line interface for pylab.

The following return codes may be returned: 0 (success), 1 (general
failure), 8 (test failed), 9 (test execution failed).

Example:
    >>> pylab-cli test.yml details.yml -a asserts.yml -dump dump.yml
"""

from __future__ import annotations

import argparse
import sys
import traceback

from pylab.core import errors
from pylab.core import workflow

_parser = argparse.ArgumentParser(
    description="Execute a pylab test",
    epilog="""
        ...
        """,
)
_parser.add_argument("driver", help="Fully qualified path to driver module")
_parser.add_argument("test", help="Path to the test file")
_parser.add_argument("details", help="Path to details file")
_parser.add_argument("-a", "--asserts", dest="asserts", help="Path the asserts file")
_parser.add_argument("-d", "--dump", dest="dump", help="Path for dumping results")


def _parse(args: list[str]) -> argparse.Namespace:
    return vars(_parser.parse_args(args))


def _format_exception_with_traceback(e: Exception) -> str:
    return traceback.format_exception(None, e, e.__traceback__)


def main():
    try:
        args = _parse(sys.argv[1:])
        workflow.run_from_files(**args)
    except AssertionError as e:
        e = _format_exception_with_traceback(e)
        print(f"pylab-cli: test failed with the following AssertionError:\n{e}")
        sys.exit(8)
    except errors.PylabError as e:
        e = _format_exception_with_traceback(e)
        print(f"pylab-cli: error: {e}\n", file=sys.stderr)
        sys.exit(9)
