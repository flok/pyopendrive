"""Immutable junction topology and signal controller records."""

from dataclasses import dataclass
from typing import Literal

from pyopendrive.odr.models.geometry import GeometrySegment

type JunctionBoundaryPosition = float | Literal["begin", "end", "start"]
type JunctionContactPoint = Literal["start", "end"]


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
class JunctionCrossPathLaneLink:
    s: float
    from_lane: int
    to_lane: int


@dataclass(frozen=True, slots=True)
class JunctionCrossPath:
    id: str
    crossing_road: str
    road_at_start: str
    road_at_end: str
    start_lane_link: JunctionCrossPathLaneLink
    end_lane_link: JunctionCrossPathLaneLink


@dataclass(frozen=True, slots=True)
class JunctionBoundaryLane:
    road_id: str
    boundary_lane: int
    s_start: JunctionBoundaryPosition
    s_end: JunctionBoundaryPosition


@dataclass(frozen=True, slots=True)
class JunctionBoundaryJoint:
    road_id: str
    contact_point: JunctionContactPoint
    joint_lane_start: int | None = None
    joint_lane_end: int | None = None
    transition_length: float | None = None


type JunctionBoundarySegment = JunctionBoundaryLane | JunctionBoundaryJoint


@dataclass(frozen=True, slots=True)
class JunctionBoundary:
    segments: tuple[JunctionBoundarySegment, ...]


@dataclass(frozen=True, slots=True)
class JunctionGridElevation:
    center: tuple[float, ...]
    left: tuple[float, ...] | None = None
    right: tuple[float, ...] | None = None


@dataclass(frozen=True, slots=True)
class JunctionElevationGrid:
    s_start: float
    grid_spacing: float
    elevations: tuple[JunctionGridElevation, ...]


@dataclass(frozen=True, slots=True)
class JunctionCrg:
    file: str
    mode: str
    orientation: str
    s_start: float
    s_end: float
    purpose: str | None = None
    h_offset: float | None = None
    s_offset: float | None = None
    t_offset: float | None = None
    z_offset: float | None = None
    z_scale: float | None = None


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
    cross_paths: tuple[JunctionCrossPath, ...] = ()
    plan_view: tuple[GeometrySegment, ...] | None = None
    boundary: JunctionBoundary | None = None
    elevation_grid: JunctionElevationGrid | None = None
    crgs: tuple[JunctionCrg, ...] = ()


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
