"""Internal XML-to-model conversion."""

import math
from pathlib import Path
from typing import IO
from xml.etree import ElementTree

from pyopendrive.odr.models import (
    DefaultRegulations,
    Header,
    License,
    Offset,
    OpenDriveDiagnostic,
    OpenDriveMap,
    OpenDriveVersion,
    RegulationSemantic,
    Road,
    RoadLink,
    RoadRegulation,
    RoadSpeed,
    RoadType,
    SignalRegulation,
)
from pyopendrive.odr.models.geometry import GeometrySegment
from pyopendrive.odr.parser.lanes import LaneParseError, parse_lane_layers
from pyopendrive.odr.parser.profiles import ProfileParseError, parse_road_profiles

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
    header = _parse_header(header_element)
    road_elements = [element for element in root if _local_name(element.tag) == "road"]
    roads = tuple(
        _parse_road(element, format_version.minor) for element in road_elements
    )
    diagnostics = _collect_diagnostics(
        root, header_element, road_elements, format_version.minor
    )
    return OpenDriveMap(
        format_version=format_version,
        header=header,
        roads=roads,
        diagnostics=diagnostics,
    )


def _parse_road(element: ElementTree.Element, revision: int) -> Road:
    path = f"/OpenDRIVE/road[@id='{element.get('id', '?')}']"
    try:
        road_id = element.attrib["id"]
        length = _float_attribute(element, "length", path)
        junction = element.attrib["junction"]
    except (KeyError, ValueError) as error:
        road_id = element.get("id", "?")
        raise OpenDriveParseError(
            f"Road has a missing or invalid attribute: {error}",
            element=path,
        ) from error

    plan_view = next(
        (child for child in element if _local_name(child.tag) == "planView"), None
    )
    if plan_view is None:
        geometries: tuple[GeometrySegment, ...] = ()
    else:
        from pyopendrive.odr.parser.geometry import parse_plan_view

        geometries = parse_plan_view(plan_view, road_id)

    try:
        profiles = parse_road_profiles(element, path, revision)
    except ProfileParseError as error:
        raise OpenDriveParseError(error.message, element=error.element) from error

    try:
        lane_layers = parse_lane_layers(element)
    except LaneParseError as error:
        raise OpenDriveParseError(error.message, element=error.element) from error

    return Road(
        id=road_id,
        length=length,
        junction=junction,
        name=element.get("name"),
        rule=element.get("rule"),
        predecessor=_parse_road_link(element, "predecessor", path),
        successor=_parse_road_link(element, "successor", path),
        types=tuple(
            _parse_road_type(child, path)
            for child in element
            if _local_name(child.tag) == "type"
        ),
        plan_view=geometries,
        profiles=profiles,
        lane_layers=lane_layers,
    )


def _parse_road_link(
    road: ElementTree.Element, direction: str, path: str
) -> RoadLink | None:
    container = next(
        (child for child in road if _local_name(child.tag) == "link"), None
    )
    if container is None:
        return None
    element = next(
        (child for child in container if _local_name(child.tag) == direction), None
    )
    if element is None:
        return None
    link_path = f"{path}/link/{direction}"
    try:
        element_type = element.attrib["elementType"]
        element_id = element.attrib["elementId"]
        element_s = (
            _float_attribute(element, "elementS", link_path)
            if "elementS" in element.attrib
            else None
        )
    except (KeyError, ValueError) as error:
        raise OpenDriveParseError(
            f"Road link has a missing or invalid attribute: {error}",
            element=link_path,
        ) from error
    return RoadLink(
        element_type=element_type,
        element_id=element_id,
        contact_point=element.get("contactPoint"),
        element_s=element_s,
        element_dir=element.get("elementDir"),
    )


def _parse_road_type(element: ElementTree.Element, road_path: str) -> RoadType:
    path = f"{road_path}/type"
    try:
        s = _float_attribute(element, "s", path)
        road_type = element.attrib["type"]
    except (KeyError, ValueError) as error:
        raise OpenDriveParseError(
            f"Road type has a missing or invalid attribute: {error}", element=path
        ) from error
    speed_element = next(
        (child for child in element if _local_name(child.tag) == "speed"), None
    )
    speed = None
    if speed_element is not None:
        speed_path = f"{path}/speed"
        maximum = speed_element.get("max")
        if maximum is None:
            raise OpenDriveParseError(
                "Road speed is missing required attribute 'max'.", element=speed_path
            )
        if maximum in {"no limit", "undefined"}:
            value: float | str = maximum
        else:
            try:
                value = float(maximum)
                if not math.isfinite(value):
                    raise ValueError("speed must be finite")
            except ValueError as error:
                raise OpenDriveParseError(
                    f"Road speed has invalid 'max' attribute: {error}",
                    element=speed_path,
                ) from error
        speed = RoadSpeed(value=value, unit=speed_element.get("unit"))
    return RoadType(
        s=s,
        type=road_type,
        country=element.get("country"),
        source=element.get("source"),
        speed=speed,
    )


def _float_attribute(element: ElementTree.Element, attribute: str, path: str) -> float:
    try:
        value = float(element.attrib[attribute])
        if not math.isfinite(value):
            raise ValueError("value must be finite")
        return value
    except (KeyError, ValueError) as error:
        raise OpenDriveParseError(
            f"Missing or invalid '{attribute}' attribute: {error}", element=path
        ) from error


def _parse_header(element: ElementTree.Element) -> Header:
    children = {_local_name(child.tag): child for child in element}
    license_element = children.get("license")
    license_info = None
    if license_element is not None:
        name = license_element.get("name")
        if name is None:
            raise OpenDriveParseError(
                "License has a missing required 'name' attribute.",
                element="/OpenDRIVE/header/license",
            )
        license_info = License(
            name=name,
            resource=license_element.get("resource"),
            spdxid=license_element.get("spdxid"),
            text=license_element.get("text"),
        )

    offset_element = children.get("offset")
    offset = _parse_offset(offset_element) if offset_element is not None else None
    regulations_element = children.get("defaultRegulations")

    return Header(
        name=element.get("name"),
        version=element.get("version"),
        date=element.get("date"),
        vendor=element.get("vendor"),
        north=_optional_float(element, "north"),
        south=_optional_float(element, "south"),
        east=_optional_float(element, "east"),
        west=_optional_float(element, "west"),
        geo_reference=(
            "".join(children["geoReference"].itertext())
            if "geoReference" in children
            else None
        ),
        offset=offset,
        license=license_info,
        default_regulations=(
            _parse_default_regulations(regulations_element)
            if regulations_element is not None
            else None
        ),
    )


def _parse_offset(element: ElementTree.Element) -> Offset:
    return Offset(
        x=_required_float(element, "x", "/OpenDRIVE/header/offset"),
        y=_required_float(element, "y", "/OpenDRIVE/header/offset"),
        z=_required_float(element, "z", "/OpenDRIVE/header/offset"),
        hdg=_required_float(element, "hdg", "/OpenDRIVE/header/offset"),
    )


def _parse_default_regulations(element: ElementTree.Element) -> DefaultRegulations:
    roads: list[RoadRegulation] = []
    signals: list[SignalRegulation] = []
    for child in element:
        name = _local_name(child.tag)
        semantics = _parse_regulation_semantics(child)
        if name == "roadRegulations":
            roads.append(
                RoadRegulation(
                    type=_required_string(
                        child,
                        "type",
                        "/OpenDRIVE/header/defaultRegulations/roadRegulations",
                    ),
                    semantics=semantics,
                )
            )
        elif name == "signalRegulations":
            signals.append(
                SignalRegulation(
                    type=_required_string(
                        child,
                        "type",
                        "/OpenDRIVE/header/defaultRegulations/signalRegulations",
                    ),
                    subtype=_required_string(
                        child,
                        "subtype" if child.get("subtype") is not None else "subType",
                        "/OpenDRIVE/header/defaultRegulations/signalRegulations",
                    ),
                    semantics=semantics,
                )
            )
    return DefaultRegulations(road=tuple(roads), signals=tuple(signals))


def _parse_regulation_semantics(
    element: ElementTree.Element,
) -> tuple[RegulationSemantic, ...]:
    semantics: list[RegulationSemantic] = []
    for container in element:
        if _local_name(container.tag) != "semantics":
            continue
        semantics.extend(
            RegulationSemantic(
                name=_local_name(child.tag),
                attributes=tuple(
                    (_local_name(key), value) for key, value in child.attrib.items()
                ),
            )
            for child in container
        )
    return tuple(semantics)


def _required_string(element: ElementTree.Element, attribute: str, path: str) -> str:
    value = element.get(attribute)
    if value is None:
        raise OpenDriveParseError(
            f"Element has a missing required '{attribute}' attribute.", element=path
        )
    return value


def _required_float(element: ElementTree.Element, attribute: str, path: str) -> float:
    try:
        return float(element.attrib[attribute])
    except (KeyError, ValueError) as error:
        raise OpenDriveParseError(
            f"Element has a missing or invalid '{attribute}' attribute.",
            element=path,
        ) from error


def _optional_float(element: ElementTree.Element, attribute: str) -> float | None:
    value = element.get(attribute)
    if value is None:
        return None
    try:
        return float(value)
    except ValueError as error:
        raise OpenDriveParseError(
            f"Header has an invalid '{attribute}' attribute.",
            element="/OpenDRIVE/header",
        ) from error


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
    revision: int,
) -> tuple[OpenDriveDiagnostic, ...]:
    diagnostics: list[OpenDriveDiagnostic] = []
    _unsupported_attributes(root, set(), "/OpenDRIVE", diagnostics)
    _unsupported_attributes(
        header,
        {
            "revMajor",
            "revMinor",
            "name",
            "version",
            "date",
            "vendor",
            "north",
            "south",
            "east",
            "west",
        },
        "/OpenDRIVE/header",
        diagnostics,
    )
    _header_child_diagnostics(header, diagnostics)

    for road in roads:
        path = f"/OpenDRIVE/road[@id='{road.get('id', '?')}']"
        _unsupported_attributes(
            road, {"id", "length", "junction", "name", "rule"}, path, diagnostics
        )
        for child in road:
            name = _local_name(child.tag)
            if name == "link":
                _unsupported_attributes(child, set(), f"{path}/link", diagnostics)
                for link in child:
                    link_path = f"{path}/link/{_local_name(link.tag)}"
                    _unsupported_attributes(
                        link,
                        {
                            "elementType",
                            "elementId",
                            "contactPoint",
                            "elementS",
                            "elementDir",
                        },
                        link_path,
                        diagnostics,
                    )
                    _unsupported_children(link, link_path, diagnostics)
            elif name == "type":
                _unsupported_attributes(
                    child,
                    {"s", "type", "country", "source"},
                    f"{path}/type",
                    diagnostics,
                )
                for nested in child:
                    nested_name = _local_name(nested.tag)
                    nested_path = f"{path}/type/{nested_name}"
                    if nested_name == "speed":
                        _unsupported_attributes(
                            nested, {"max", "unit"}, nested_path, diagnostics
                        )
                        _unsupported_children(nested, nested_path, diagnostics)
                    else:
                        _unsupported_element(nested, nested_path, diagnostics)
            elif name == "planView":
                continue
            elif name in {"elevationProfile", "lateralProfile"}:
                supported = (
                    {"elevation"}
                    if name == "elevationProfile"
                    else {"superelevation", "shape"}
                )
                if name == "lateralProfile":
                    if revision < 6:
                        supported.add("crossfall")
                    if revision >= 8:
                        supported.add("crossSectionSurface")
                for record in child:
                    record_name = _local_name(record.tag)
                    if record_name not in supported:
                        _unsupported_element(
                            record, f"{path}/{name}/{record_name}", diagnostics
                        )
            elif name == "lanes":
                _lane_diagnostics(child, f"{path}/lanes", diagnostics)
            else:
                _unsupported_element(child, f"{path}/{name}", diagnostics)

    for child in root:
        name = _local_name(child.tag)
        if name not in {"header", "road"}:
            _unsupported_element(child, f"/OpenDRIVE/{name}", diagnostics)
    return tuple(diagnostics)


def _header_child_diagnostics(
    header: ElementTree.Element, diagnostics: list[OpenDriveDiagnostic]
) -> None:
    known_children = {"geoReference", "offset", "license", "defaultRegulations"}
    for child in header:
        name = _local_name(child.tag)
        path = f"/OpenDRIVE/header/{name}"
        if name not in known_children:
            _unsupported_element(child, path, diagnostics)
        elif name == "offset":
            _unsupported_attributes(child, {"x", "y", "z", "hdg"}, path, diagnostics)
        elif name == "license":
            _unsupported_attributes(
                child, {"name", "resource", "spdxid", "text"}, path, diagnostics
            )
        elif name == "defaultRegulations":
            _default_regulation_diagnostics(child, path, diagnostics)


def _default_regulation_diagnostics(
    element: ElementTree.Element,
    path: str,
    diagnostics: list[OpenDriveDiagnostic],
) -> None:
    for regulation in element:
        name = _local_name(regulation.tag)
        regulation_path = f"{path}/{name}"
        if name == "roadRegulations":
            _unsupported_attributes(regulation, {"type"}, regulation_path, diagnostics)
        elif name == "signalRegulations":
            _unsupported_attributes(
                regulation, {"type", "subtype", "subType"}, regulation_path, diagnostics
            )
        else:
            _unsupported_element(regulation, regulation_path, diagnostics)
            continue

        for container in regulation:
            container_name = _local_name(container.tag)
            container_path = f"{regulation_path}/{container_name}"
            if container_name != "semantics":
                _unsupported_element(container, container_path, diagnostics)
                continue
            for semantic in container:
                semantic_name = _local_name(semantic.tag)
                if semantic_name not in {"speed", "priority"}:
                    _unsupported_element(
                        semantic, f"{container_path}/{semantic_name}", diagnostics
                    )


def _lane_diagnostics(
    element: ElementTree.Element,
    path: str,
    diagnostics: list[OpenDriveDiagnostic],
) -> None:
    supported_children = {
        "lanes": {"laneOffset", "laneSection"},
        "laneSection": {"left", "center", "right"},
        "left": {"lane"},
        "center": {"lane"},
        "right": {"lane"},
        "lane": {
            "link",
            "width",
            "border",
            "roadMark",
            "material",
            "speed",
            "access",
            "height",
            "rule",
        },
        "link": {"predecessor", "successor"},
        "roadMark": {"type"},
        "type": {"line"},
    }
    supported_attributes = {
        "lanes": {"layer"},
        "laneOffset": {"s", "a", "b", "c", "d"},
        "laneSection": {"s", "length", "singleSide"},
        "lane": {
            "id",
            "type",
            "level",
            "roadWorks",
            "advisory",
            "direction",
            "dynamicLaneDirection",
            "dynamicLaneType",
        },
        "predecessor": {"id", "layer"},
        "successor": {"id", "layer"},
        "width": {"sOffset", "a", "b", "c", "d"},
        "border": {"sOffset", "a", "b", "c", "d"},
        "roadMark": {
            "sOffset",
            "type",
            "material",
            "weight",
            "color",
            "width",
            "laneChange",
            "height",
        },
        "type": {"name", "width"},
        "line": {"sOffset", "length", "space", "tOffset", "rule", "width"},
        "material": {"sOffset", "surface", "friction", "roughness"},
        "speed": {"sOffset", "max", "unit"},
        "access": {"sOffset", "restriction", "rule"},
        "height": {"sOffset", "inner", "outer"},
        "rule": {"sOffset"},
    }
    name = _local_name(element.tag)
    _unsupported_attributes(
        element, supported_attributes.get(name, set()), path, diagnostics
    )
    allowed = supported_children.get(name, set())
    for child in element:
        child_name = _local_name(child.tag)
        child_path = f"{path}/{child_name}"
        if child_name not in allowed:
            _unsupported_element(child, child_path, diagnostics)
        else:
            _lane_diagnostics(child, child_path, diagnostics)


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


def _unsupported_children(
    element: ElementTree.Element,
    path: str,
    diagnostics: list[OpenDriveDiagnostic],
) -> None:
    for child in element:
        name = _local_name(child.tag)
        _unsupported_element(child, f"{path}/{name}", diagnostics)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", maxsplit=1)[-1]
