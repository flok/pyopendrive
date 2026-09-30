"""Data models for road elevation and lateral profiles."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PolynomialProfile:
    """Cubic polynomial record anchored at a road reference-line position."""

    s: float
    a: float
    b: float
    c: float
    d: float
    level: bool | None = None


@dataclass(frozen=True, slots=True)
class Crossfall:
    """Crossfall record, applied to the specified side(s) of the road."""

    s: float
    a: float
    b: float
    c: float
    d: float
    side: str
    level: bool | None = None


@dataclass(frozen=True, slots=True)
class Shape:
    """Cubic lateral shape record anchored at an (s, t) position."""

    s: float
    t: float
    a: float
    b: float
    c: float
    d: float


@dataclass(frozen=True, slots=True)
class SurfaceCoefficients:
    """Cubic coefficients in s-direction for a cross-section surface."""

    s: float
    a: float | None = None
    b: float | None = None
    c: float | None = None
    d: float | None = None


@dataclass(frozen=True, slots=True)
class SurfaceStrip:
    """One polynomial strip in a cross-section surface."""

    id: int
    mode: str | None = None
    width: tuple[SurfaceCoefficients, ...] | None = None
    constant: tuple[SurfaceCoefficients, ...] | None = None
    linear: tuple[SurfaceCoefficients, ...] | None = None
    quadratic: tuple[SurfaceCoefficients, ...] | None = None
    cubic: tuple[SurfaceCoefficients, ...] | None = None


@dataclass(frozen=True, slots=True)
class CrossSectionSurface:
    """Road-wide cross-section surface record introduced in OpenDRIVE 1.8."""

    t_offset: tuple[SurfaceCoefficients, ...] | None
    strips: tuple[SurfaceStrip, ...]


@dataclass(frozen=True, slots=True)
class RoadProfiles:
    """Optional road profile groups; None means the XML group was absent."""

    elevation: tuple[PolynomialProfile, ...] | None = None
    superelevation: tuple[PolynomialProfile, ...] | None = None
    crossfall: tuple[Crossfall, ...] | None = None
    lane_offset: tuple[PolynomialProfile, ...] | None = None
    shape: tuple[Shape, ...] | None = None
    cross_section_surface: CrossSectionSurface | None = None
