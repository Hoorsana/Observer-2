from __future__ import annotations


class InvalidAddressLayoutError(Exception):
    def __init__(
        self, previous: Variable, current: Variable, msg: Optional[str] = None
    ) -> None:
        if msg is None:
            msg = f"Invalid address for variable '{current.name}' specified: {current.address}. Previous variable store ends at {previous.end}. Variable stores must not overlap."
        super().__init__(msg)
        self.previous = previous
        self.current = current


class VariableNotFoundError(Exception):
    def __init__(self, variables: Iterable[str], msg: Optional[str] = None) -> None:
        if msg is None:
            msg = f"Variables not found: {variables}"
        super().__init__(msg)
        self.variables = variables


class DuplicateVariableError(Exception):
    def __init__(self, duplicate: str, msg: Optional[str] = None) -> None:
        if msg is None:
            msg = f"Duplicate variable name: {duplicate}"
        super().__init__(msg)
        self.duplicate = duplicate
