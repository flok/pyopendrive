"""Convert junction topology and static signal controller mappings.

Common junction attributes follow ASAM OpenDRIVE 1.9.0 section 12.2:
https://publications.pages.asam.net/standards/ASAM_OpenDRIVE/ASAM_OpenDRIVE_Specification/v1.9.0/specification/12_junctions/12_02_common_junctions.html
Other records were checked against the 1.8.1 specification sections 12.4,
12.6, 12.7, 12.8, 12.13, 12.14 and 14.6. Their complete 1.9.0 revision
changes remain unverified. Parsing does not perform schema or topology validation.
"""

import math
from xml.etree import ElementTree

from pyopendrive.odr.models.junctions import (
    Controller,
    ControllerControl,
    Junction,
    JunctionConnection,
    JunctionConnectionLink,
    JunctionController,
    JunctionGroup,
    JunctionLaneLink,
    JunctionPriority,
    JunctionReference,
    JunctionRoadSection,
)


class JunctionParseError(ValueError):
    def __init__(self, message: str, *, element: str) -> None:
        self.message = message
        self.element = element
        super().__init__(f"{message} ({element})")


def parse_junction(element: ElementTree.Element) -> Junction:
    path = f"/OpenDRIVE/junction[@id='{element.get('id', '?')}']"
    return Junction(
        id=_required(element, "id", path),
        name=element.get("name"),
        type=element.get("type"),
        main_road=element.get("mainRoad"),
        orientation=element.get("orientation"),
        s_start=_optional_float(element, "sStart", path),
        s_end=_optional_float(element, "sEnd", path),
        connections=tuple(
            _connection(child, path) for child in _children(element, "connection")
        ),
        priorities=tuple(
            JunctionPriority(
                high=_required(child, "high", f"{path}/priority"),
                low=_required(child, "low", f"{path}/priority"),
            )
            for child in _children(element, "priority")
        ),
        controllers=tuple(
            JunctionController(
                id=_required(child, "id", f"{path}/controller"),
                type=child.get("type"),
                sequence=_optional_int(child, "sequence", f"{path}/controller"),
            )
            for child in _children(element, "controller")
        ),
        road_sections=tuple(
            JunctionRoadSection(
                id=_required(child, "id", f"{path}/roadSection"),
                road_id=_required(child, "roadId", f"{path}/roadSection"),
                s_start=_float(child, "sStart", f"{path}/roadSection"),
                s_end=_float(child, "sEnd", f"{path}/roadSection"),
            )
            for child in _children(element, "roadSection")
        ),
    )


def _connection(element: ElementTree.Element, parent_path: str) -> JunctionConnection:
    path = f"{parent_path}/connection[@id='{element.get('id', '?')}']"
    return JunctionConnection(
        id=_required(element, "id", path),
        incoming_road=element.get("incomingRoad"),
        connecting_road=element.get("connectingRoad"),
        linked_road=element.get("linkedRoad"),
        contact_point=element.get("contactPoint"),
        type=element.get("type"),
        lane_links=tuple(
            JunctionLaneLink(
                from_lane=_int(child, "from", f"{path}/laneLink"),
                to_lane=_int(child, "to", f"{path}/laneLink"),
                overlap_zone=_optional_float(child, "overlapZone", f"{path}/laneLink"),
            )
            for child in _children(element, "laneLink")
        ),
        predecessor=_connection_link(element, "predecessor", path),
        successor=_connection_link(element, "successor", path),
    )


def _connection_link(
    parent: ElementTree.Element, name: str, parent_path: str
) -> JunctionConnectionLink | None:
    element = next(iter(_children(parent, name)), None)
    if element is None:
        return None
    path = f"{parent_path}/{name}"
    return JunctionConnectionLink(
        element_type=_required(element, "elementType", path),
        element_id=_required(element, "elementId", path),
        element_s=_optional_float(element, "elementS", path),
        element_dir=element.get("elementDir"),
        contact_point=element.get("contactPoint"),
    )


def parse_junction_group(element: ElementTree.Element) -> JunctionGroup:
    path = f"/OpenDRIVE/junctionGroup[@id='{element.get('id', '?')}']"
    return JunctionGroup(
        id=_required(element, "id", path),
        type=_required(element, "type", path),
        name=element.get("name"),
        junction_references=tuple(
            JunctionReference(
                junction=_required(child, "junction", f"{path}/junctionReference")
            )
            for child in _children(element, "junctionReference")
        ),
    )


def parse_controller(element: ElementTree.Element) -> Controller:
    path = f"/OpenDRIVE/controller[@id='{element.get('id', '?')}']"
    return Controller(
        id=_required(element, "id", path),
        name=element.get("name"),
        sequence=_optional_int(element, "sequence", path),
        controls=tuple(
            ControllerControl(
                signal_id=_required(child, "signalId", f"{path}/control"),
                type=child.get("type"),
            )
            for child in _children(element, "control")
        ),
    )


def _children(element: ElementTree.Element, name: str) -> list[ElementTree.Element]:
    return [child for child in element if child.tag.rsplit("}", 1)[-1] == name]


def _required(element: ElementTree.Element, attribute: str, path: str) -> str:
    value = element.get(attribute)
    if value is None:
        raise JunctionParseError(
            f"Missing required '{attribute}' attribute.", element=path
        )
    return value


def _int(element: ElementTree.Element, attribute: str, path: str) -> int:
    value = _required(element, attribute, path)
    try:
        return int(value)
    except ValueError as error:
        raise JunctionParseError(
            f"Invalid integer '{attribute}' attribute: {value!r}.", element=path
        ) from error


def _optional_int(
    element: ElementTree.Element, attribute: str, path: str
) -> int | None:
    return _int(element, attribute, path) if attribute in element.attrib else None


def _float(element: ElementTree.Element, attribute: str, path: str) -> float:
    value = _required(element, attribute, path)
    try:
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("value must be finite")
        return result
    except ValueError as error:
        raise JunctionParseError(
            f"Invalid numeric '{attribute}' attribute: {value!r}.", element=path
        ) from error


def _optional_float(
    element: ElementTree.Element, attribute: str, path: str
) -> float | None:
    return _float(element, attribute, path) if attribute in element.attrib else None
