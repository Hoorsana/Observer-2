# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import enum
from typing import List, Union

import pymodbus.client.sync
import pymodbus.constants
import pymodbus.payload

import itertools
import dataclasses

_ValueType = Union[int, float, str, List[bool]]

_DEFAULT_SLAVE: Final[int] = pymodbus.constants.Defaults.UnitId

_ENCODE_DISPATCH = {
    "str": "add_string",
    "bits": "add_bits",
    "i8": "add_8bit_int",
    "i16": "add_16bit_int",
    "i32": "add_32bit_int",
    "i64": "add_64bit_int",
    "u8": "add_8bit_uint",
    "u16": "add_16bit_uint",
    "u32": "add_32bit_uint",
    "u64": "add_64bit_uint",
    "f16": "add_16bit_float",
    "f32": "add_32bit_float",
    "f64": "add_64bit_float",
}

_DECODE_DISPATCH = {
    "str": "decode_string",
    "bits": "decode_bits",
    "i8": "decode_8bit_int",
    "i16": "decode_16bit_int",
    "i32": "decode_32bit_int",
    "i64": "decode_64bit_int",
    "u8": "decode_8bit_uint",
    "u16": "decode_16bit_uint",
    "u32": "decode_32bit_uint",
    "u64": "decode_64bit_uint",
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


class Endian:  # Can't use enum for this, as pymodbus requires raw ``str`` values!
    little = pymodbus.constants.Endian.Little
    big = pymodbus.constants.Endian.Big


class TypeMismatchError(Exception):
    pass


class InvalidValueError(Exception):
    pass


class MissingSizeError(Exception):
    pass


class FieldNotFoundError(Exception):
    pass


def _decode(
    decoder: pymodbus.payload.BinaryPayloadDecoder,
    type: str,
    size: Optional[int] = None,
) -> _ValueType:
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
    if type == "str":
        if size is None:
            raise MissingSizeError()  # TODO
        return d(size)
    elif type == "bits":
        if size is None:
            raise MissingSizeError()  # TODO
        result = []
        for _ in range(size):
            result += d()
        return result
    return d()


def _encode(
    builder: pymodbus.payload.BinaryPayloadDecoder, type: str, value: _ValueType
) -> None:
    """Encode a value into a payload builder.

    Args:
        builder: The builder to encode in
        type: The type of the element
        value: The value to encode
    """
    getattr(builder, _ENCODE_DISPATCH[type])(value)


_MATCHING_TYPES = {
    "str": str,
    "bits": list,
    "i8": int,
    "i16": int,
    "i32": int,
    "i64": int,
    "u8": int,
    "u16": int,
    "u32": int,
    "u64": int,
    "f16": float,
    "f32": float,
    "f64": float,
}


class Field:
    def __init__(
        self,
        name: str,
        type: str,
        length: Optional[int] = None,
        address: Optional[int] = None,
    ) -> None:
        self._name = name
        self._type = type
        self._length = length
        self.address = address

    def __repr__(self) -> str:
        return f"field(name={self._name}, type={self._type}, size_in_bytes={self._size_in_bytes}, address={self.address})"

    def check_value(self, value: _ValueType) -> bool:
        """Check if the space allocated for ``self`` can hold ``value``.

        This check is only for strings and bit sequences. Strings are
        expected to be equal or smaller than the allocated space. Bit
        sequences are expected to be *exactly* as large as the allocated
        space.

        Integers and floating point numbers are *not* checked for
        numerical bounds. This is handled later by the payload builder.

        Raises:
            TypeMismatchError:
                If ``type(value)`` does not match ``self.type``
        """
        if type(value) != _MATCHING_TYPES[self._type]:
            raise TypeMismatchError()  # TODO
        # TODO Check that type of bit sequence is list[bool].
        if self._type == "str":
            return len(value) <= self.size_in_bytes
        if self._type == "bits":
            return len(value) // 8 == self.size_in_bytes

    def decode(self, decoder: pymodbus.payload.BinaryPayloadDecoder) -> None:
        if isinstance(self._type, tuple):
            # # TODO Check if size is specified:
            # if self._size is not None:
            #     # TODO Split result according to sizes
            # We expect tuples to hold two 8-bit types, so size (in bytes)
            # is always 1.
            return tuple(_decode(decoder, t, size=1) for t in self._type)
        result = _decode(decoder, self._type, self.size_in_bytes)
        # Trim strings and bit sequences to size:
        if self._type == "str":
            return result[:self.size_in_bytes]
        # # TODO Replace size_in_bytes with size (which may is in bytes
        # # for "str" and in bits for "bits")
        # if self._type == "bits":
        #     return result[self._size]
        return result

    def encode(self, builder: pymodbus.payload.BinaryPayloadDecoder, value: _ValueType) -> None:
        """Encode a value into a payload builder.

        Args:
            builder: The builder to encode in
            value: The value to encode
        """
        if isinstance(self._type, tuple):
            assert isinstance(value, tuple)
            assert len(self._type) == len(value)
            for t, v in zip(self._type, value):
                _encode(builder, t, v)
        else:
            # Pad the string if its smaller than the allocated memory.
            if self._type == "str":
                value += (self.size_in_bytes - len(value)) * " "
            _encode(builder, self._type, value)

    @property
    def name(self) -> str:
        return self._name

    @property
    def type(self) -> str:
        return self._type

    @property
    def size_in_bytes(self) -> int:
        if self._length is None:
            if isinstance(self._type, tuple):
                # TODO Assert that all elements of the type are 1 byte large!
                return len(self._type)
            else:
                return _get_size_of_type_in_bytes(self._type)
        if self._type == "str":
            return self._length
        return (self._length + 7) // 8

    @property
    def size_in_registers(self) -> int:
        return (self.size_in_bytes + 1) // 2

    @property
    def end(self) -> int:
        """Return the next free address."""
        return self.address + self.size_in_registers


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
    if isinstance(type, tuple):
        return sum(_get_size_of_type_in_bytes(elem) for elem in type)
    if type not in _SIZE_IN_BYTES:
        raise MissingSizeError(f"No size found for type: {type}")
    return _SIZE_IN_BYTES[type]


@dataclasses.dataclass
class Payload:
    """A chunk of registers for a single write operation.

    Attributes:
        address: Indicates at what register to write
        values: The value to write
    """

    address: int
    values: list[bytes]


class ModbusRegisterMapping:
    def __init__(
        self, fields, byteorder: str = Endian.little, wordorder: str = Endian.big
    ) -> None:
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

    def build_payload(self, values: dict[str, _ValueType]) -> list[Payload]:
        """Build data for writing ``values`` to register.

        Args:
            values: A dict mapping field values to

        Returns: A list of ``Payload`` objects, one for each

        Note that a highly fragmented payload will result in more items
        in the list, and, thus, a larger amount of IO operations.
        """
        result = []
        builder = pymodbus.payload.BinaryPayloadBuilder(
            byteorder=self._byteorder, wordorder=self._wordorder
        )
        chunk = self._fields[0].address  # Begin of current chunk

        def build_chunk():
            payload = builder.build()
            if payload:
                result.append(Payload(chunk, builder.build()))
                builder.reset()

        # FIXME Improve the algorithm!
        next_address = chunk  # Next address must be correct on first pass!
        for field, next_ in itertools.zip_longest(
            self._fields, self._fields[1:], fillvalue=None
        ):
            value = values.pop(field.name, None)
            if value is None:
                build_chunk()
                if next_ is not None:
                    chunk = next_.address
                continue
            if field.type in {"str", "bits"} and not field.check_value(value):
                raise InvalidValueError()  # TODO
            field.encode(builder, value)
            # Check if chunk must be built!
            if next_ is None:
                build_chunk()
            elif field.end != next_.address:
                build_chunk()
                chunk = next_.address

        if values:
            raise FieldNotFoundError()  # TODO
        return result

    def decode_registers(
        self, registers: list[int], fields_to_decode: Optional[Iterable[str]] = None
    ) -> dict[str, _ValueType]:
        """Decode registers into Python types.

        Args:
            registers: The registers to decode
            fields_to_decode:
                The names of the fields that occur in ``registers``
        """
        if fields_to_decode is None:
            fields_to_decode = [field.name for field in self._fields]
        decoder = pymodbus.payload.BinaryPayloadDecoder.fromRegisters(
            registers, byteorder=self._byteorder, wordorder=self._wordorder
        )
        result = {}
        # FIXME Improve the algorithm!
        end_of_last_read = None
        for field in self._fields:
            if field.name not in fields_to_decode:
                continue
            if end_of_last_read is None:
                end_of_last_read = field.address
            decoder.skip_bytes(2 * (field.address - end_of_last_read))
            result[field.name] = field.decode(decoder)
            end_of_last_read = field.end
        return result

    def get_field_dimensions(self, field: str) -> tuple[int, int]:
        f = next((f for f in self._fields if f.name == field), None)
        if f is None:
            raise FieldNotFoundError()  # TODO
        return f.address, f.size_in_registers

    @property
    def size(self) -> int:
        """Return the total size of the layout in registers."""
        return self._fields[-1].end - self._fields[0].address

    @property
    def address(self) -> int:
        """Return the starting address of the layout."""
        return self._fields[0].address


class ModbusClient:
    def __init__(
        self,
        client: pymodbus.client.sync.ModbusClientMixin,
        mapping: ModbusRegisterMapping,
        single: bool = True
    ):
        self._client = client
        if single:
            self._mapping = {_DEFAULT_SLAVE: mapping}
        else:
            self._mapping = mapping

    def read_holding_register(
        self, field: str, unit: Hashable = _DEFAULT_SLAVE
    ) -> _ValueType:
        mapping = self._mapping[unit]
        address, size = mapping.get_field_dimensions(field)
        result = self._client.read_holding_registers(address, size, unit=unit)
        d = mapping.decode_registers(result.registers, fields_to_decode={field})
        return d[field]

    def read_holding_registers(
        self, fields: Optional[Iterable[str]] = None, unit: Hashable = _DEFAULT_SLAVE
    ) -> dict[str, _ValueType]:
        mapping = self._mapping[unit]
        result = self._client.read_holding_registers(
            mapping.address, mapping.size, unit=unit
        )
        return mapping.decode_registers(result.registers, fields)

    def write_register(
        self, field: str, value: _ValueType, unit: Hashable = _DEFAULT_SLAVE
    ) -> None:
        self.write_registers({field: value}, unit)

    def write_registers(
        self, values: dict[str, _ValueType], unit: Hashable = _DEFAULT_SLAVE
    ) -> None:
        payloads = self._mapping[unit].build_payload(values)
        for payload in payloads:
            self._client.write_registers(
                payload.address, payload.values, skip_encode=True, unit=unit
            )

    @property
    def client(self) -> pymodbus.client.sync.ModbusClientMixin:
        return self._client


# TODO coils (holding, input), registers (holding, input) -> vier Tabellen?
# TODO Add ``unit`` parameter plus test for reading from multiple servers
