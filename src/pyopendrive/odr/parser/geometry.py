"""Plan-view geometry parsing helpers."""

from xml.etree import ElementTree

from pyopendrive.odr.models.geometry import (
    Arc,
    GeometryPrimitive,
    GeometrySegment,
    Line,
    ParamPoly3,
    Poly3,
    Spiral,
)
from pyopendrive.odr.parser.xml import OpenDriveParseError, _local_name


def parse_plan_view(
    element: ElementTree.Element, road_id: str
) -> tuple[GeometrySegment, ...]:
    road_path = f"/OpenDRIVE/road[@id='{road_id}']"
    segments: list[GeometrySegment] = []
    for index, geometry in enumerate(element, start=1):
        path = f"{road_path}/planView/geometry[{index}]"
        try:
            s = _required_float(geometry, "s")
            x = _required_float(geometry, "x")
            y = _required_float(geometry, "y")
            heading = _required_float(geometry, "hdg")
            length = _required_float(geometry, "length")
            children = list(geometry)
            if len(children) != 1:
                raise ValueError("expected exactly one geometry primitive")
            primitive = _parse_primitive(children[0])
        except (KeyError, ValueError) as error:
            raise OpenDriveParseError(
                f"Geometry has missing or invalid data: {error}", element=path
            ) from error

        segments.append(GeometrySegment(s, x, y, heading, length, primitive))
    return tuple(segments)


def _parse_primitive(element: ElementTree.Element) -> GeometryPrimitive:
    name = _local_name(element.tag)
    if name == "line":
        return Line()
    if name == "arc":
        return Arc(_required_float(element, "curvature"))
    if name == "spiral":
        return Spiral(
            _required_float(element, "curvStart"),
            _required_float(element, "curvEnd"),
        )
    if name == "poly3":
        return Poly3(*(_required_float(element, key) for key in "abcd"))
    if name == "paramPoly3":
        return ParamPoly3(
            *(
                _required_float(element, key)
                for key in ("aU", "bU", "cU", "dU", "aV", "bV", "cV", "dV")
            ),
            p_range=_required_text(element, "pRange"),
        )
    raise ValueError(f"unsupported geometry primitive '{name}'")


def _required_float(element: ElementTree.Element, attribute: str) -> float:
    try:
        return float(element.attrib[attribute])
    except (KeyError, ValueError) as error:
        raise ValueError(f"missing or invalid '{attribute}' attribute") from error


def _required_text(element: ElementTree.Element, attribute: str) -> str:
    try:
        return element.attrib[attribute]
    except KeyError as error:
        raise ValueError(f"missing '{attribute}' attribute") from error
