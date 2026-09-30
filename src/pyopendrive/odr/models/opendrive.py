from __future__ import annotations

from dataclasses import dataclass
from os import PathLike
from typing import IO

type OpenDriveSource = str | PathLike[str] | IO[bytes] | IO[str]


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
    north: float | None = None
    south: float | None = None
    east: float | None = None
    west: float | None = None
    geo_reference: str | None = None
    offset: Offset | None = None
    license: License | None = None
    default_regulations: DefaultRegulations | None = None


@dataclass(frozen=True, slots=True)
class Offset:
    x: float
    y: float
    z: float
    hdg: float


@dataclass(frozen=True, slots=True)
class License:
    name: str
    resource: str | None = None
    spdxid: str | None = None
    text: str | None = None


@dataclass(frozen=True, slots=True)
class RegulationSemantic:
    name: str
    attributes: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class RoadRegulation:
    type: str
    semantics: tuple[RegulationSemantic, ...]


@dataclass(frozen=True, slots=True)
class SignalRegulation:
    type: str
    subtype: str
    semantics: tuple[RegulationSemantic, ...]


@dataclass(frozen=True, slots=True)
class DefaultRegulations:
    road: tuple[RoadRegulation, ...] = ()
    signals: tuple[SignalRegulation, ...] = ()


@dataclass(frozen=True, slots=True)
class Road:
    id: str
    length: float
    junction: str
    name: str | None = None


@dataclass(frozen=True, slots=True)
class OpenDriveDiagnostic:
    """A recoverable parser observation tied to an XML element."""

    code: str
    message: str
    element: str


@dataclass(frozen=True, slots=True)
class OpenDriveMap:
    """Parsed OpenDRIVE map with its format version, header, and roads."""

    format_version: OpenDriveVersion
    header: Header
    roads: tuple[Road, ...]
    diagnostics: tuple[OpenDriveDiagnostic, ...] = ()

    @staticmethod
    def load(source: OpenDriveSource) -> OpenDriveMap:
        """Load a map from a filesystem path or caller-owned XML stream."""
        from pyopendrive.odr.parser.xml import parse

        return parse(source)
