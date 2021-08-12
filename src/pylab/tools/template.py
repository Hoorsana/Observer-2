# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import os


def fill(data: dict[str, str], fsrc: str, fdst: Optional[str] = None) -> None:
    """Fill out a template file.

    Args:
        data: Maps fields to their content
        fsrc: Path to the template (input) file
        fdst: Path to the output file (equal to ``fsrc`` by default)
    """
    if fdst is None:
        fdst = fsrc
    with open(fsrc, "r") as f:
        content = f.read()
    for k, v in data.items():
        content = content.replace(k, v)
    with open(fdst, "w") as f:
        f.write(content)


def fill_with_environment_variables(
    fsrc: str, fdst: Optional[str] = None, delim: str = "@"
) -> None:
    """Replace marked expression in file with

    Args:
        fsrc: Path to the template (input) file
        fdst: Path to the output file (equal to ``fsrc`` by default)
        delim: The delimiter used to mark the expressions

    Expressions to be replaced are marked with ``delim`` on both sides
    of the expression, i.e. ``'@EXPR@'`` will be replaced by the
    value of the environment variable ``EXPR``.
    """
    data = {f"@{k}@": v for k, v in os.environ.items()}
    fill(data, fsrc, fdst)
