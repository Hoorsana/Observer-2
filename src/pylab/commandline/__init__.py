# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Parser and utility for pylab-cli script."""

from __future__ import annotations

import argparse


_parser = argparse.ArgumentParser(
    description='Execute a pylab test',
    epilog='''
        ...
        '''
)
_parser.add_argument('driver', help='Fully qualified path to driver module')
_parser.add_argument('test', help='Path to the test file')
_parser.add_argument('details', help='Path to details file')
_parser.add_argument('-a', '--asserts', dest='asserts', help='Path the asserts file')
_parser.add_argument('-d', '--dump', dest='dump', help='Path for dumping results')


def parse(args: list[str]) -> argparse.Namespace:
    return vars(_parser.parse_args(args))
