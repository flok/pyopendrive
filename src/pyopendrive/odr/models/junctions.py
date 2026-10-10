"""Immutable junction topology and signal controller records."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class JunctionLaneLink:
    from_lane: int
    to_lane: int
    overlap_zone: float | None = None


@dataclass(frozen=True, slots=True)
class JunctionConnectionLink:
    element_type: str
    element_id: str
    element_s: float | None = None
    element_dir: str | None = None
    contact_point: str | None = None


@dataclass(frozen=True, slots=True)
class JunctionConnection:
    id: str
    incoming_road: str | None = None
    connecting_road: str | None = None
    linked_road: str | None = None
    contact_point: str | None = None
    type: str | None = None
    lane_links: tuple[JunctionLaneLink, ...] = ()
    predecessor: JunctionConnectionLink | None = None
    successor: JunctionConnectionLink | None = None


@dataclass(frozen=True, slots=True)
class JunctionPriority:
    high: str
    low: str


@dataclass(frozen=True, slots=True)
class JunctionController:
    id: str
    type: str | None = None
    sequence: int | None = None


@dataclass(frozen=True, slots=True)
class JunctionRoadSection:
    id: str
    road_id: str
    s_start: float
    s_end: float


@dataclass(frozen=True, slots=True)
class Junction:
    id: str
    name: str | None = None
    type: str | None = None
    main_road: str | None = None
    orientation: str | None = None
    s_start: float | None = None
    s_end: float | None = None
    connections: tuple[JunctionConnection, ...] = ()
    priorities: tuple[JunctionPriority, ...] = ()
    controllers: tuple[JunctionController, ...] = ()
    road_sections: tuple[JunctionRoadSection, ...] = ()


@dataclass(frozen=True, slots=True)
class JunctionReference:
    junction: str


@dataclass(frozen=True, slots=True)
class JunctionGroup:
    id: str
    type: str
    name: str | None = None
    junction_references: tuple[JunctionReference, ...] = ()


@dataclass(frozen=True, slots=True)
class ControllerControl:
    signal_id: str
    type: str | None = None


@dataclass(frozen=True, slots=True)
class Controller:
    id: str
    name: str | None = None
    sequence: int | None = None
    controls: tuple[ControllerControl, ...] = ()
