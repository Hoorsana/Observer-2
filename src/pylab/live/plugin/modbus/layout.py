from __future__ import annotations

import pymodbus.payload
import bitstruct
import struct

import pydantic

_TYPE_TO_STRUCT = {
    # "s8": "b",
    "i16": "h",
    "i32": "i",
    "i64": "l",
    # "u8": "B",
    "u16": "H",
    "u32": "I",
    "u64": "L",
    "f16": "e",
    "f32": "f",
    "f64": "d",
    "t": ...,
}

_BITSTRUCT_TO_STRUCT = {
    # "s8": "b",
    "s16": "h",
    "s32": "i",
    "s64": "l",
    # "u8": "B",
    "u16": "H",
    "u32": "I",
    "u64": "L",
    "f16": "e",
    "f32": "f",
    "f64": "d",
    "t": ...,
}

# See https://docs.python.org/3/library/struct.html
_STRUCT_SIZE = {
    "c": 1,
    "b": 1,
    "B": 1,
    "?": 1,
    "h": 2,
    "i": 4,
    "l": 8,
    "q": 16,
    "e": 2,
    "f": 4,
    "d": 8,
}

_DEFAULT_SLAVE = 0


# types:
# sX - signed int
# uX - unsigned int
# b - bool
# fX - (X=16, 32, 64) float
# tX - text (ASCII, UTF-8)
# p/PX - padding


# TODO Endianess in structs? -> We need our own PayloadBuilder!


class UnknownTypeError(Exception):
    pass


class Endian:  # Can't use enum for this, as pymodbus requires raw ``str`` values!
    little = "<"
    big = ">"


class RegisterMapping:
    def __init__(
        self, variables, byteorder: str = Endian.little, wordorder: str = Endian.big
    ) -> None:
        self._variables = variables
        self._byteorder = byteorder
        self._wordorder = wordorder

        # Deduce implicit addresses.
        assert variables
        if variables[0].address is None:
            variables[0].address = 0
        for current, last in zip(self._variables[1:], self._variables):
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
        builder = _PayloadBuilder(byteorder=self._byteorder, wordorder=self._wordorder)
        chunk = self._variables[0].address  # Begin of current chunk

        def build_chunk():
            payload = builder.build()
            if payload:
                result.append(Payload(chunk, builder.build()))
                builder.reset()

        # FIXME Improve the algorithm!
        next_address = chunk  # Next address must be correct on first pass!
        for field, next_ in itertools.zip_longest(
            self._variables, self._variables[1:], fillvalue=None
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
        self, registers: list[int], variables_to_decode: Optional[Iterable[str]] = None
    ) -> dict[str, _ValueType]:
        """Decode registers into Python types.

        Args:
            registers: The registers to decode
            variables_to_decode:
                The names of the variables that occur in ``registers``
        """
        if variables_to_decode is None:
            variables_to_decode = [field.name for field in self._variables]
        decoder = _PayloadDecoder(
            registers, byteorder=self._byteorder, wordorder=self._wordorder
        )
        result = {}
        # FIXME Improve the algorithm!
        end_of_last_read = None
        for field in self._variables:
            if field.name not in variables_to_decode:
                continue
            if end_of_last_read is None:
                end_of_last_read = field.address
            decoder.skip_bytes(2 * (field.address - end_of_last_read))
            result[field.name] = field.decode(decoder)
            end_of_last_read = field.end
        return result

    def get_field_dimensions(self, field: str) -> tuple[int, int]:
        f = next((f for f in self._variables if f.name == field), None)
        if f is None:
            raise FieldNotFoundError()  # TODO
        return f.address, f.size_in_registers

    @property
    def size(self) -> int:
        """Return the total size of the layout in registers."""
        return self._variables[-1].end - self._variables[0].address

    @property
    def address(self) -> int:
        """Return the starting address of the layout."""
        return self._variables[0].address


class Client:
    def __init__(
        self,
        client: pymodbus.client.sync.ModbusClientMixin,
        mapping: MemoryLayout,
        single: bool = True,
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


class Variable:
    """Represents a variable in memory.

    Variables begin and end at register bounds, regardless of their actual size.
    """

    def __init__(self, name: str, address: Optional[int] = None) -> None:
        self._name = name
        self._address = address

    @property
    def name(self) -> str:
        return self._name

    @property
    def address(self) -> int:
        return self._address

    @property
    def size_in_registers(self) -> int:
        return self.size_in_bytes + (self.size_in_bytes % 2)

    @property
    def end(self) -> int:
        return self._address + self.size_in_registers

    def touches(self, other: Element) -> bool:
        return self._address == other.end

    def align_with(self, other: Element) -> None:
        self._address = other.end

    @property
    def size_in_bytes(self) -> int:
        pass

    def decode(self, decoder: pymodbus.payload.BinaryPayloadDecoder) -> _ValueType:
        pass

    def encode(
        self, encoder: pymodbus.payload.BinaryPayloadBuilder, value: _ValueType
    ) -> list[bytes]:
        pass


@pydantic.dataclasses.dataclass
class Field:
    name: str
    format: str

    # TODO Validate that format is correct using pydantic!

    def size_in_bits(self) -> int:
        return int(self.format[1:])


class Struct(Variable):
    def __init__(
        self, name: str, fields: list[Field], address: Optional[int] = None
    ) -> None:
        super().__init__(name, address)
        self._fields = field

    def _format(self) -> str:
        result = "".join(field.format for field in self._fields)
        padding = sum(field.size_in_bits for field in fields) % 8
        if padding != 0:
            result += f"p{padding}"
        return result

    def decode(self, decoder: _PayloadDecoder) -> dict[str, _ValueType]:
        values = decoder.decode_struct(self._format)
        return dict(zip(self._fields, values))

    def encode(
        self,
        builder: _PayloadBuilder,
        value: dict[str, _ValueType],
    ) -> None:
        # TODO Error handling!
        values = [value[field.name] for field in self._fields]
        builder.add_struct(self._format(), values)


class Str(Variable):
    def __init__(self, name: str, length: int, address: Optional[int] = None) -> None:
        super().__init__(name, address)
        self._length = length

    def decode(self, decoder: _PayloadDecoder) -> str:
        return decoder.decode_string(self._length)

    def encode(self, builder: _PayloadBuilder, value: str) -> None:
        assert len(value) < self._length  # TODO
        builder.add_string(str)


class Number(Variable):
    def __init__(self, name: str, type: str, address: Optional[int] = None) -> None:
        super().__init__(name, address)
        self._type = type
        self._address = address

    @property
    def size_in_bytes(self) -> int:
        bits = int(self._type[1:])
        return (bits + 7) // 8

    def decode(self, decoder: pymodbus.payload.BinaryPayloadDecoder) -> _ValueType:
        return decoder.decode_number(self._type)

    def encode(self, builder: _PayloadBuilder, value: _ValueType):
        builder.add_number(self._type, value)


class _PayloadDecoder:
    def __init__(
        self, payload: bytes, byteorder: str = "<", wordorder: str = ">"
    ) -> None:
        self._payload = payload
        self._byteorder = byteorder
        self._wordorder = wordorder

    def decode_struct(
        self, compiled_format: bitstruct.CompiledFormat
    ) -> tuple[_ValueType]:
        pass

    def skip_bytes(self, count: int = 1) -> None:
        pass


class _PayloadBuilder:
    def __init__(self, byteorder: str = "<", wordorder: str = ">") -> None:
        self._byteorder = byteorder
        self._wordorder = wordorder
        self._payload = []

    def load(self, payload: list[bytes]) -> None:
        """Push double byte registers onto payload.

        Args:
            payload: A list of double byte registers

        Use this to manually add bytes to the payload builder instead of
        adding them using class methods!
        """
        self._payload.extend(payload)

    def reset(self) -> None:
        self._payload = []

    def build(self) -> list[bytes]:
        return self._payload

    def add_struct(self, fmt: str, values: list[_ValueType]) -> None:
        # TODO Endianess?
        cf = bitstruct.compile(fmt)
        packed: bytes = cf.pack(*values)
        # Don't use ``_pack``, as we don't want to use word order to unpack!
        self._payload.extend([packed[2 * i : 2 * i + 2] for i in range(len(packed))])

    def add_number(self, type: str, value: int) -> None:
        """

        Args:
            type: The type of the number

        8-bit formats are *not* allowed!
        """
        fmt = _TYPE_TO_STRUCT.get(type)
        if fmt is None:
            raise UnknownTypeError()  # TODO
        self._payload.extend(self._pack(fmt, value))

    def _pack(self, fmt: str, value: _ValueType) -> bytes:
        """Pack and pad value into format.

        Args:
            fmt: The ``struct`` format to pack the value into
            value: The value to pack and pad

        Returns:
            A ``bytes`` object of length ?????????
        """
        # Use correct wordorder by formatting in big endian and then
        # reversing if wordorder is little endian. Based on
        # pymodbus.payload.BinaryPayloadBuilder._pack_words.
        packed = struct.pack("!" + fmt, value)
        size = _STRUCT_SIZE[fmt.lower()]
        unpacked = struct.unpack(f"!{size//2}H", packed)
        if self._wordorder == Endian.little:
            unpacked = list(unpacked)
            unpacked.reverse()
        return [struct.pack(self._byteorder + "H", word) for word in unpacked]


# ???
def _visit_blocks(
    variables: list[Variables], selection: set[str], fn: Callable
) -> None:
    """Apply ``fn`` to every chunk."""
    results = []
    current = []

    def finish_chunk():
        if not current:
            return
        result.append(fn(current))
        current = []

    for var in [x for x in variables if x in selection]:
        selection.remove(var)
        if not current:
            current.append(var)
        else:
            if var.touches(current[-1]):
                finish_chunk()
            current.append(var)
    finish_chunk()

    if selection:
        raise ValueError()  # TODO

    return result
