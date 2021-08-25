from __future__ import annotations

import scipy.interpolate


class AffineMap:
    def __init__(self, slope: float, offset: float) -> None:
        self._slope = slope
        self._offset = offset

    def __call__(self, value: float) -> float:
        return self._slope * value + self._offset

    @classmethod
    def affine_range_transform(
        cls, domain: RangeInfo, destination: RangeInfo
    ) -> AffineMap:
        slope = (destination.max - destination.min) / (domain.max - domain.min)
        offset = destination.min - domain.min
        return AffineMap(slope, offset)

    @classmethod
    def linear_range_transform(
        cls, domain: RangeInfo, destination: RangeInfo
    ) -> AffineMap:
        return AffineMap(
            (destination.max - destination.min) / (domain.max - domain.min), 0
        )


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
    def affine_range_transform(
        cls, domain: pylab.core.infos.RangeInfo, codomain: pylab.core.infos.RangeInfo
    ) -> LookupTable:
        return LookupTable([domain.min, domain.max], [codomain.min, codomain.max])

    @classmethod
    def linear_range_transform(
        cls, domain: pylab.core.infos.RangeInfo, codomain: pylab.core.infos.RangeInfo
    ) -> LookupTable:

        return LookupTable(
            [0, domain.max - domain.min], [0, codomain.max - codomain.min]
        )

    def __call__(self, t: float) -> float:
        return self._f(t)

    def inverted(self) -> LookupTable:
        return LookupTable(self._y, self._x)
