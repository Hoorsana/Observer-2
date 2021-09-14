# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import collections
import dataclasses
import itertools
from typing import Union, List

from pylab.live.plugin.modbus.exceptions import (
    InvalidAddressLayoutError,
    VariableNotFoundError,
    DuplicateVariableError,
)

_ValueType = Union[List[bool], bool]


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

    def succeeds(self, other: Variable) -> bool:
        """Check if the variable's store succeeds that of ``other``."""
        return self.address == other.end

    def align_with(self, other: Variable) -> None:
        """Set the address of ``self`` so that it succeeds ``other``."""
        self.address = other.end


@dataclasses.dataclass
class Chunk:
    address: int
    values: _ValueType


class CoilLayout:
    def __init__(self, variables: list[Variable]) -> None:
        """Decode and encode boolean payloads according to a specified
        layout.

        Args:
            variables: The variables stored in the layout

        Raises:
            DuplicateVariableError: If two variables have the same name
            InvalidAddressLayoutError: If two variable stores overlap

        ``variables`` must be non-empty and specified in the order in
        which they are stored in memory. If ``variables[0].address`` is
        ``None``, it is assumed to be ``0``. If some other variable's
        address is ``None``, it is aligned with the previous variable,
        i.e. its address is set equal to the end of the previous variable.
        """
        self._variables = variables

        # Raise on duplicate!
        names = [v.name for v in self._variables]
        duplicates = [value for value, count in collections.Counter(names).items() if count > 1]
        if duplicates:
            raise DuplicateVariableError(duplicates[0])

        assert variables  # TODO pydantic validation
        if variables[0].address is None:
            variables[0].address = 0
        for current, last in zip(self._variables[1:], self._variables):
            if current.address is None:
                current.align_with(last)
            elif current.address < last.end:
                raise InvalidAddressLayoutError(current, last)

    @classmethod
    def from_dict(cls, data) -> cls:
        return CoilLayout([Variable(**v) for v in data])

    # FIXME This has a healthy amount of code duplication with the register layout's analogous
    # function. Maybe use an abstraction for chunking the memory?
    def build_payload(self, values: dict[str, _ValueType]) -> list[Chunk]:
        """Build data for writing new values to memory.

        Args:
            values: A dict mapping variable names to their new value

        Returns:
            A list of ``Chunk`` objects, one for each block of bytes to
            be written to memory

        Raises:
            VariableNotFoundError:
                If ``values`` contains a key that does not match any
                variable of the layout

        ``values.keys()`` must be a subset of the layout's variable
        names. If not all variables are present, only the provided
        subset is written.

        The method collects the values into ``Chunk`` objects, each of
        which contains a block of bits. The chunks are made as large as
        possible without becoming disconnected. Note that a highly
        fragmented ``values`` parameter will result in more items in the
        list, and, thus, a larger amount of IO operations.
        """
        result = []
        address = self._variables[0].address
        bits = []

        def build_chunk():
            nonlocal bits
            result.append(Chunk(address, bits))
            bits = []

        seen = set()
        for var, next_ in itertools.zip_longest(
            self._variables, self._variables[1:], fillvalue=None
        ):
            value = values.get(var.name, None)
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
            elif not next_.succeeds(var):
                build_chunk()
                address = next_.address
            seen.add(var.name)

        if len(seen) < len(values):
            not_found = set(values.keys()) - seen
            raise VariableNotFoundError(not_found)
        return result

    def decode_coils(
        self, coils: list[str], variables_to_decode: Optional[Iterable[str]] = None
    ) -> dict[str, _ValueType]:
        """Decode coils into Python types.

        Args:
            coils: The coils to decode
            variables_to_decode:
                The names of the variables that occur in ``coils``

        Returns:
            A ``dict`` mapping variable names to their value

        Raises:
            VariableNotFound:
                If ``variables_to_decode`` contains an items which does
                not match any variable of the layout
        """
        if variables_to_decode is None:
            variables_to_decode = [x.name for x in self._variables]
        result = {}
        seen = set()
        for var in self._variables:
            if var.name not in variables_to_decode:
                continue
            value = coils[var.address : var.end]
            # Unpack single bit sequence!
            if len(value) == 1:
                value = value[0]
            result[var.name] = value
            seen.add(var.name)

        if len(seen) < len(variables_to_decode):
            not_found = set(variables_to_decode) - seen
            raise VariableNotFoundError(not_found)
        return result

    @property
    def size(self) -> int:
        """Return the total size of the layout in bits."""
        return self._variables[-1].end - self._variables[0].address

    @property
    def address(self) -> int:
        """Return the starting address of the layout."""
        return self._variables[0].address
