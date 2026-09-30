"""Road metadata models parsed from OpenDRIVE documents."""

from dataclasses import dataclass

from pyopendrive.odr.models.geometry import GeometrySegment


@dataclass(frozen=True, slots=True)
class RoadSpeed:
    value: float | str
    unit: str | None = None


@dataclass(frozen=True, slots=True)
class RoadType:
    s: float
    type: str
    country: str | None = None
    source: str | None = None
    speed: RoadSpeed | None = None


@dataclass(frozen=True, slots=True)
class RoadLink:
    element_type: str
    element_id: str
    contact_point: str | None = None
    element_s: float | None = None
    element_dir: str | None = None


@dataclass(frozen=True, slots=True)
class Road:
    id: str
    length: float
    junction: str
    name: str | None = None
    rule: str | None = None
    predecessor: RoadLink | None = None
    successor: RoadLink | None = None
    types: tuple[RoadType, ...] = ()
    plan_view: tuple[GeometrySegment, ...] = ()
