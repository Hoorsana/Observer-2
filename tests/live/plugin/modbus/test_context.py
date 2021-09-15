# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
import pymodbus.datastore
import pymodbus.datastore.context

from pylab.live.plugin.modbus import context
from pylab.live.plugin.modbus import layout
from pylab.live.plugin.modbus import registers
from pylab.live.plugin.modbus import coils


class TestServerContext:
    @pytest.fixture
    def server_context(self):
        return pymodbus.datastore.context.ModbusServerContext(
            pymodbus.datastore.ModbusSlaveContext(
                hr=pymodbus.datastore.ModbusSequentialDataBlock(0, [0] * 100),
                ir=pymodbus.datastore.ModbusSequentialDataBlock(0, [0] * 100),
                co=pymodbus.datastore.ModbusSequentialDataBlock(0, [0] * 100),
                di=pymodbus.datastore.ModbusSequentialDataBlock(0, [0] * 100),
                zero_mode=True,
            ),
        )

    @pytest.fixture
    def slave_layout(self):
        return layout.SlaveContextLayout(
            holding_registers=registers.RegisterLayout(
                [
                    registers.Str("str", length=5, address=2),
                    registers.Number("i", "i32"),
                    registers.Struct(
                        "struct",
                        [
                            registers.Field("CHANGED", "u1"),
                            registers.Field("ELEMENT_TYPE", "u7"),
                            registers.Field("ELEMENT_ID", "u5"),
                        ],
                        address=19,
                    ),
                    registers.Number("f", "f16"),
                ]
            ),
            input_registers=registers.RegisterLayout(
                [
                    registers.Number("a", "u16"),
                    registers.Number("b", "u16"),
                    registers.Number("c", "u16"),
                ],
                byteorder=">",
            ),
            coils=coils.CoilLayout(
                [
                    coils.Variable("x", 3),
                    coils.Variable("y", 1, address=7),
                    coils.Variable("z", 5),
                    coils.Variable("u", 1),
                    coils.Variable("v", 2),
                ]
            ),
            discrete_inputs=coils.CoilLayout(
                [
                    coils.Variable("a", 1),
                    coils.Variable("b", 2),
                    coils.Variable("c", 3),
                ]
            ),
        )

    @pytest.fixture
    def context(self, server_context, slave_layout):
        return context.ServerContext(server_context, slave_layout)

    def test_set_input_registers_get_input_registers(self, context):
        values = {"a": 7, "b": 8, "c": 9}
        context.set_input_registers(values)
        assert context.get_input_registers() == values

    def test_set_holding_registers_get_holding_registers(self, context):
        context.set_holding_registers(
            {
                "str": "hello",
                "i": 12,
                "struct": {
                    "CHANGED": 1,
                    "ELEMENT_TYPE": 33,
                    "ELEMENT_ID": 7,
                },
                "f": 3.4,
            }
        )
        assert context.get_holding_registers() == {
            "str": "hello",
            "i": 12,
            "struct": {
                "CHANGED": 1,
                "ELEMENT_TYPE": 33,
                "ELEMENT_ID": 7,
            },
            "f": pytest.approx(3.4, abs=0.001),
        }

    def test_set_coils_get_coils(self, context):
        values = {"x": [0, 1, 0], "y": 0, "z": [1, 0, 1, 0, 0], "u": 1, "v": [1, 1]}
        context.set_coils(values)
        assert context.get_coils() == values

    def test_set_discrete_inputs_get_discrete_inputs(self, context):
        values = {"a": 1, "b": [1, 0], "c": [1, 0, 0]}
        context.set_discrete_inputs(values)
        assert context.get_discrete_inputs(values) == values
