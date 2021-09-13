from __future__ import annotations


class InvalidAddressLayoutError(Exception):
    def __init__(self, msg: str, previous: Variable, current: Variable) -> None:
        super().__init__(msg)
        self._last = last
        self._current = ...
        # TODO Check Arjan codes: Should this even have a custom message?
        "Invalid address layout: Previous variable {self._previous} stored on [{self._previous.address}, {self._previous.end}), next variable stored on [{self._next.address}, {self._previous.end}). Variables must have seperate stores in memory."


class VariableNotFoundError(Exception):
    def __init__(self, variables: Iterable[str], msg: Optional[str] = None) -> None:
        if msg is None:
            msg = f"Variables not found: {variables}"
        super().__init__(msg)
        self.variables = variables


class DuplicateVariableError(Exception):
    pass
