"""Immutable models for OpenDRIVE lane layers and lane properties."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LanePolynomial:
    s_offset: float
    a: float
    b: float
    c: float
    d: float


@dataclass(frozen=True, slots=True)
class LaneLink:
    id: int
    layer: str | None = None


@dataclass(frozen=True, slots=True)
class LaneLinks:
    predecessors: tuple[LaneLink, ...] = ()
    successors: tuple[LaneLink, ...] = ()


@dataclass(frozen=True, slots=True)
class LaneRoadMarkLine:
    s_offset: float
    length: float | None = None
    space: float | None = None
    t_offset: float | None = None
    rule: str | None = None
    width: float | None = None


@dataclass(frozen=True, slots=True)
class LaneRoadMarkType:
    name: str
    width: float
    lines: tuple[LaneRoadMarkLine, ...] = ()


@dataclass(frozen=True, slots=True)
class LaneRoadMark:
    s_offset: float
    mark_type: str | None = None
    material: str | None = None
    weight: str | None = None
    color: str | None = None
    width: float | None = None
    lane_change: str | None = None
    height: float | None = None
    type_definition: LaneRoadMarkType | None = None


@dataclass(frozen=True, slots=True)
class LaneMaterial:
    s_offset: float
    surface: str | None = None
    friction: float | None = None
    roughness: float | None = None


@dataclass(frozen=True, slots=True)
class LaneSpeed:
    s_offset: float
    max: float | None = None
    unit: str | None = None


@dataclass(frozen=True, slots=True)
class LaneAccess:
    s_offset: float
    restriction: str | None = None
    rule: str | None = None


@dataclass(frozen=True, slots=True)
class LaneHeight:
    s_offset: float
    inner: float | None = None
    outer: float | None = None


@dataclass(frozen=True, slots=True)
class LaneRule:
    s_offset: float
    value: str


@dataclass(frozen=True, slots=True)
class Lane:
    id: int
    lane_type: str | None = None
    level: bool | None = None
    road_works: bool | None = None
    advisory: str | None = None
    direction: str | None = None
    dynamic_lane_direction: bool | None = None
    dynamic_lane_type: bool | None = None
    links: LaneLinks = LaneLinks()
    widths: tuple[LanePolynomial, ...] = ()
    borders: tuple[LanePolynomial, ...] = ()
    road_marks: tuple[LaneRoadMark, ...] = ()
    materials: tuple[LaneMaterial, ...] = ()
    speeds: tuple[LaneSpeed, ...] = ()
    access: tuple[LaneAccess, ...] = ()
    heights: tuple[LaneHeight, ...] = ()
    rules: tuple[LaneRule, ...] = ()


@dataclass(frozen=True, slots=True)
class LaneGroups:
    left: tuple[Lane, ...] | None = None
    center: tuple[Lane, ...] = ()
    right: tuple[Lane, ...] | None = None
    order: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class LaneSection:
    s: float
    length: float | None = None
    single_side: bool | None = None
    lanes: LaneGroups = LaneGroups()


@dataclass(frozen=True, slots=True)
class LaneLayer:
    layer: str | None
    sections: tuple[LaneSection, ...]
