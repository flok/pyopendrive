"""Plan-view reference-line geometry values."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Line:
    """Straight reference-line segment."""


@dataclass(frozen=True, slots=True)
class Arc:
    curvature: float


@dataclass(frozen=True, slots=True)
class Spiral:
    curvature_start: float
    curvature_end: float


@dataclass(frozen=True, slots=True)
class Poly3:
    a: float
    b: float
    c: float
    d: float


@dataclass(frozen=True, slots=True)
class ParamPoly3:
    a_u: float
    b_u: float
    c_u: float
    d_u: float
    a_v: float
    b_v: float
    c_v: float
    d_v: float
    p_range: str


type GeometryPrimitive = Line | Arc | Spiral | Poly3 | ParamPoly3


@dataclass(frozen=True, slots=True)
class GeometrySegment:
    """One ordered plan-view segment and its unmodified source parameters."""

    s: float
    x: float
    y: float
    heading: float
    length: float
    primitive: GeometryPrimitive
