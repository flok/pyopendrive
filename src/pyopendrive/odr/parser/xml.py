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
    Platform,
    PlatformSegment,
    RailroadSwitch,
    RailroadTrack,
    RegulationSemantic,
    Road,
    RoadCrg,
    RoadLink,
    RoadRegulation,
    RoadSpeed,
    RoadType,
    SignalRegulation,
    Station,
    SwitchPartner,
)
from pyopendrive.odr.models.geometry import GeometrySegment
from pyopendrive.odr.parser.junctions import (
    JunctionParseError,
    parse_controller,
    parse_junction,
    parse_junction_group,
)
from pyopendrive.odr.parser.lanes import LaneParseError, parse_lane_layers
from pyopendrive.odr.parser.objects import OBJECT_RULES, parse_objects
from pyopendrive.odr.parser.profiles import ProfileParseError, parse_road_profiles
from pyopendrive.odr.parser.signals import (
    SIGNAL_RULES,
    RoadRecordParseError,
    parse_signals,
    record_diagnostics,
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
    header = _parse_header(header_element)
    road_elements = [element for element in root if _local_name(element.tag) == "road"]
    roads = tuple(
        _parse_road(element, format_version.minor) for element in road_elements
    )
    try:
        junctions = tuple(
            parse_junction(child)
            for child in root
            if _local_name(child.tag) == "junction"
        )
        junction_groups = tuple(
            parse_junction_group(child)
            for child in root
            if _local_name(child.tag) == "junctionGroup"
        )
        controllers = tuple(
            parse_controller(child)
            for child in root
            if _local_name(child.tag) == "controller"
        )
    except JunctionParseError as error:
        raise OpenDriveParseError(error.message, element=error.element) from error
    stations = (
        tuple(
            _parse_station(child)
            for child in root
            if _local_name(child.tag) == "station"
        )
        if format_version.minor >= 7
        else ()
    )

    diagnostics = _collect_diagnostics(
        root, header_element, road_elements, format_version.minor
    )
    return OpenDriveMap(
        format_version=format_version,
        header=header,
        roads=roads,
        diagnostics=diagnostics,
        junctions=junctions,
        junction_groups=junction_groups,
        controllers=controllers,
        stations=stations,
    )


def _parse_station(element: ElementTree.Element) -> Station:
    path = f"/OpenDRIVE/station[@id='{element.get('id', '?')}']"
    return Station(
        id=_required_string(element, "id", path),
        name=_required_string(element, "name", path),
        type=element.get("type"),
        platforms=tuple(
            Platform(
                id=_required_string(platform, "id", f"{path}/platform"),
                name=platform.get("name"),
                segments=tuple(
                    PlatformSegment(
                        road_id=_required_string(
                            segment, "roadId", f"{path}/platform/segment"
                        ),
                        s_start=_required_float(
                            segment, "sStart", f"{path}/platform/segment"
                        ),
                        s_end=_required_float(
                            segment, "sEnd", f"{path}/platform/segment"
                        ),
                        side=_required_string(
                            segment, "side", f"{path}/platform/segment"
                        ),
                    )
                    for segment in platform
                    if _local_name(segment.tag) == "segment"
                ),
            )
            for platform in element
            if _local_name(platform.tag) == "platform"
        ),
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

    try:
        signals, signal_references = parse_signals(element, path)
        objects, object_references = parse_objects(element, path)
    except RoadRecordParseError as error:
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
        signals=signals,
        signal_references=signal_references,
        objects=objects,
        object_references=object_references,
        crgs=_parse_road_crgs(element, path, revision),
        switches=_parse_road_switches(element, path, revision),
    )


def _parse_road_crgs(
    road: ElementTree.Element, path: str, revision: int
) -> tuple[RoadCrg, ...]:
    surface = next(
        (child for child in road if _local_name(child.tag) == "surface"), None
    )
    if surface is None:
        return ()

    crgs = []
    for index, element in enumerate(surface):
        if _local_name(element.tag) != "CRG":
            continue
        crg_path = f"{path}/surface/CRG[{index}]"
        file = element.get("file")
        mode = element.get("mode")
        orientation = element.get("orientation")
        if file is None or mode is None or orientation is None:
            missing = next(
                name
                for name, value in (
                    ("file", file),
                    ("mode", mode),
                    ("orientation", orientation),
                )
                if value is None
            )
            raise OpenDriveParseError(
                f"CRG is missing required '{missing}' attribute.", element=crg_path
            )
        crgs.append(
            RoadCrg(
                file=file,
                mode=mode,
                orientation=orientation,
                s_start=_float_attribute(element, "sStart", crg_path),
                s_end=_float_attribute(element, "sEnd", crg_path),
                purpose=element.get("purpose"),
                h_offset=(
                    _float_attribute(element, "hOffset", crg_path)
                    if "hOffset" in element.attrib
                    else None
                ),
                s_offset=(
                    _float_attribute(element, "sOffset", crg_path)
                    if "sOffset" in element.attrib
                    else None
                ),
                t_offset=(
                    _float_attribute(element, "tOffset", crg_path)
                    if "tOffset" in element.attrib
                    else None
                ),
                x_offset=(
                    _float_attribute(element, "xOffset", crg_path)
                    if revision >= 9 and "xOffset" in element.attrib
                    else None
                ),
                y_offset=(
                    _float_attribute(element, "yOffset", crg_path)
                    if revision >= 9 and "yOffset" in element.attrib
                    else None
                ),
                z_offset=(
                    _float_attribute(element, "zOffset", crg_path)
                    if "zOffset" in element.attrib
                    else None
                ),
                z_scale=(
                    _float_attribute(element, "zScale", crg_path)
                    if "zScale" in element.attrib
                    else None
                ),
            )
        )
    return tuple(crgs)


def _parse_road_switches(
    road: ElementTree.Element, path: str, revision: int
) -> tuple[RailroadSwitch, ...]:
    if revision < 7:
        return ()
    railroad = next(
        (child for child in road if _local_name(child.tag) == "railroad"), None
    )
    if railroad is None:
        return ()

    switches = []
    for switch in railroad:
        if _local_name(switch.tag) != "switch":
            continue
        switch_path = f"{path}/railroad/switch[@id='{switch.get('id', '?')}']"

        def track(
            switch_element: ElementTree.Element, path: str, name: str
        ) -> RailroadTrack:
            element = next(
                (child for child in switch_element if _local_name(child.tag) == name),
                None,
            )
            if element is None:
                raise OpenDriveParseError(
                    f"Switch is missing required '{name}' element.",
                    element=path,
                )
            track_path = f"{path}/{name}"
            return RailroadTrack(
                _required_string(element, "id", track_path),
                _required_float(element, "s", track_path),
                _required_string(element, "dir", track_path),
            )

        partner_element = next(
            (child for child in switch if _local_name(child.tag) == "partner"), None
        )
        partner = (
            SwitchPartner(
                _required_string(partner_element, "id", f"{switch_path}/partner"),
                partner_element.get("name"),
            )
            if partner_element is not None
            else None
        )
        switches.append(
            RailroadSwitch(
                id=_required_string(switch, "id", switch_path),
                name=_required_string(switch, "name", switch_path),
                position=_required_string(switch, "position", switch_path),
                main_track=track(switch, switch_path, "mainTrack"),
                side_track=track(switch, switch_path, "sideTrack"),
                partner=partner,
            )
        )
    return tuple(switches)


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
            elif name in {"signals", "objects"}:
                diagnostics.extend(
                    record_diagnostics(
                        child,
                        f"{path}/{name}",
                        SIGNAL_RULES if name == "signals" else OBJECT_RULES,
                        revision,
                    )
                )
            elif name == "lanes":
                _lane_diagnostics(child, f"{path}/lanes", diagnostics)
            elif name == "surface":
                for index, crg in enumerate(child):
                    crg_name = _local_name(crg.tag)
                    crg_path = f"{path}/surface/{crg_name}[{index}]"
                    if crg_name == "CRG":
                        attributes = {
                            "file",
                            "hOffset",
                            "mode",
                            "orientation",
                            "purpose",
                            "sEnd",
                            "sOffset",
                            "sStart",
                            "tOffset",
                            "zOffset",
                            "zScale",
                        }
                        if revision >= 9:
                            attributes.update({"xOffset", "yOffset"})
                        _unsupported_attributes(crg, attributes, crg_path, diagnostics)
                        _unsupported_children(crg, crg_path, diagnostics)
                    else:
                        _unsupported_element(crg, crg_path, diagnostics)
            elif name == "railroad" and revision >= 7:
                railroad_path = f"{path}/railroad"
                _unsupported_attributes(child, set(), railroad_path, diagnostics)
                for switch in child:
                    switch_name = _local_name(switch.tag)
                    switch_path = f"{railroad_path}/{switch_name}"
                    if switch_name != "switch":
                        _unsupported_element(switch, switch_path, diagnostics)
                        continue
                    _unsupported_attributes(
                        switch, {"id", "name", "position"}, switch_path, diagnostics
                    )
                    for record in switch:
                        record_name = _local_name(record.tag)
                        record_path = f"{switch_path}/{record_name}"
                        if record_name in {"mainTrack", "sideTrack"}:
                            _unsupported_attributes(
                                record, {"id", "s", "dir"}, record_path, diagnostics
                            )
                            _unsupported_children(record, record_path, diagnostics)
                        elif record_name == "partner":
                            _unsupported_attributes(
                                record, {"id", "name"}, record_path, diagnostics
                            )
                            _unsupported_children(record, record_path, diagnostics)
                        else:
                            _unsupported_element(record, record_path, diagnostics)
            else:
                _unsupported_element(child, f"{path}/{name}", diagnostics)

    for child in root:
        name = _local_name(child.tag)
        if name in {"junction", "junctionGroup", "controller"}:
            path = f"/OpenDRIVE/{name}[@id='{child.get('id', '?')}']"
            _junction_diagnostics(child, path, diagnostics)
        elif name == "station" and revision >= 7:
            path = f"/OpenDRIVE/station[@id='{child.get('id', '?')}']"
            _unsupported_attributes(child, {"id", "name", "type"}, path, diagnostics)
            for platform in child:
                platform_name = _local_name(platform.tag)
                platform_path = f"{path}/{platform_name}"
                if platform_name != "platform":
                    _unsupported_element(platform, platform_path, diagnostics)
                    continue
                _unsupported_attributes(
                    platform, {"id", "name"}, platform_path, diagnostics
                )
                for segment in platform:
                    segment_name = _local_name(segment.tag)
                    segment_path = f"{platform_path}/{segment_name}"
                    if segment_name == "segment":
                        _unsupported_attributes(
                            segment,
                            {"roadId", "sStart", "sEnd", "side"},
                            segment_path,
                            diagnostics,
                        )
                        _unsupported_children(segment, segment_path, diagnostics)
                    else:
                        _unsupported_element(segment, segment_path, diagnostics)
        elif name not in {"header", "road"}:
            _unsupported_element(child, f"/OpenDRIVE/{name}", diagnostics)
    return tuple(diagnostics)


def _junction_diagnostics(
    element: ElementTree.Element,
    path: str,
    diagnostics: list[OpenDriveDiagnostic],
) -> None:
    attributes = {
        "junction": {"id", "name", "type", "mainRoad", "orientation", "sStart", "sEnd"},
        "crossPath": {"id", "crossingRoad", "roadAtStart", "roadAtEnd"},
        "startLaneLink": {"s", "from", "to"},
        "endLaneLink": {"s", "from", "to"},
        "planView": set(),
        "geometry": {"s", "x", "y", "hdg", "length"},
        "line": set(),
        "boundary": set(),
        "segment": {
            "type",
            "roadId",
            "boundaryLane",
            "sStart",
            "sEnd",
            "contactPoint",
            "jointLaneStart",
            "jointLaneEnd",
            "transitionLength",
        },
        "elevationGrid": {"sStart", "gridSpacing"},
        "elevation": {"center", "left", "right"},
        "surface": set(),
        "CRG": {
            "file",
            "mode",
            "orientation",
            "purpose",
            "sStart",
            "sEnd",
            "hOffset",
            "sOffset",
            "tOffset",
            "zOffset",
            "zScale",
        },
        "connection": {
            "id",
            "incomingRoad",
            "connectingRoad",
            "linkedRoad",
            "contactPoint",
            "type",
        },
        "laneLink": {"from", "to", "overlapZone"},
        "predecessor": {
            "elementType",
            "elementId",
            "elementS",
            "elementDir",
            "contactPoint",
        },
        "successor": {
            "elementType",
            "elementId",
            "elementS",
            "elementDir",
            "contactPoint",
        },
        "priority": {"high", "low"},
        "controller": {"id", "name", "sequence", "type"},
        "control": {"signalId", "type"},
        "roadSection": {"id", "roadId", "sStart", "sEnd"},
        "junctionGroup": {"id", "name", "type"},
        "junctionReference": {"junction"},
    }
    children = {
        "junction": {
            "connection",
            "priority",
            "controller",
            "roadSection",
            "crossPath",
            "planView",
            "boundary",
            "elevationGrid",
            "surface",
        },
        "connection": {"laneLink", "predecessor", "successor"},
        "junctionGroup": {"junctionReference"},
        "crossPath": {"startLaneLink", "endLaneLink"},
        "planView": {"geometry"},
        "geometry": {"line"},
        "boundary": {"segment"},
        "elevationGrid": {"elevation"},
        "surface": {"CRG"},
        "controller": {"control"}
        if path.startswith("/OpenDRIVE/controller[")
        else set(),
    }
    name = _local_name(element.tag)
    supported_attributes = attributes[name]
    if name == "controller":
        supported_attributes = (
            {"id", "name", "sequence"}
            if path.startswith("/OpenDRIVE/controller[")
            else {"id", "sequence", "type"}
        )
    _unsupported_attributes(element, supported_attributes, path, diagnostics)
    for child in element:
        child_name = _local_name(child.tag)
        child_path = f"{path}/{child_name}"
        if child.get("id") is not None:
            child_path += f"[@id='{child.get('id')}']"
        if child_name in children.get(name, set()):
            _junction_diagnostics(child, child_path, diagnostics)
        else:
            _unsupported_element(child, child_path, diagnostics)


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
        "rule": {"sOffset", "value"},
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
        if attribute not in supported:
            diagnostics.append(
                OpenDriveDiagnostic(
                    code="unsupported-attribute",
                    message=f"Attribute '{attribute}' is not currently parsed.",
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
