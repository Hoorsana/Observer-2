# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from pylab.live.plugin.modbus import registers
from pylab.live.plugin.modbus.exceptions import (
    InvalidAddressLayoutError,
    VariableNotFoundError,
    DuplicateVariableError,
)


class TestRegisterLayout:
    @pytest.fixture
    def layout(self):
        return registers.RegisterLayout(
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
            ],
            byteorder="<",
            wordorder=">",
        )

    @pytest.fixture
    def data(self):
        return {
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
        }

    @pytest.mark.parametrize(
        "variables, exception",
        [
            (
                [registers.Number("foo", "i64", 2), registers.Number("bar", "i32", 5)],
                InvalidAddressLayoutError,
            ),
            (
                [registers.Number("foo", "i64", 2), registers.Str("foo", 5)],
                DuplicateVariableError,
            ),
        ],
    )
    def test_init_failure(self, variables, exception):
        with pytest.raises(exception) as e:
            registers.RegisterLayout(variables)

    def test_build_payload_failure(self, layout):
        with pytest.raises(VariableNotFoundError):
            layout.build_payload({"str": "hello", "world": "!"})

    def test_load(self, layout, data):
        loaded = registers.RegisterLayout.load(**data)
        assert loaded == layout


class TestPayloadBuilder:
    @pytest.mark.parametrize(
        "type, value, expected, byteorder, wordorder",
        [
            ("i16", 777, [b"\t\x03"], "<", ">"),
            ("i16", 777, [b"\x03\t"], ">", ">"),
            ("i32", 67108864, [b"\x00\x04", b"\x00\x00"], "<", ">"),
            ("i32", 67108864, [b"\x00\x00", b"\x00\x04"], "<", "<"),
            ("f64", 3.141, [b"\t@", b"\xc4 ", b"\xa5\x9b", b"T\xe3"], "<", ">"),
            ("f64", 3.141, [b"\xe3T", b"\x9b\xa5", b" \xc4", b"@\t"], ">", "<"),
        ],
    )
    def test_encode_number_single(self, type, value, expected, byteorder, wordorder):
        builder = registers._PayloadBuilder(byteorder=byteorder, wordorder=wordorder)
        var = registers.Number("", type)
        var.encode(builder, value)
        assert builder.build() == expected

    @pytest.mark.parametrize(
        "payload, expected, byteorder, wordorder",
        [
            (
                [("i16", 777), ("i32", 67108864), ("f64", 3.141)],
                [
                    b"\t\x03",
                    b"\x00\x04",
                    b"\x00\x00",
                    b"\t@",
                    b"\xc4 ",
                    b"\xa5\x9b",
                    b"T\xe3",
                ],
                "<",
                ">",
            ),
        ],
    )
    def test_encode_number_multiple(self, payload, expected, byteorder, wordorder):
        builder = registers._PayloadBuilder(byteorder, wordorder)
        for type_, value in payload:
            var = registers.Number("", type_)
            var.encode(builder, value)
        assert builder.build() == expected

    def test_encode_string(self):
        builder = registers._PayloadBuilder("<", ">")
        var = registers.Str("", 7)
        var.encode(builder, "Hullo")
        assert builder.build() == [b"Hu", b"ll", b"o ", b"  "]


@pytest.mark.parametrize(
    "fields, values, byteorder, wordorder",
    [
        (
            [
                registers.Field("CHANGED", "u1"),
                registers.Field("ELEMENT_TYPE", "u7"),
                registers.Field("ELEMENT_ID", "u8"),
            ],
            {
                "CHANGED": 1,
                "ELEMENT_TYPE": 33,
                "ELEMENT_ID": 7,
            },
            "<",
            ">",
        ),
        pytest.param(
            [
                registers.Field("CHANGED", "u1"),
                registers.Field("ELEMENT_TYPE", "u7"),
                registers.Field("ELEMENT_ID", "u5"),
            ],
            {
                "CHANGED": 1,
                "ELEMENT_TYPE": 33,
                "ELEMENT_ID": 7,
            },
            "<",
            ">",
            id="With padding",
        ),
    ],
)
def test_encode_decode_struct(fields, values, byteorder, wordorder):
    s = registers.Struct("", fields)
    builder = registers._PayloadBuilder(byteorder, wordorder)
    s.encode(builder, values)
    payload = b"".join(builder.build())
    decoder = registers._PayloadDecoder(payload, byteorder, wordorder)
    assert s.decode(decoder) == values


def test_encode_decode_mixed():
    byteorder = ">"
    wordorder = "<"


class TestPayloadDecoder:
    @pytest.mark.parametrize(
        "type, expected, payload, byteorder, wordorder",
        [
            ("i16", 777, b"\t\x03", "<", ">"),
            ("i16", 777, b"\x03\t", ">", ">"),
            ("i32", 67108864, b"\x00\x04\x00\x00", "<", ">"),
            ("i32", 67108864, b"\x00\x00\x00\x04", "<", "<"),
            ("f64", 3.141, b"\t@\xc4 \xa5\x9bT\xe3", "<", ">"),
            ("f64", 3.141, b"\xe3T\x9b\xa5 \xc4@\t", ">", "<"),
        ],
    )
    def test_decode_single(self, type, expected, payload, byteorder, wordorder):
        builder = registers._PayloadDecoder(payload, byteorder, wordorder)
        var = registers.Number("", type)
        assert var.decode(builder) == expected
