# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import yaml


# TODO Move typing to ...?
def yaml_safe_load_from_file(path: PathLike) -> dict:
    with open(path, "r") as f:
        content = f.read()
    return yaml.safe_load(content)
