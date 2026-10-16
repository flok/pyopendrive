"""Static railway station and platform records."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RailroadTrack:
    id: str
    s: float
    direction: str


@dataclass(frozen=True, slots=True)
class SwitchPartner:
    id: str
    name: str | None = None


@dataclass(frozen=True, slots=True)
class RailroadSwitch:
    id: str
    name: str
    position: str
    main_track: RailroadTrack
    side_track: RailroadTrack
    partner: SwitchPartner | None = None


@dataclass(frozen=True, slots=True)
class PlatformSegment:
    road_id: str
    s_start: float
    s_end: float
    side: str


@dataclass(frozen=True, slots=True)
class Platform:
    id: str
    name: str | None = None
    segments: tuple[PlatformSegment, ...] = ()


@dataclass(frozen=True, slots=True)
class Station:
    id: str
    name: str
    type: str | None = None
    platforms: tuple[Platform, ...] = ()
