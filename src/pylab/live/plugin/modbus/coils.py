from __future__ import annotations

import dataclasses
import itertools
from typing import Union, List

_ValueType = Union[List[bool], bool]


class VariableNotFoundError(Exception):
    pass


class Variable:
    def __init__(self, name: str, size: int, address: Optional[int] = None) -> None:
        """
        Args:
            name: The variable's name
            size: The size in bits
            address: The address in bits
        """
        self._name = name
        self._size = size
        self.address = address

    @property
    def name(self) -> str:
        return self._name

    @property
    def size(self) -> int:
        return self._size

    @property
    def end(self) -> int:
        return self.address + self._size

    def touches(self, other: Variable) -> bool:
        return self.address == other.end

    def align_with(self, other: Variable) -> None:
        self.address = other.end


@dataclasses.dataclass
class Chunk:
    address: int
    values: list[bool]


class CoilLayout:
    def __init__(self, variables: list[Variable]) -> None:
        self._variables = variables

        assert variables
        if variables[0].address is None:
            variables[0].address = 0
        for current, last in zip(self._variables[1:], self._variables):
            if current.address is None:
                current.align_with(last)
            elif current.address < last.end:
                raise ValueError()  # TODO Conflicting information!

    # FIXME This has a healthy amount of code duplication with the register layout's analogous
    # function. Maybe use an abstraction for chunking the memory?
    def build_payload(self, values: dict[str, _ValueType]) -> list[Chunk]:
        result = []
        address = self._variables[0].address
        bits = []

        def build_chunk():
            nonlocal bits
            result.append(Chunk(address, bits))
            bits = []

        for var, next_ in itertools.zip_longest(
            self._variables, self._variables[1:], fillvalue=None
        ):
            value = values.pop(var.name, None)
            if value is None:
                build_chunk()
                if next_ is not None:
                    address = next_.address
                continue
            if isinstance(value, list):
                bits.extend(value)
            else:  # Assuming int/bool/...
                bits.append(bool(value))
            if next_ is None:
                build_chunk()
            elif not next_.touches(var):
                build_chunk()
                address = next_.address

        # If values remain, the corresonding variables are not found in self._variables.
        if values:
            raise VariableNotFoundError()  # TODO
        return result

    def decode_coils(
        self, coils: list[bool], variables_to_decode: Optional[Iterable[str]] = None
    ) -> dict[str, _ValueType]:
        """Decode coils into Python types.

        Args:
            coils: The coils to decode
            variables_to_decode:
                The names of the variables that occur in ``coils``

        Returns:
            A ``dict`` mapping variable names to their value
        """
        if variables_to_decode is None:
            variables_to_decode = [x.name for x in self._variables]
        result = {}
        pointer = 0
        # TODO Place this logic in an extra class!
        end_of_last_read = None
        for var in self._variables:
            if var.name not in variables_to_decode:
                continue
            if end_of_last_read is None:  # (First pass)
                end_of_last_read = var.address
            pointer += var.address - end_of_last_read
            result[var.name] = coils[pointer : pointer + size]
            end_of_last_read = var.end
        return result
