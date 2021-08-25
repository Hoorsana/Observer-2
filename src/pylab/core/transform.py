from __future__ import annotations

import scipy.interpolate


class LookupTable:
    def __init__(self, x: list[float], y: list[float]) -> None:
        self._x = x
        self._y = y
        self._f = scipy.interpolate.interp1d(
            self._x,
            self._y,
            axis=0,
            copy=False,
            bounds_error=False,
            fill_value="extrapolate",
            kind="linear",
        )

    @classmethod
    def transform_ranges(
        cls, domain: pylab.core.infos.RangeInfo, codomain: pylab.core.infos.RangeInfo
    ) -> LookupTable:
        return LookupTable([domain.min, domain.max], [codomain.min, codomain.max])

    def __call__(self, t: float) -> float:
        return self._f(t)

    def inverted(self) -> LookupTable:
        return LookupTable(self._y, self._x)
