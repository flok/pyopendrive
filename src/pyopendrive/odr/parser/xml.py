"""Internal XML-to-model conversion."""

from pathlib import Path
from typing import IO
from xml.etree import ElementTree

from pyopendrive.odr.models import (
    Header,
    OpenDriveDiagnostic,
    OpenDriveMap,
    OpenDriveVersion,
    Road,
)

type XmlSource = str | Path | IO[bytes] | IO[str]


class OpenDriveParseError(ValueError):
    """Raised when an XML document cannot be read as an OpenDRIVE file."""

    def __init__(self, message: str, *, element: str | None = None) -> None:
        self.message = message
        self.element = element
        context = f" ({element})" if element else ""
        super().__init__(f"{message}{context}")


def parse(source: XmlSource) -> OpenDriveMap:
    try:
        root = ElementTree.parse(source).getroot()
    except ElementTree.ParseError as error:
        raise OpenDriveParseError(f"Invalid XML: {error}") from error

    if _local_name(root.tag) != "OpenDRIVE":
        raise OpenDriveParseError(
            "Root element must be 'OpenDRIVE'.", element=f"/{_local_name(root.tag)}"
        )

    header_element = next(
        (element for element in root if _local_name(element.tag) == "header"),
        None,
    )
    if header_element is None:
        raise OpenDriveParseError(
            "OpenDRIVE document is missing its header.", element="/OpenDRIVE"
        )

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
    road_elements = [element for element in root if _local_name(element.tag) == "road"]
    roads = tuple(_parse_road(element) for element in road_elements)
    diagnostics = _collect_diagnostics(root, header_element, road_elements)
    return OpenDriveMap(
        format_version=format_version,
        header=header,
        roads=roads,
        diagnostics=diagnostics,
    )


def _parse_road(element: ElementTree.Element) -> Road:
    try:
        road_id = element.attrib["id"]
        length = float(element.attrib["length"])
        junction = element.attrib["junction"]
    except (KeyError, ValueError) as error:
        road_id = element.get("id", "?")
        raise OpenDriveParseError(
            f"Road has a missing or invalid attribute: {error}",
            element=f"/OpenDRIVE/road[@id='{road_id}']",
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
            f"Header has a missing or invalid '{attribute}' attribute.",
            element="/OpenDRIVE/header",
        ) from error


def _collect_diagnostics(
    root: ElementTree.Element,
    header: ElementTree.Element,
    roads: list[ElementTree.Element],
) -> tuple[OpenDriveDiagnostic, ...]:
    diagnostics: list[OpenDriveDiagnostic] = []
    _unsupported_attributes(root, set(), "/OpenDRIVE", diagnostics)
    _unsupported_attributes(
        header,
        {"revMajor", "revMinor", "name", "version", "date", "vendor"},
        "/OpenDRIVE/header",
        diagnostics,
    )
    _unsupported_children(header, "/OpenDRIVE/header", diagnostics)

    for road in roads:
        path = f"/OpenDRIVE/road[@id='{road.get('id', '?')}']"
        _unsupported_attributes(
            road, {"id", "length", "junction", "name"}, path, diagnostics
        )
        _unsupported_children(road, path, diagnostics)

    for child in root:
        name = _local_name(child.tag)
        if name not in {"header", "road"}:
            _unsupported_element(child, f"/OpenDRIVE/{name}", diagnostics)
    return tuple(diagnostics)


def _unsupported_attributes(
    element: ElementTree.Element,
    supported: set[str],
    path: str,
    diagnostics: list[OpenDriveDiagnostic],
) -> None:
    for attribute in element.attrib:
        name = _local_name(attribute)
        if name not in supported:
            diagnostics.append(
                OpenDriveDiagnostic(
                    code="unsupported-attribute",
                    message=f"Attribute '{name}' is not currently parsed.",
                    element=path,
                )
            )


def _unsupported_children(
    element: ElementTree.Element,
    path: str,
    diagnostics: list[OpenDriveDiagnostic],
) -> None:
    for child in element:
        name = _local_name(child.tag)
        _unsupported_element(child, f"{path}/{name}", diagnostics)


def _unsupported_element(
    element: ElementTree.Element,
    path: str,
    diagnostics: list[OpenDriveDiagnostic],
) -> None:
    diagnostics.append(
        OpenDriveDiagnostic(
            code="unsupported-element",
            message=f"Element '{_local_name(element.tag)}' is not currently parsed.",
            element=path,
        )
    )


def _local_name(tag: str) -> str:
    return tag.rsplit("}", maxsplit=1)[-1]
