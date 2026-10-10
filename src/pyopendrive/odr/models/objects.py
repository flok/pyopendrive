"""Immutable object source values from OpenDRIVE 1.9 chapter 13."""

from dataclasses import dataclass

from pyopendrive.odr.models.geometry import Arc, Line, ParamPoly3
from pyopendrive.odr.models.signals import LaneValidity


@dataclass(frozen=True, slots=True)
class CornerRoad:
    s: float
    t: float
    dz: float
    height: float
    id: int | None = None


@dataclass(frozen=True, slots=True)
class CornerLocal:
    u: float
    v: float
    z: float
    height: float
    id: int | None = None


@dataclass(frozen=True, slots=True)
class CurveLocal:
    u: float
    v: float
    z: float
    height: float
    primitive: Line | Arc | ParamPoly3
    id: int | None = None
    heading: float | None = None
    length: float | None = None


@dataclass(frozen=True, slots=True)
class ObjectMarking:
    color: str
    line_length: float
    space_length: float
    start_offset: float
    stop_offset: float
    side: str | None = None
    weight: str | None = None
    width: float | None = None
    z_offset: float | None = None
    corner_references: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class ObjectOutline:
    corners: tuple[CornerRoad | CornerLocal | CurveLocal, ...] = ()
    id: int | None = None
    closed: bool | None = None
    outer: bool | None = None
    fill_type: str | None = None
    lane_type: str | None = None
    markings: tuple[ObjectMarking, ...] = ()


@dataclass(frozen=True, slots=True)
class ObjectReference:
    id: str
    s: float
    t: float
    orientation: str
    z_offset: float | None = None
    valid_length: float | None = None
    validity: tuple[LaneValidity, ...] = ()


@dataclass(frozen=True, slots=True)
class RoadObject:
    id: str
    s: float
    t: float
    z_offset: float
    name: str | None = None
    type: str | None = None
    subtype: str | None = None
    orientation: str | None = None
    dynamic: bool | None = None
    heading: float | None = None
    pitch: float | None = None
    roll: float | None = None
    height: float | None = None
    length: float | None = None
    width: float | None = None
    radius: float | None = None
    valid_length: float | None = None
    perpendicular_to_road: bool | None = None
    temporary: bool | None = None
    invalidated: bool | None = None
    validity: tuple[LaneValidity, ...] = ()
    outlines: tuple[ObjectOutline, ...] = ()
    markings: tuple[ObjectMarking, ...] = ()
