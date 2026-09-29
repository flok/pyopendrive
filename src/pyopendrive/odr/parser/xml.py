"""Internal XML-to-model conversion."""

from pathlib import Path
from typing import IO
from xml.etree import ElementTree

from pyopendrive.odr.models import Header, OpenDriveMap, OpenDriveVersion, Road

type XmlSource = str | Path | IO[bytes] | IO[str]


class OpenDriveParseError(ValueError):
    """Raised when an XML document cannot be read as an OpenDRIVE file."""


def parse(source: XmlSource) -> OpenDriveMap:
    try:
        root = ElementTree.parse(source).getroot()
    except ElementTree.ParseError as error:
        raise OpenDriveParseError(f"Invalid XML: {error}") from error

    if _local_name(root.tag) != "OpenDRIVE":
        raise OpenDriveParseError("Root element must be 'OpenDRIVE'.")

    header_element = next(
        (element for element in root if _local_name(element.tag) == "header"),
        None,
    )
    if header_element is None:
        raise OpenDriveParseError("OpenDRIVE document is missing its header.")

    format_version = OpenDriveVersion(
        major=_required_int(header_element, "revMajor"),
        minor=_required_int(header_element, "revMinor"),
    )
    header = Header(
        name=header_element.get("name"),
        version=header_element.get("version"),
        date=header_element.get("date"),
        vendor=header_element.get("vendor"),
    )
    roads = tuple(
        _parse_road(element) for element in root if _local_name(element.tag) == "road"
    )
    return OpenDriveMap(format_version=format_version, header=header, roads=roads)


def _parse_road(element: ElementTree.Element) -> Road:
    try:
        road_id = element.attrib["id"]
        length = float(element.attrib["length"])
        junction = element.attrib["junction"]
    except (KeyError, ValueError) as error:
        raise OpenDriveParseError(
            f"Road has a missing or invalid attribute: {error}"
        ) from error

    return Road(
        id=road_id,
        length=length,
        junction=junction,
        name=element.get("name"),
    )


def _required_int(element: ElementTree.Element, attribute: str) -> int:
    try:
        return int(element.attrib[attribute])
    except (KeyError, ValueError) as error:
        raise OpenDriveParseError(
            f"Header has a missing or invalid '{attribute}' attribute."
        ) from error


def _local_name(tag: str) -> str:
    return tag.rsplit("}", maxsplit=1)[-1]
