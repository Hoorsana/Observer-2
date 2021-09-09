# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from pylab.live.plugin.modbus import coils


class TestCoilLayout:
    @pytest.fixture
    def layout(self):
        return coils.CoilLayout(
            [
                coils.Variable("x", 3),
                coils.Variable("y", 1, address=7),
                coils.Variable("z", 5),
                coils.Variable("u", 1),
                coils.Variable("v", 2),
            ]
        )

    def test_build_payload(self, layout):
        payload = layout.build_payload(
            {
                "x": [0, 1, 0],
                "y": 1,
                "z": [0, 0, 1, 1, 0],
                "v": [0, 1]
            }
        )
        assert payload == [
            coils.Chunk(0, [0, 1, 0]),
            coils.Chunk(7, [1, 0, 0, 1, 1, 0]),
            coils.Chunk(14, [0, 1])
        ]
