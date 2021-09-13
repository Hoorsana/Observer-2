# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import dataclasses


@dataclasses.dataclass
class SlaveContextLayout:
    holding_registers: Optional[registers.RegisterLayout] = None
    input_registers: Optional[registers.RegisterLayout] = None
    coils: Optional[coils.CoilLayout] = None
    discrete_inputs: Optional[coils.CoilLayout] = None
