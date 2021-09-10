# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from pylab.live.plugin.modbus import registers


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
