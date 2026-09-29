from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import IO

type OpenDriveSource = str | Path | IO[bytes] | IO[str]


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

    @classmethod
    def load(cls, source: OpenDriveSource) -> OpenDriveMap:
        """Load an OpenDRIVE XML file from a path or open text/binary stream."""
        from pyopendrive.odr.parser.xml import parse

        return parse(source)
