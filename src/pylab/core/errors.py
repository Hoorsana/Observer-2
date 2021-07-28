# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Collection of custom errors."""


class PylabError(Exception):
    pass


class LogicError(PylabError):
    """Raised if driver logic is violated."""
    pass
