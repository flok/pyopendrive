"""Parse road lane layers into immutable lane models."""

from xml.etree import ElementTree

from pyopendrive.odr.models.lanes import (
    Lane,
    LaneAccess,
    LaneGroups,
    LaneHeight,
    LaneLayer,
    LaneLink,
    LaneLinks,
    LaneMaterial,
    LanePolynomial,
    LaneRoadMark,
    LaneRoadMarkLine,
    LaneRoadMarkType,
    LaneRule,
    LaneSection,
    LaneSpeed,
)


class LaneParseError(ValueError):
    """Raised when a lane element cannot be converted to a model."""

    def __init__(self, message: str, *, element: str) -> None:
        self.message = message
        self.element = element
        super().__init__(f"{message} ({element})")


def parse_lane_layers(road: ElementTree.Element) -> tuple[LaneLayer, ...]:
    """Parse all ``lanes`` children of a road, preserving their order."""
    road_id = road.get("id", "?")
    path = f"/OpenDRIVE/road[@id='{road_id}']"
    return tuple(
        _parse_layer(element, f"{path}/lanes[{index}]")
        for index, element in enumerate(_children(road, "lanes"))
    )


def _parse_layer(element: ElementTree.Element, path: str) -> LaneLayer:
    sections = tuple(
        _parse_section(section, f"{path}/laneSection[{index}]")
        for index, section in enumerate(_children(element, "laneSection"))
    )
    return LaneLayer(layer=element.get("layer"), sections=sections)


def _parse_section(element: ElementTree.Element, path: str) -> LaneSection:
    section_s = _required_float(element, "s", path)
    center_elements = _children(element, "center")
    if len(center_elements) != 1:
        raise LaneParseError(
            "Lane section must contain exactly one center group.", element=path
        )

    groups: dict[str, tuple[Lane, ...] | None] = {"left": None, "right": None}
    center_lanes: tuple[Lane, ...] = ()
    order: list[str] = []
    for group in element:
        group_name = _local_name(group.tag)
        if group_name not in {"left", "center", "right"}:
            continue
        order.append(group_name)
        lanes = tuple(
            _parse_lane(lane, f"{path}/{group_name}/lane[{index}]")
            for index, lane in enumerate(_children(group, "lane"))
        )
        if group_name == "center":
            center_lanes = lanes
        else:
            if groups[group_name] is not None:
                raise LaneParseError(f"Duplicate {group_name} group.", element=path)
            groups[group_name] = lanes
    if len(center_lanes) != 1:
        raise LaneParseError(
            "Center group must contain exactly one lane.",
            element=f"{path}/center",
        )

    return LaneSection(
        s=section_s,
        length=_optional_float(element, "length", path),
        single_side=_optional_bool(element, "singleSide", path),
        lanes=LaneGroups(
            left=groups["left"],
            center=center_lanes,
            right=groups["right"],
            order=tuple(order),
        ),
    )


def _parse_lane(element: ElementTree.Element, path: str) -> Lane:
    lane_id = _required_int(element, "id", path)
    links_element = _child(element, "link")
    links = LaneLinks()
    if links_element is not None:
        links = LaneLinks(
            predecessors=tuple(
                _parse_link(link, f"{path}/link/predecessor[{index}]")
                for index, link in enumerate(_children(links_element, "predecessor"))
            ),
            successors=tuple(
                _parse_link(link, f"{path}/link/successor[{index}]")
                for index, link in enumerate(_children(links_element, "successor"))
            ),
        )

    return Lane(
        id=lane_id,
        lane_type=element.get("type"),
        level=_optional_bool(element, "level", path),
        road_works=_optional_bool(element, "roadWorks", path),
        advisory=element.get("advisory"),
        direction=element.get("direction"),
        dynamic_lane_direction=_optional_bool(element, "dynamicLaneDirection", path),
        dynamic_lane_type=_optional_bool(element, "dynamicLaneType", path),
        links=links,
        widths=tuple(
            _parse_polynomial(child, f"{path}/width[{index}]")
            for index, child in enumerate(_children(element, "width"))
        ),
        borders=tuple(
            _parse_polynomial(child, f"{path}/border[{index}]")
            for index, child in enumerate(_children(element, "border"))
        ),
        road_marks=tuple(
            _parse_road_mark(child, f"{path}/roadMark[{index}]")
            for index, child in enumerate(_children(element, "roadMark"))
        ),
        materials=tuple(
            LaneMaterial(
                s_offset=_required_float(child, "sOffset", f"{path}/material[{index}]"),
                surface=child.get("surface"),
                friction=_optional_float(
                    child, "friction", f"{path}/material[{index}]"
                ),
                roughness=_optional_float(
                    child, "roughness", f"{path}/material[{index}]"
                ),
            )
            for index, child in enumerate(_children(element, "material"))
        ),
        speeds=tuple(
            LaneSpeed(
                s_offset=_required_float(child, "sOffset", f"{path}/speed[{index}]"),
                max=_optional_float(child, "max", f"{path}/speed[{index}]"),
                unit=child.get("unit"),
            )
            for index, child in enumerate(_children(element, "speed"))
        ),
        access=tuple(
            LaneAccess(
                s_offset=_required_float(child, "sOffset", f"{path}/access[{index}]"),
                restriction=child.get("restriction"),
                rule=child.get("rule"),
            )
            for index, child in enumerate(_children(element, "access"))
        ),
        heights=tuple(
            LaneHeight(
                s_offset=_required_float(child, "sOffset", f"{path}/height[{index}]"),
                inner=_optional_float(child, "inner", f"{path}/height[{index}]"),
                outer=_optional_float(child, "outer", f"{path}/height[{index}]"),
            )
            for index, child in enumerate(_children(element, "height"))
        ),
        rules=tuple(
            _parse_rule(child, f"{path}/rule[{index}]")
            for index, child in enumerate(_children(element, "rule"))
        ),
    )


def _parse_link(element: ElementTree.Element, path: str) -> LaneLink:
    return LaneLink(
        id=_required_int(element, "id", path),
        layer=element.get("layer"),
    )


def _parse_polynomial(element: ElementTree.Element, path: str) -> LanePolynomial:
    return LanePolynomial(
        s_offset=_required_float(element, "sOffset", path),
        a=_required_float(element, "a", path),
        b=_required_float(element, "b", path),
        c=_required_float(element, "c", path),
        d=_required_float(element, "d", path),
    )


def _parse_road_mark(element: ElementTree.Element, path: str) -> LaneRoadMark:
    type_element = _child(element, "type")
    type_definition = None
    if type_element is not None:
        type_path = f"{path}/type"
        type_definition = LaneRoadMarkType(
            name=_required_attribute(type_element, "name", type_path),
            width=_required_float(type_element, "width", type_path),
            lines=tuple(
                LaneRoadMarkLine(
                    s_offset=_required_float(
                        line, "sOffset", f"{type_path}/line[{index}]"
                    ),
                    length=_optional_float(
                        line, "length", f"{type_path}/line[{index}]"
                    ),
                    space=_optional_float(line, "space", f"{type_path}/line[{index}]"),
                    t_offset=_optional_float(
                        line, "tOffset", f"{type_path}/line[{index}]"
                    ),
                    rule=line.get("rule"),
                    width=_optional_float(line, "width", f"{type_path}/line[{index}]"),
                )
                for index, line in enumerate(_children(type_element, "line"))
            ),
        )
    return LaneRoadMark(
        s_offset=_required_float(element, "sOffset", path),
        mark_type=element.get("type"),
        material=element.get("material"),
        weight=element.get("weight"),
        color=element.get("color"),
        width=_optional_float(element, "width", path),
        lane_change=element.get("laneChange"),
        height=_optional_float(element, "height", path),
        type_definition=type_definition,
    )


def _parse_rule(element: ElementTree.Element, path: str) -> LaneRule:
    s_offset = _required_float(element, "sOffset", path)
    if element.text is None:
        raise LaneParseError("Rule has no value.", element=path)
    return LaneRule(s_offset=s_offset, value=element.text)


def _required_attribute(element: ElementTree.Element, name: str, path: str) -> str:
    value = element.get(name)
    if value is None:
        raise LaneParseError(f"Missing required '{name}' attribute.", element=path)
    return value


def _required_int(element: ElementTree.Element, name: str, path: str) -> int:
    value = _required_attribute(element, name, path)
    try:
        return int(value)
    except ValueError as error:
        raise LaneParseError(
            f"Invalid integer '{name}' value {value!r}.", element=path
        ) from error


def _required_float(element: ElementTree.Element, name: str, path: str) -> float:
    value = _required_attribute(element, name, path)
    try:
        return float(value)
    except ValueError as error:
        raise LaneParseError(
            f"Invalid number '{name}' value {value!r}.", element=path
        ) from error


def _optional_float(element: ElementTree.Element, name: str, path: str) -> float | None:
    value = element.get(name)
    if value is None:
        return None
    try:
        return float(value)
    except ValueError as error:
        raise LaneParseError(
            f"Invalid number '{name}' value {value!r}.", element=path
        ) from error


def _optional_bool(element: ElementTree.Element, name: str, path: str) -> bool | None:
    value = element.get(name)
    if value is None:
        return None
    if value in {"true", "1"}:
        return True
    if value in {"false", "0"}:
        return False
    raise LaneParseError(f"Invalid boolean '{name}' value {value!r}.", element=path)


def _children(element: ElementTree.Element, name: str) -> list[ElementTree.Element]:
    return [child for child in element if _local_name(child.tag) == name]


def _child(element: ElementTree.Element, name: str) -> ElementTree.Element | None:
    return next((child for child in element if _local_name(child.tag) == name), None)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", maxsplit=1)[-1]
