# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Loader for test infos in YAML."""

from __future__ import annotations

import posixpath
import os

import yaml

from pylab.core import infos
from pylab.core import verification

PHASE_DIR = 'PYLAB_PHASE_DIR'


# FIXME Implement loader using `from_yaml` and `yaml.YAMLObject`?


def load_test(path: str) -> infos.TestInfo:
    """Load test info from ``path``.

    Even on non-UNIX systems, the path must be specified as UNIX
    filesystem path.

    Args:
        path: A filesystem path
    """
    data = _yaml_safe_load_from_file(path)

    targets = [infos.TargetInfo.from_dict(each)
               for each in data['targets']]
    logging = [infos.LoggingInfo(**each)
               for each in data.get('logging', [])]

    # If a phase info is a string, use it as a filesystem path to find
    # the file which holds the actual phase info data. If ``data`` is a
    # relative path, view it as relative to ``path``, or relative to the
    # environment variable ``PYLAB_PHASE_DIR``.
    phase_data = data['phases']
    for index, elem in enumerate(phase_data):
        if isinstance(elem, str):
            phase_path = _find_phase_path(path, elem)
            phase_data[index] = _yaml_safe_load_from_file(phase_path)
    phases = [infos.PhaseInfo.from_dict(each) for each in phase_data]

    return infos.TestInfo(targets, logging, phases)


# FIXME Do assertion loading using `from_yaml` and `yaml.YAMLObject`.
def load_asserts(path: str) -> list[AbstractVerification]:
    """Load a list of assertions from filesystem path.

    Args:
        path: The filesystem path

    Returns:
        The list of assertions

    Raises:
        ...
    """
    with open(path, 'r') as f:
        content = f.read()
    data = yaml.safe_load(content)
    info = [infos.AssertionInfo(**each) for each in data]
    return [verification.load_info(each) for each in info]


def _find_phase_path(root: str, path: str) -> str:
    """Find a phase file.

    Args:
        root:
            Path to the test file which contains a reference to the
            phase file
        path: Absolute or relative path to a phase file

    We try to interpret ``path`` as filesystem path and find the file it
    is pointing to. If ``path`` is relative, the function searches the
    folder containing the original test file (``root``), then the
    folders set by the environment variable ``PHASE_DIR``.

    Note that this function does not check if any of the candidates is
    in fact a valid phase file (i.e. has the correct fields, etc.).

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
        raise ValueError(f'File {path} not found')

    paths = [posixpath.join(posixpath.dirname(root), path)]  # Candidates for path.
    phase_dir = os.environ.get(PHASE_DIR)
    if phase_dir:
        paths.append(posixpath.join(posixpath.dirname(phase_dir), path))
    for each in paths:
        if posixpath.exists(each):
            return each

    raise ValueError(f'File {path} not found')


def _yaml_safe_load_from_file(path: str) -> dict:
    with open(path, 'r') as f:
        content = f.read()
    return yaml.safe_load(content)
