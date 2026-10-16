"""Road metadata models parsed from OpenDRIVE documents."""

from dataclasses import dataclass

from pyopendrive.odr.models.geometry import GeometrySegment
from pyopendrive.odr.models.lanes import LaneLayer
from pyopendrive.odr.models.objects import ObjectReference, RoadObject
from pyopendrive.odr.models.profiles import RoadProfiles
from pyopendrive.odr.models.railroads import RailroadSwitch
from pyopendrive.odr.models.signals import Signal, SignalReference


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
class RoadCrg:
    file: str
    mode: str
    orientation: str
    s_start: float
    s_end: float
    purpose: str | None = None
    h_offset: float | None = None
    s_offset: float | None = None
    t_offset: float | None = None
    x_offset: float | None = None
    y_offset: float | None = None
    z_offset: float | None = None
    z_scale: float | None = None


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
    profiles: RoadProfiles = RoadProfiles()
    lane_layers: tuple[LaneLayer, ...] = ()
    signals: tuple[Signal, ...] = ()
    signal_references: tuple[SignalReference, ...] = ()
    objects: tuple[RoadObject, ...] = ()
    object_references: tuple[ObjectReference, ...] = ()
    crgs: tuple[RoadCrg, ...] = ()
    switches: tuple[RailroadSwitch, ...] = ()
