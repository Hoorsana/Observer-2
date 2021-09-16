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
    def pymodbus_context(self):
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
    def data(self):
        return {
            "context": {
                "factory": "pymodbus.datastore.context.ModbusServerContext",
                "slaves": {
                    "hr": {
                        "factory": "pymodbus.datastore.ModbusSequentialDataBlock",
                        "address": 0,
                        "value": 0,
                        "length": 100,
                    },
                    "ir": {
                        "factory": "pymodbus.datastore.ModbusSequentialDataBlock",
                        "address": 0,
                        "value": 0,
                        "length": 100,
                    },
                    "co": {
                        "factory": "pymodbus.datastore.ModbusSequentialDataBlock",
                        "address": 0,
                        "value": 0,
                        "length": 100,
                    },
                    "di": {
                        "factory": "pymodbus.datastore.ModbusSequentialDataBlock",
                        "address": 0,
                        "value": 0,
                        "length": 100,
                    },
                    "zero_mode": True,
                },
            },
            "slave_layout": {
                "holding_registers": {
                    "variables": [
                        {"name": "str", "type": "str", "length": 5, "address": 5},
                        {"name": "i", "type": "i32"},
                        {
                            "name": "struct",
                            "type": "struct",
                            "fields": [
                                {"name": "CHANGED", "format": "u1"},
                                {"name": "ELEMENT_TYPE", "format": "u7"},
                                {"name": "ELEMENT_ID", "format": "u5"},
                            ],
                            "address": 19,
                        },
                        {"name": "f", "type": "f16"},
                    ],
                    "byteorder": "<",
                    "wordorder": ">",
                },
                "input_registers": {
                    "variables": [
                        {"name": "a", "type": "u16"},
                        {"name": "b", "type": "u16"},
                        {"name": "c", "type": "u16"},
                    ],
                    "byteorder": ">",
                },
                "coils": [
                    {"name": "x", "size": 3},
                    {"name": "y", "size": 1, "address": 7},
                    {"name": "z", "size": 5},
                    {"name": "u", "size": 1},
                    {"name": "v", "size": 2},
                ],
                "discrete_inputs": [
                    {"name": "a", "size": 1},
                    {"name": "b", "size": 2},
                    {"name": "c", "size": 3},
                ],
            },
            "single": True,
        }

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
    def pylab_context(self, pymodbus_context, slave_layout):
        return context.ServerContext(pymodbus_context, slave_layout)

    def test_load(self, pylab_context, data, pymodbus_context):
        loaded = context.ServerContext.load(**data)
        assert (
            loaded._context._slaves[0].zero_mode
            == pymodbus_context._slaves[0].zero_mode
        )
        assert (
            loaded._context._slaves[0].store["d"].values
            == pymodbus_context._slaves[0].store["d"].values
        )
        assert (
            loaded._context._slaves[0].store["c"].values
            == pymodbus_context._slaves[0].store["c"].values
        )
        assert (
            loaded._context._slaves[0].store["i"].values
            == pymodbus_context._slaves[0].store["i"].values
        )
        assert (
            loaded._context._slaves[0].store["h"].values
            == pymodbus_context._slaves[0].store["h"].values
        )
        assert loaded._slave_layout == pylab_context._slave_layout

    def test_set_input_registers_get_input_registers(self, pylab_context):
        values = {"a": 7, "b": 8, "c": 9}
        pylab_context.set_input_registers(values)
        assert pylab_context.get_input_registers() == values

    def test_set_holding_registers_get_holding_registers(self, pylab_context):
        pylab_context.set_holding_registers(
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
        assert pylab_context.get_holding_registers() == {
            "str": "hello",
            "i": 12,
            "struct": {
                "CHANGED": 1,
                "ELEMENT_TYPE": 33,
                "ELEMENT_ID": 7,
            },
            "f": pytest.approx(3.4, abs=0.001),
        }

    def test_set_coils_get_coils(self, pylab_context):
        values = {"x": [0, 1, 0], "y": 0, "z": [1, 0, 1, 0, 0], "u": 1, "v": [1, 1]}
        pylab_context.set_coils(values)
        assert pylab_context.get_coils() == values

    def test_set_discrete_inputs_get_discrete_inputs(self, pylab_context):
        values = {"a": 1, "b": [1, 0], "c": [1, 0, 0]}
        pylab_context.set_discrete_inputs(values)
        assert pylab_context.get_discrete_inputs(values) == values
