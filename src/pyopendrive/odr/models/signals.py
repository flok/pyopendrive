"""Immutable signal source values from OpenDRIVE 1.9 sections 14.1 to 14.5."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LaneValidity:
    from_lane: int
    to_lane: int
    layer: str | None = None


@dataclass(frozen=True, slots=True)
class SignalDependency:
    id: str
    type: str | None = None


@dataclass(frozen=True, slots=True)
class SignalLink:
    element_id: str
    element_type: str
    type: str | None = None


@dataclass(frozen=True, slots=True)
class SignalReference:
    id: str
    s: float
    t: float
    orientation: str
    validity: tuple[LaneValidity, ...] = ()


@dataclass(frozen=True, slots=True)
class Signal:
    id: str
    s: float
    t: float
    z_offset: float
    dynamic: bool
    orientation: str
    type: str
    subtype: str
    name: str | None = None
    country: str | None = None
    country_revision: str | None = None
    value: float | None = None
    unit: str | None = None
    height: float | None = None
    width: float | None = None
    length: float | None = None
    h_offset: float | None = None
    pitch: float | None = None
    roll: float | None = None
    text: str | None = None
    temporary: bool | None = None
    invalidated: bool | None = None
    validity: tuple[LaneValidity, ...] = ()
    dependencies: tuple[SignalDependency, ...] = ()
    references: tuple[SignalLink, ...] = ()
