# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import pymodbus.client.sync
import pymodbus.payload

import itertools
import dataclasses

# TODO Use skip_bytes! Does the payload builder also have that function? (Probably not!)

_VALUE_TYPE = "Union[int, float, str, list[bool]]"

_ENCODE_DISPATCH = {
    "str": "add_string",
    "bits": "add_bits",
    "i8": "add_8bit_int",
    "i16": "add_16bit_int",
    "i32": "add_32bit_int",
    "i64": "add_64bit_int",
    "u8": "add_8bit_unsigned_int",
    "u16": "add_16bit_unsigned_int",
    "u32": "add_32bit_unsigned_int",
    "u64": "add_64bit_unsigned_int",
    "f16": "add_16bit_float",
    "f32": "add_32bit_float",
    "f64": "add_64bit_float",
}

_DECODE_DISPATCH = {
    # TODO String, bytes
    "str": "decode_string",
    "bits": "decode_bits",
    "i8": "decode_8bit_int",
    "i16": "decode_16bit_int",
    "i32": "decode_32bit_int",
    "i64": "decode_64bit_int",
    "u8": "decode_8bit_unsigned_int",
    "u16": "decode_16bit_unsigned_int",
    "u32": "decode_32bit_unsigned_int",
    "u64": "decode_64bit_unsigned_int",
    "f16": "decode_16bit_float",
    "f32": "decode_32bit_float",
    "f64": "decode_64bit_float",
}

_SIZE_IN_BYTES = {
    "i8": 1,
    "i16": 2,
    "i32": 4,
    "i64": 8,
    "u8": 1,
    "u16": 2,
    "u32": 4,
    "u64": 8,
    "f16": 2,
    "f32": 4,
    "f64": 8,
}


def _decode(
    decoder: pymodbus.payload.BinaryPayloadDecoder,
    type: str,
    size: Optional[int] = None,
) -> _VALUE_TYPE:
    """Decode from a payload decoder.

    If ``type`` is ``str`` or ``bits``, then ``size`` must specify the
    size of the value in *bytes*. Otherwise, the ``size`` parameter is
    ignored and should not be specified.

    Args:
        decoder: The payload decoder to decode from
        type: The type of the element
        size: The size of the element in bytes

    Returns:
        The decoded element
    """
    d = getattr(decoder, _DECODE_DISPATCH[type])
    if type in {"str", "bits"}:
        if size is None:
            raise ValueError()  # TODO
        return d(size)
    return d()


def _encode(
    builder: pymodbus.payload.BinaryPayloadDecoder, type: str, value: _VALUE_TYPE
) -> None:
    """Encode a value into a payload builder.

    Args:
        builder: The builder to encode in
        type: The type of the element
        value: The value to encode
    """
    getattr(builder, _ENCODE_DISPATCH[type])(value)


class Field:
    def __init__(
        self,
        name: str,
        type: str,
        size_in_bytes: Optional[int] = None,
        address: Optional[int] = None,
    ) -> None:
        self._name = name
        self._type = type
        if size_in_bytes is None:
            self._size_in_bytes = _get_size_of_type_in_bytes(type)
        else:
            self._size_in_bytes = size_in_bytes
        self.address = address

    def __repr__(self) -> str:
        return f"field(name={self._name}, type={self._type}, size_in_bytes={self._size_in_bytes}, address={self.address})"

    @property
    def name(self) -> str:
        return self._name

    @property
    def type(self) -> str:
        return self._type

    @property
    def size_in_bytes(self) -> int:
        return self._size_in_bytes

    @property
    def size_in_registers(self) -> int:
        return (self._size_in_bytes + 1) // 2

    @property
    def end(self) -> int:
        """Return the next free address."""
        return self.address + self.size_in_registers


class NoSizeError(Exception):
    pass


def _get_size_of_type_in_bytes(type: str) -> int:
    """Return the size of ``type`` (in bytes).

    Args:
        type: One of the following:
        ``"i8"``,
        ``"i16"``,
        ``"i32"``,
        ``"i64"``,
        ``"u8"``,
        ``"u16"``,
        ``"u32"``,
        ``"u64"``,
        ``"f16"``,
        ``"f32"``,
        ``"f64"``.

    Raises:
        UnknownTypeError
    """
    if type not in _SIZE_IN_BYTES:
        raise NoSizeError(f"No size found for type: {type}")
    return _SIZE_IN_BYTES[type]


@dataclasses.dataclass
class Payload:
    address: int
    values: list[bytes]


class FieldNotFoundError(Exception):
    pass


class ModbusRegisterMapping:
    def __init__(self, fields, byteorder: str = "<", wordorder: str = ">") -> None:
        self._fields = fields
        self._byteorder = byteorder
        self._wordorder = wordorder

        # Deduce implicit addresses.
        assert fields
        if fields[0].address is None:
            fields[0].address = 0
        for current, last in zip(self._fields[1:], self._fields):
            if current.address is None:
                current.address = last.end
            elif current.address < last.end:
                raise ValueError()  # TODO Conflicting information!
        # print(self._fields)

    def build_payload(self, values: dict[str, _VALUE_TYPE]) -> list[Payload]:
        """Build data for writing ``values`` to register.

        Args:
            values: A dict mapping field values to

        Returns: A list of ``Payload`` objects

        Note that a highly fragmented payload will result in more items
        in the list, and, thus, a larger amount of IO operations.
        """
        result = []
        builder = pymodbus.payload.BinaryPayloadBuilder(
            byteorder=self._byteorder, wordorder=self._wordorder
        )
        chunk = 0  # Begin of current chunk

        def build_chunk():
            payload = builder.build()
            if payload:
                result.append(Payload(chunk, builder.build()))
                builder.reset()

        next_address = 0
        for field in self._fields:
            value = values.pop(field.name, None)
            # print(f"next_address={next_address};field.address={field.address};field.end={field.end};value={value};chunk={chunk}")
            if next_address != field.address or value is None:
                build_chunk()
                chunk = field.end
            else:
                # print(f"_encode(builder, {field.type}, {value})")
                _encode(builder, field.type, value)
            next_address = field.end
        build_chunk()

        if values:
            raise FieldNotFoundError()  # TODO
        return result

    def decode_registers(self, registers: list[int]) -> dict[str, _VALUE_TYPE]:
        decoder = pymodbus.payload.BinaryPayloadDecoder.fromRegisters(
            registers, byteorder=self._byteorder, wordorder=self._wordorder
        )
        result = {}
        for field in self._fields:
            result[field.name] = _decode(decoder, field.type)
        return result

    @property
    def size(self) -> int:
        """Return the total size of the layout."""
        return self._fields[-1].end

    @property
    def address(self) -> int:
        """Return the starting address of the layout."""
        return self._fields[0].address


class ModbusClient:
    def __init__(
        self,
        client: pymodbus.client.sync.ModbusClientMixin,
        mapping: ModbusRegisterMapping,
    ):
        self._client = client
        self._mapping = mapping

    # TODO
    def read_single_holding_register(self, field: str) -> _VALUE_TYPE:
        pass

    def read_holding_registers(self) -> dict[str, _VALUE_TYPE]:
        result = self._client.read_holding_registers(self._mapping.address, self._mapping.size)
        return self._mapping.decode_registers(result.registers)

    def write_register(self, field: str, value: _VALUE_TYPE) -> None:
        self.write_registers({field: value})

    def write_registers(self, values: dict[str, _VALUE_TYPE]) -> None:
        payloads = self._mapping.build_payload(values)
        print(payloads)
        for payload in payloads:
            self._client.write_registers(
                payload.address, payload.values, skip_encode=True
            )

    @property
    def client(self) -> pymodbus.client.sync.ModbusClientMixin:
        return self._client


# TODO coils (holding, input), registers (holding, input) -> vier Tabellen?

if __name__ == "__main__":
    mapping = ModbusRegisterMapping(
        [
            Field("x", "i32", address=3),
            Field("y", "f16"),
            # Field("a", "f16"),
            # Field("b", "f16"), # addr=103),
            # Field("c", "f16"),
        ],
        byteorder="<",
        wordorder=">",
    )
    client = ModbusClient(
        pymodbus.client.sync.ModbusTcpClient(host="localhost", port=5020), mapping
    )
    client.write_register("y", 1.23)
    client.write_register("x", 4567)
    result = client.read_holding_registers()  # {"x": 4567, "y": 1.23}
    print(result)
    client.write_register("y", 4.56)
    result = client.read_holding_registers()  # {"x": 4567, "y": 4.56}
    print(result)
    client.client.close()
