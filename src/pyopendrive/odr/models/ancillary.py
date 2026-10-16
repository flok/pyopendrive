"""Source values for OpenDRIVE extension and data-quality elements."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UserData:
    path: str
    code: str | None
    value: str | None = None


@dataclass(frozen=True, slots=True)
class DataQualityError:
    xy_absolute: str | None = None
    xy_relative: str | None = None
    z_absolute: str | None = None
    z_relative: str | None = None


@dataclass(frozen=True, slots=True)
class RawData:
    date: str | None = None
    post_processing: str | None = None
    post_processing_comment: str | None = None
    source: str | None = None
    source_comment: str | None = None


@dataclass(frozen=True, slots=True)
class DataQuality:
    path: str
    error: DataQualityError | None = None
    raw_data: RawData | None = None
