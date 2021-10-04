# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import importlib
from typing import Any, Sequence, TypeVar

from pylab.core.typing import ArrayLike

_T = TypeVar("T")


def getattr_from_module(attr: str) -> Any:
    """Get attribute from module by string.

    The string must be the path to a fully qualified module member, e.g.
    ``'fully.qualified.module.path.to.member'``. The method will try to
    guess which part of ``attr`` is ``'fully.qualified.module'`` and
    which is ``'path.to.member'``.

    Args:
        attr: The attribute

    Returns:
        The module member

    Raises:
        AttributeError: If guessing fails

    Example:
        >>> ValidationInfo = getattr_from_module('pylab.core.infos.ValidationInfo')
    """
    tokens = attr.split(".")
    try:
        index = 1
        while True:
            module = importlib.import_module(".".join(tokens[:index]))
            index += 1
    except ModuleNotFoundError as error:
        module_not_found = error
    else:
        module_not_found = None

    try:
        return recursive_getattr(module, ".".join(tokens[index - 1 :]))
    except AttributeError as attribute_error:
        msg = (
            "Failed to getattr from module:\n\n\t"
            + str(attribute_error)
            + "\n\nUsed the module: "
            + ".".join(tokens[: index - 1])
        )
        if module_not_found is not None:
            msg += (
                "; tried to use "
                + ".".join(tokens[:index])
                + " but failed with the following error:\n\n\t"
                + str(module_not_found)
            )
        raise AttributeError(msg)


def recursive_getattr(obj: Any, attr: str) -> Any:
    for token in attr.split("."):
        obj = getattr(obj, token)
    return obj


def split_by_attribute(seq: Sequence[_T], attr: str) -> dict[str, list[_T]]:
    """Split a sequence into equivalence classes w/r to an attribute.

    Args:
        seq: A sequence of hashable objects
        attr: The name of an attribute common to all elements of ``seq``

    Returns:
        A dictionary which maps ``value`` to a list of the elements of
        the equivalence class of elements ``elem`` of ``seq`` with
        ``elem.attr == value``.

        The ordering of the elements of ``seq`` is preseved in the
        equivalence classes.
    """
    values = {getattr(each, attr) for each in seq}
    return {val: [each for each in seq if getattr(each, attr) == val] for val in values}
