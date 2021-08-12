# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import posixpath
import yaml

from pylab.shared import infos


def find_relative_path(root: str, path: PathLike) -> str:
    """Find ``path`` relative to ``root``.

    Args:
        root: Base of the relative path
        path: Absolute or relative path to a file

    We try to interpret ``path`` as filesystem path and find the file it
    is pointing to. If ``path`` is relative, the function searches the
    folder containing the original test file (``root``).

    Returns:
        A path to an existing file

    Raises:
        ValueError:
            If none of the viable interpretations leads to an existing
            file
    """
    if posixpath.isabs(path):
        if posixpath.exists(path):
            return path
        raise ValueError(f"File {path} not found")

    paths = [posixpath.join(posixpath.dirname(root), path)]  # Candidates for path.
    for each in paths:
        if posixpath.exists(each):
            return each

    # If no candidates check out, throw an error.
    raise ValueError(f"File {path} not found")
