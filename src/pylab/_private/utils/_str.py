from __future__ import annotations

import re


def load_range(expr: str) -> tuple[float, float]:
    """Extract ``lo`` and ``hi`` from a range expression ``lo..hi``.

    There must be at least two dots. Leading and trailing white spaces
    are allowed. White spaces between ``lo`` resp. ``hi`` and ``..`` are
    allowed.

    Args:
        expr: A range expression of the form ``"lo..hi"``

    Returns:
        The numbers ``lo`` and ``hi``
    """
    # Regex for numbers:
    #      Optional sign
    #                  With comma
    #                                 Or...
    #                                  Optional signl
    #                                             No comma
    num = '[\\+-]{0,1}[0-9]+[.,][0-9]+|[\\+-]{0,1}[0-9]+'
    whitespace = '[ ]*'
    # Regex for range expression:
    #                    Leading whitespace
    #                                A number
    #                                                   At least two dots
    #                                                                   A number
    #                                                                          Trailing whitespace
    matches = re.match(f'{whitespace}({num}){whitespace}\\.+{whitespace}({num}){whitespace}$', expr)
    if matches is None or matches.lastindex != 2:
        raise ValueError(f'Failed to read range expression: {expr}')
    min_, max_ = map(float, [matches.group(1), matches.group(2)])
    return min_, max_


def is_valid_id(id: str):
    """Check if ``id`` is a valid id in the sense of the pylab specification.

    Args:
        id: The id to check
    """
    return '.' not in id
