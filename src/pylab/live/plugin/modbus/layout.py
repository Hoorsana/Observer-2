# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import dataclasses

from pylab.live.plugin.modbus.registers import RegisterLayout
from pylab.live.plugin.modbus.coils import CoilLayout


@dataclasses.dataclass
class SlaveContextLayout:
    holding_registers: Optional[registers.RegisterLayout] = None
    input_registers: Optional[registers.RegisterLayout] = None
    coils: Optional[coils.CoilLayout] = None
    discrete_inputs: Optional[coils.CoilLayout] = None

    @classmethod
    def load(cls, holding_registers, input_registers, coils, discrete_inputs) -> cls:
        return cls(
            holding_registers=RegisterLayout.load(**holding_registers),
            input_registers=RegisterLayout.load(**input_registers),
            coils=CoilLayout.load(coils),
            discrete_inputs=CoilLayout.load(discrete_inputs),
        )
