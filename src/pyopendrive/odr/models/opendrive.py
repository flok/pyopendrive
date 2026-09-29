from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OpenDriveVersion:
    major: int
    minor: int


@dataclass(frozen=True, slots=True)
class Header:
    name: str | None = None
    version: str | None = None
    date: str | None = None
    vendor: str | None = None


@dataclass(frozen=True, slots=True)
class Road:
    id: str
    length: float
    junction: str
    name: str | None = None


@dataclass(frozen=True, slots=True)
class OpenDriveMap:
    """Parsed OpenDRIVE map with its format version, header, and roads."""

    format_version: OpenDriveVersion
    header: Header
    roads: tuple[Road, ...]
