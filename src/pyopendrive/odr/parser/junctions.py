"""Convert junction topology and static signal controller mappings.

Common junction attributes follow ASAM OpenDRIVE 1.9.0 section 12.2:
https://publications.pages.asam.net/standards/ASAM_OpenDRIVE/ASAM_OpenDRIVE_Specification/v1.9.0/specification/12_junctions/12_02_common_junctions.html
Other records were checked against the 1.8.1 specification sections 12.4,
12.6, 12.7, 12.8, 12.13, 12.14 and 14.6. Their complete 1.9.0 revision
changes remain unverified. Parsing does not perform schema or topology validation.
"""

import math
from xml.etree import ElementTree

from pyopendrive.odr.models.geometry import GeometrySegment, Line
from pyopendrive.odr.models.junctions import (
    Controller,
    ControllerControl,
    Junction,
    JunctionBoundary,
    JunctionBoundaryJoint,
    JunctionBoundaryLane,
    JunctionConnection,
    JunctionConnectionLink,
    JunctionController,
    JunctionCrg,
    JunctionCrossPath,
    JunctionCrossPathLaneLink,
    JunctionElevationGrid,
    JunctionGridElevation,
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
        cross_paths=tuple(
            _cross_path(child, path) for child in _children(element, "crossPath")
        ),
        plan_view=_junction_plan_view(element, path),
        boundary=_boundary(element, path),
        elevation_grid=_elevation_grid(element, path),
        crgs=_crgs(element, path),
    )


def _cross_path(element: ElementTree.Element, parent_path: str) -> JunctionCrossPath:
    path = f"{parent_path}/crossPath[@id='{element.get('id', '?')}']"
    links = {}
    for name in ("startLaneLink", "endLaneLink"):
        matches = _children(element, name)
        if len(matches) != 1:
            raise JunctionParseError(
                f"Cross path requires exactly one '{name}' element.", element=path
            )
        child = matches[0]
        child_path = f"{path}/{name}"
        links[name] = JunctionCrossPathLaneLink(
            s=_float(child, "s", child_path),
            from_lane=_int(child, "from", child_path),
            to_lane=_int(child, "to", child_path),
        )
    return JunctionCrossPath(
        id=_required(element, "id", path),
        crossing_road=_required(element, "crossingRoad", path),
        road_at_start=_required(element, "roadAtStart", path),
        road_at_end=_required(element, "roadAtEnd", path),
        start_lane_link=links["startLaneLink"],
        end_lane_link=links["endLaneLink"],
    )


def _junction_plan_view(
    element: ElementTree.Element, path: str
) -> tuple[GeometrySegment, ...] | None:
    plans = _children(element, "planView")
    if len(plans) > 1:
        raise JunctionParseError("Junction allows at most one planView.", element=path)
    if not plans:
        return None
    plan = plans[0]
    geometries = _children(plan, "geometry")
    if len(geometries) != 1:
        raise JunctionParseError(
            "Junction reference line requires exactly one geometry.",
            element=f"{path}/planView",
        )
    geometry = geometries[0]
    geometry_path = f"{path}/planView/geometry"
    lines = _children(geometry, "line")
    if len(lines) != 1 or len(geometry) != 1:
        raise JunctionParseError(
            "Junction reference line geometry must contain one line primitive.",
            element=geometry_path,
        )
    return (
        GeometrySegment(
            s=_float(geometry, "s", geometry_path),
            x=_float(geometry, "x", geometry_path),
            y=_float(geometry, "y", geometry_path),
            heading=_float(geometry, "hdg", geometry_path),
            length=_float(geometry, "length", geometry_path),
            primitive=Line(),
        ),
    )


def _boundary(element: ElementTree.Element, path: str) -> JunctionBoundary | None:
    matches = _children(element, "boundary")
    if len(matches) > 1:
        raise JunctionParseError("Junction allows at most one boundary.", element=path)
    if not matches:
        return None
    result = []
    for segment in _children(matches[0], "segment"):
        segment_path = f"{path}/boundary/segment"
        kind = _required(segment, "type", segment_path)
        road_id = _required(segment, "roadId", segment_path)
        if kind == "lane":
            result.append(
                JunctionBoundaryLane(
                    road_id=road_id,
                    boundary_lane=_int(segment, "boundaryLane", segment_path),
                    s_start=_position(segment, "sStart", segment_path),
                    s_end=_position(segment, "sEnd", segment_path),
                )
            )
        elif kind == "joint":
            result.append(
                JunctionBoundaryJoint(
                    road_id=road_id,
                    contact_point=_contact_point(segment, segment_path),
                    joint_lane_start=_optional_int(
                        segment, "jointLaneStart", segment_path
                    ),
                    joint_lane_end=_optional_int(segment, "jointLaneEnd", segment_path),
                    transition_length=_optional_float(
                        segment, "transitionLength", segment_path
                    ),
                )
            )
        else:
            raise JunctionParseError(
                f"Unknown boundary segment type {kind!r}.", element=segment_path
            )
    if not result:
        raise JunctionParseError(
            "Boundary requires at least one segment.", element=f"{path}/boundary"
        )
    return JunctionBoundary(tuple(result))


def _position(element: ElementTree.Element, name: str, path: str) -> float | str:
    value = _required(element, name, path)
    if value in {"begin", "end", "start"}:
        return value
    try:
        result = float(value)
        if not math.isfinite(result):
            raise ValueError
        return result
    except ValueError as error:
        raise JunctionParseError(
            f"Invalid position {name!r}: {value!r}.", element=path
        ) from error


def _contact_point(element: ElementTree.Element, path: str) -> str:
    value = _required(element, "contactPoint", path)
    if value not in {"start", "end"}:
        raise JunctionParseError(
            f"Invalid contactPoint value: {value!r}.", element=path
        )
    return value


def _elevation_grid(
    element: ElementTree.Element, path: str
) -> JunctionElevationGrid | None:
    matches = _children(element, "elevationGrid")
    if len(matches) > 1:
        raise JunctionParseError(
            "Junction allows at most one elevationGrid.", element=path
        )
    if not matches:
        return None
    grid = matches[0]
    grid_path = f"{path}/elevationGrid"
    rows = []
    for row in _children(grid, "elevation"):
        row_path = f"{grid_path}/elevation"
        rows.append(
            JunctionGridElevation(
                center=_float_list(row, "center", row_path),
                left=_optional_float_list(row, "left", row_path),
                right=_optional_float_list(row, "right", row_path),
            )
        )
    return JunctionElevationGrid(
        s_start=_float(grid, "sStart", grid_path),
        grid_spacing=_float(grid, "gridSpacing", grid_path),
        elevations=tuple(rows),
    )


def _float_list(
    element: ElementTree.Element, name: str, path: str
) -> tuple[float, ...]:
    value = _required(element, name, path)
    try:
        values = tuple(float(part) for part in value.split())
        if not values or not all(math.isfinite(item) for item in values):
            raise ValueError
        return values
    except ValueError as error:
        raise JunctionParseError(
            f"Invalid numeric list {name!r}: {value!r}.", element=path
        ) from error


def _optional_float_list(
    element: ElementTree.Element, name: str, path: str
) -> tuple[float, ...] | None:
    return _float_list(element, name, path) if name in element.attrib else None


def _crgs(element: ElementTree.Element, path: str) -> tuple[JunctionCrg, ...]:
    surfaces = _children(element, "surface")
    if len(surfaces) > 1:
        raise JunctionParseError("Junction allows at most one surface.", element=path)
    result = []
    for crg in _children(surfaces[0], "CRG") if surfaces else ():
        crg_path = f"{path}/surface/CRG"
        result.append(
            JunctionCrg(
                file=_required(crg, "file", crg_path),
                mode=_required(crg, "mode", crg_path),
                orientation=_required(crg, "orientation", crg_path),
                s_start=_float(crg, "sStart", crg_path),
                s_end=_float(crg, "sEnd", crg_path),
                purpose=crg.get("purpose"),
                h_offset=_optional_float(crg, "hOffset", crg_path),
                s_offset=_optional_float(crg, "sOffset", crg_path),
                t_offset=_optional_float(crg, "tOffset", crg_path),
                z_offset=_optional_float(crg, "zOffset", crg_path),
                z_scale=_optional_float(crg, "zScale", crg_path),
            )
        )
    return tuple(result)


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
