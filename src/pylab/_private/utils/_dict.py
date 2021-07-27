# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
# 
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations


def assert_keys(d: dict[_T, Any],
                required_keys: Optional[set[_T]] = None,
                optional_keys: Optional[set[_T]] = None,
                prefix: str = ''
                ) -> None:
    """Raise InfoError if dict does not have the prescibed keys.

    Args:
        d: The dict to check
        required_keys: The keys that must be present
        optional_keys:
            The keys that may, in addition to the required keys, be present

    Raises:
        errors.InfoError:
            If not all required keys are present or a non-required,
            non-optional key is present
    """
    def pretty_print(s: set[str]):
        return ', '.join(str(elem) for elem in s)
    keys = set(d.keys())
    required_diff = required_keys - keys
    if required_diff:
        raise AssertionError(prefix + 'Missing keys: ' + pretty_print(required_diff) + '. Expected keys: ' + pretty_print(required_keys))
    optional_diff = keys - required_keys - optional_keys
    if optional_diff:
        raise AssertionError(prefix + 'Unexpected keys: ' + pretty_print(optional_diff))
