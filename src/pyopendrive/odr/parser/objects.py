from xml.etree.ElementTree import Element

from pyopendrive.odr.models.geometry import Arc, Line, ParamPoly3
from pyopendrive.odr.models.objects import (
    CornerLocal,
    CornerRoad,
    CurveLocal,
    ObjectMarking,
    ObjectOutline,
    ObjectReference,
    RoadObject,
)
from pyopendrive.odr.parser.signals import (
    RoadRecordParseError,
    boolean,
    children,
    integer,
    local_name,
    number,
    optional_number,
    parse_validity,
    string,
    yes_no,
)


def parse_objects(
    road: Element, path: str
) -> tuple[tuple[RoadObject, ...], tuple[ObjectReference, ...]]:
    objects: list[RoadObject] = []
    references: list[ObjectReference] = []
    for container in children(road, "objects"):
        for element in container:
            name = local_name(element.tag)
            record_path = f"{path}/objects/{name}[@id='{element.get('id', '?')}']"
            if name == "objectReference":
                references.append(
                    ObjectReference(
                        id=string(element, "id", record_path),
                        s=number(element, "s", record_path),
                        t=number(element, "t", record_path),
                        orientation=string(element, "orientation", record_path),
                        z_offset=optional_number(element, "zOffset", record_path),
                        valid_length=optional_number(
                            element, "validLength", record_path
                        ),
                        validity=parse_validity(element, record_path),
                    )
                )
            elif name == "object":
                outlines: list[ObjectOutline] = []
                for child in element:
                    child_name = local_name(child.tag)
                    if child_name == "outline":
                        outlines.append(_outline(child, f"{record_path}/outline"))
                    elif child_name == "outlines":
                        outlines.extend(
                            _outline(outline, f"{record_path}/outlines/outline")
                            for outline in children(child, "outline")
                        )
                objects.append(
                    RoadObject(
                        id=string(element, "id", record_path),
                        s=number(element, "s", record_path),
                        t=number(element, "t", record_path),
                        z_offset=number(element, "zOffset", record_path),
                        name=element.get("name"),
                        type=element.get("type"),
                        subtype=element.get("subtype"),
                        orientation=element.get("orientation"),
                        dynamic=yes_no(element, record_path),
                        perpendicular_to_road=boolean(
                            element, "perpToRoad", record_path
                        ),
                        temporary=boolean(element, "temporary", record_path),
                        invalidated=boolean(element, "invalidated", record_path),
                        validity=parse_validity(element, record_path),
                        outlines=tuple(outlines),
                        markings=_markings(element, record_path),
                        **{
                            key: optional_number(element, attr, record_path)
                            for key, attr in (
                                ("heading", "hdg"),
                                ("pitch", "pitch"),
                                ("roll", "roll"),
                                ("height", "height"),
                                ("length", "length"),
                                ("width", "width"),
                                ("radius", "radius"),
                                ("valid_length", "validLength"),
                            )
                        },
                    )
                )
    return tuple(objects), tuple(references)


def _outline(element: Element, path: str) -> ObjectOutline:
    corners: list[CornerRoad | CornerLocal | CurveLocal] = []
    for child in element:
        name = local_name(child.tag)
        if name not in {"cornerRoad", "cornerLocal", "curveLocal"}:
            continue
        child_path = f"{path}/{name}"
        corner_id = integer(child, "id", child_path) if "id" in child.attrib else None
        if name == "cornerRoad":
            corners.append(
                CornerRoad(
                    s=number(child, "s", child_path),
                    t=number(child, "t", child_path),
                    dz=number(child, "dz", child_path),
                    height=number(child, "height", child_path),
                    id=corner_id,
                )
            )
        elif name in {"cornerLocal", "curveLocal"}:
            coordinates = {
                attr: number(child, attr, child_path)
                for attr in ("u", "v", "z", "height")
            }
            if name == "cornerLocal":
                corners.append(CornerLocal(id=corner_id, **coordinates))
            else:
                corners.append(
                    CurveLocal(
                        id=corner_id,
                        heading=optional_number(child, "hdg", child_path),
                        length=optional_number(child, "length", child_path),
                        primitive=_curve_primitive(child, child_path),
                        **coordinates,
                    )
                )
    return ObjectOutline(
        corners=tuple(corners),
        id=integer(element, "id", path) if "id" in element.attrib else None,
        closed=boolean(element, "closed", path),
        outer=boolean(element, "outer", path),
        fill_type=element.get("fillType"),
        lane_type=element.get("laneType"),
        markings=_markings(element, path),
    )


def _curve_primitive(element: Element, path: str) -> Line | Arc | ParamPoly3:
    primitives = tuple(
        child
        for child in element
        if local_name(child.tag) in {"line", "arc", "paramPoly3"}
    )
    if len(primitives) != 1:
        raise RoadRecordParseError(
            "Curve requires exactly one line, arc, or paramPoly3.", element=path
        )
    primitive = primitives[0]
    name = local_name(primitive.tag)
    primitive_path = f"{path}/{name}"
    if name == "line":
        return Line()
    if name == "arc":
        return Arc(curvature=number(primitive, "curvature", primitive_path))
    return ParamPoly3(
        **{
            f"{coefficient}_{axis.lower()}": number(
                primitive, f"{coefficient}{axis}", primitive_path
            )
            for axis in ("U", "V")
            for coefficient in ("a", "b", "c", "d")
        },
        p_range=string(primitive, "pRange", primitive_path),
    )


def _markings(element: Element, path: str) -> tuple[ObjectMarking, ...]:
    markings: list[ObjectMarking] = []
    for container in children(element, "markings"):
        for marking in children(container, "marking"):
            marking_path = f"{path}/markings/marking"
            markings.append(
                ObjectMarking(
                    color=string(marking, "color", marking_path),
                    line_length=number(marking, "lineLength", marking_path),
                    space_length=number(marking, "spaceLength", marking_path),
                    start_offset=number(marking, "startOffset", marking_path),
                    stop_offset=number(marking, "stopOffset", marking_path),
                    side=marking.get("side"),
                    weight=marking.get("weight"),
                    width=optional_number(marking, "width", marking_path),
                    z_offset=optional_number(marking, "zOffset", marking_path),
                    corner_references=tuple(
                        integer(child, "id", f"{marking_path}/cornerReference")
                        for child in children(marking, "cornerReference")
                    ),
                )
            )
    return tuple(markings)


OBJECT_RULES = {
    "objects": (set(), {"object", "objectReference"}),
    "object": (
        {
            "id",
            "s",
            "t",
            "zOffset",
            "name",
            "type",
            "subtype",
            "orientation",
            "dynamic",
            "hdg",
            "pitch",
            "roll",
            "height",
            "length",
            "width",
            "radius",
            "validLength",
            "perpToRoad",
            "temporary",
            "invalidated",
        },
        {"validity", "outline", "outlines", "markings"},
    ),
    "objectReference": (
        {"id", "s", "t", "orientation", "zOffset", "validLength"},
        {"validity"},
    ),
    "validity": ({"fromLane", "toLane", "layer"}, set()),
    "outlines": (set(), {"outline"}),
    "outline": (
        {"id", "closed", "outer", "fillType", "laneType"},
        {"cornerRoad", "cornerLocal", "curveLocal", "markings"},
    ),
    "cornerRoad": ({"id", "s", "t", "dz", "height"}, set()),
    "cornerLocal": ({"id", "u", "v", "z", "height"}, set()),
    "curveLocal": (
        {"id", "u", "v", "z", "height", "hdg", "length"},
        {"line", "arc", "paramPoly3"},
    ),
    "line": (set(), set()),
    "arc": ({"curvature"}, set()),
    "paramPoly3": ({"aU", "bU", "cU", "dU", "aV", "bV", "cV", "dV", "pRange"}, set()),
    "markings": (set(), {"marking"}),
    "marking": (
        {
            "color",
            "lineLength",
            "spaceLength",
            "startOffset",
            "stopOffset",
            "side",
            "weight",
            "width",
            "zOffset",
        },
        {"cornerReference"},
    ),
    "cornerReference": ({"id"}, set()),
}
