"""Parse supported OpenDRIVE road profile records."""

from xml.etree import ElementTree

from pyopendrive.odr.models.profiles import (
    Crossfall,
    CrossSectionSurface,
    PolynomialProfile,
    RoadProfiles,
    Shape,
    SurfaceCoefficients,
    SurfaceStrip,
)


class ProfileParseError(ValueError):
    """A profile record is missing a required or numeric attribute."""

    def __init__(self, message: str, *, element: str) -> None:
        self.message = message
        self.element = element
        super().__init__(f"{message} ({element})")


def parse_road_profiles(
    road: ElementTree.Element, road_path: str, revision: int
) -> RoadProfiles:
    elevation_element = _child(road, "elevationProfile")
    lateral_element = _child(road, "lateralProfile")
    lanes_element = _child(road, "lanes")

    return RoadProfiles(
        elevation=(
            _polynomials(elevation_element, "elevation", road_path)
            if elevation_element is not None
            else None
        ),
        superelevation=(
            _polynomials(lateral_element, "superelevation", road_path)
            if lateral_element is not None
            and _has_record(lateral_element, "superelevation")
            else None
        ),
        crossfall=(
            _crossfalls(lateral_element, road_path)
            if revision < 6
            and lateral_element is not None
            and _has_record(lateral_element, "crossfall")
            else None
        ),
        lane_offset=(
            _polynomials(lanes_element, "laneOffset", road_path)
            if lanes_element is not None and _has_record(lanes_element, "laneOffset")
            else None
        ),
        shape=(
            _shapes(lateral_element, road_path)
            if lateral_element is not None and _has_record(lateral_element, "shape")
            else None
        ),
        cross_section_surface=(
            _cross_section_surface(lateral_element, road_path)
            if revision >= 8 and lateral_element is not None
            else None
        ),
    )


def _polynomials(
    parent: ElementTree.Element, tag: str, road_path: str
) -> tuple[PolynomialProfile, ...]:
    return tuple(
        PolynomialProfile(
            s=_number(element, "s", road_path, tag),
            a=_number(element, "a", road_path, tag),
            b=_number(element, "b", road_path, tag),
            c=_number(element, "c", road_path, tag),
            d=_number(element, "d", road_path, tag),
            level=(
                _optional_bool(element, "level", road_path, tag)
                if tag == "superelevation"
                else None
            ),
        )
        for element in parent
        if _local_name(element.tag) == tag
    )


def _crossfalls(parent: ElementTree.Element, road_path: str) -> tuple[Crossfall, ...]:
    records: list[Crossfall] = []
    for element in parent:
        if _local_name(element.tag) != "crossfall":
            continue
        path = f"{road_path}/lateralProfile/crossfall"
        try:
            side = element.attrib["side"]
        except KeyError as error:
            raise ProfileParseError(
                "Profile record is missing required 'side' attribute.", element=path
            ) from error
        records.append(
            Crossfall(
                s=_number(element, "s", road_path, "crossfall"),
                a=_number(element, "a", road_path, "crossfall"),
                b=_number(element, "b", road_path, "crossfall"),
                c=_number(element, "c", road_path, "crossfall"),
                d=_number(element, "d", road_path, "crossfall"),
                level=_optional_bool(element, "level", road_path, "crossfall"),
                side=side,
            )
        )
    return tuple(records)


def _shapes(parent: ElementTree.Element, road_path: str) -> tuple[Shape, ...]:
    return tuple(
        Shape(
            s=_number(element, "s", road_path, "shape"),
            t=_number(element, "t", road_path, "shape"),
            a=_number(element, "a", road_path, "shape"),
            b=_number(element, "b", road_path, "shape"),
            c=_number(element, "c", road_path, "shape"),
            d=_number(element, "d", road_path, "shape"),
        )
        for element in parent
        if _local_name(element.tag) == "shape"
    )


def _cross_section_surface(
    parent: ElementTree.Element, road_path: str
) -> CrossSectionSurface | None:
    surface = _child(parent, "crossSectionSurface")
    if surface is None:
        return None
    path = f"{road_path}/lateralProfile/crossSectionSurface"
    offset = _child(surface, "tOffset")
    strips_element = _child(surface, "surfaceStrips")
    if strips_element is None:
        raise ProfileParseError(
            "Cross-section surface is missing required 'surfaceStrips' element.",
            element=path,
        )
    return CrossSectionSurface(
        t_offset=_surface_coefficients(offset, path) if offset is not None else None,
        strips=tuple(_surface_strip(strip, path) for strip in strips_element),
    )


def _surface_strip(element: ElementTree.Element, path: str) -> SurfaceStrip:
    strip_path = f"{path}/surfaceStrips/strip"
    try:
        strip_id = int(element.attrib["id"])
    except (KeyError, ValueError) as error:
        raise ProfileParseError(
            "Surface strip has a missing or invalid 'id' attribute.",
            element=strip_path,
        ) from error
    profiles = {
        name: (_surface_coefficients(child, strip_path) if child is not None else None)
        for name in ("width", "constant", "linear", "quadratic", "cubic")
        if (child := _child(element, name)) is not None
    }
    return SurfaceStrip(
        id=strip_id,
        mode=element.get("mode"),
        **profiles,
    )


def _surface_coefficients(
    element: ElementTree.Element, path: str
) -> tuple[SurfaceCoefficients, ...]:
    return tuple(
        SurfaceCoefficients(
            s=_surface_number(record, "s", path),
            a=_optional_surface_number(record, "a", path),
            b=_optional_surface_number(record, "b", path),
            c=_optional_surface_number(record, "c", path),
            d=_optional_surface_number(record, "d", path),
        )
        for record in element
        if _local_name(record.tag) == "coefficients"
    )


def _surface_number(element: ElementTree.Element, attribute: str, path: str) -> float:
    try:
        return float(element.attrib[attribute])
    except (KeyError, ValueError) as error:
        raise ProfileParseError(
            f"Profile record has a missing or invalid '{attribute}' attribute.",
            element=f"{path}/coefficients",
        ) from error


def _optional_surface_number(
    element: ElementTree.Element, attribute: str, path: str
) -> float | None:
    if attribute not in element.attrib:
        return None
    return _surface_number(element, attribute, path)


def _number(
    element: ElementTree.Element, attribute: str, road_path: str, tag: str
) -> float:
    path = f"{road_path}/{tag}"
    try:
        return float(element.attrib[attribute])
    except (KeyError, ValueError) as error:
        raise ProfileParseError(
            f"Profile record has a missing or invalid '{attribute}' attribute.",
            element=path,
        ) from error


def _optional_bool(
    element: ElementTree.Element, attribute: str, road_path: str, tag: str
) -> bool | None:
    value = element.get(attribute)
    if value is None:
        return None
    if value in {"true", "1"}:
        return True
    if value in {"false", "0"}:
        return False
    raise ProfileParseError(
        f"Profile record has an invalid '{attribute}' attribute.",
        element=f"{road_path}/{tag}",
    )


def _child(element: ElementTree.Element, tag: str) -> ElementTree.Element | None:
    return next((child for child in element if _local_name(child.tag) == tag), None)


def _has_record(element: ElementTree.Element | None, tag: str) -> bool:
    return element is not None and any(
        _local_name(child.tag) == tag for child in element
    )


def _local_name(tag: str) -> str:
    return tag.rsplit("}", maxsplit=1)[-1]
