"""Convert signal records; retain source values without resolving references."""

import math
from xml.etree.ElementTree import Element

from pyopendrive.odr.models.opendrive import OpenDriveDiagnostic
from pyopendrive.odr.models.signals import (
    LaneValidity,
    Signal,
    SignalDependency,
    SignalLink,
    SignalReference,
)


class RoadRecordParseError(ValueError):
    def __init__(self, message: str, *, element: str) -> None:
        self.message = message
        self.element = element
        super().__init__(f"{message} ({element})")


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def children(element: Element, tag: str) -> tuple[Element, ...]:
    return tuple(child for child in element if local_name(child.tag) == tag)


def string(element: Element, name: str, path: str) -> str:
    value = element.get(name)
    if value is None:
        raise RoadRecordParseError(
            f"Missing required '{name}' attribute.", element=path
        )
    return value


def number(element: Element, name: str, path: str) -> float:
    source = string(element, name, path)
    try:
        value = float(source)
        if not math.isfinite(value):
            raise ValueError("value must be finite")
        return value
    except ValueError as error:
        raise RoadRecordParseError(
            f"Invalid '{name}' attribute.", element=path
        ) from error


def optional_number(element: Element, name: str, path: str) -> float | None:
    return number(element, name, path) if name in element.attrib else None


def integer(element: Element, name: str, path: str) -> int:
    source = string(element, name, path)
    try:
        return int(source)
    except ValueError as error:
        raise RoadRecordParseError(
            f"Invalid '{name}' attribute.", element=path
        ) from error


def boolean(element: Element, name: str, path: str) -> bool | None:
    value = element.get(name)
    if value is None:
        return None
    values = {"true": True, "1": True, "false": False, "0": False}
    if value not in values:
        raise RoadRecordParseError(f"Invalid '{name}' attribute.", element=path)
    return values[value]


def yes_no(element: Element, path: str, *, required: bool = False) -> bool | None:
    value = string(element, "dynamic", path) if required else element.get("dynamic")
    if value is None:
        return None
    if value not in {"yes", "no"}:
        raise RoadRecordParseError("Invalid 'dynamic' attribute.", element=path)
    return value == "yes"


def parse_validity(element: Element, path: str) -> tuple[LaneValidity, ...]:
    return tuple(
        LaneValidity(
            from_lane=integer(child, "fromLane", f"{path}/validity"),
            to_lane=integer(child, "toLane", f"{path}/validity"),
            layer=child.get("layer"),
        )
        for child in children(element, "validity")
    )


def parse_signals(
    road: Element, path: str
) -> tuple[tuple[Signal, ...], tuple[SignalReference, ...]]:
    signals: list[Signal] = []
    references: list[SignalReference] = []
    for container in children(road, "signals"):
        for element in container:
            name = local_name(element.tag)
            record_path = f"{path}/signals/{name}[@id='{element.get('id', '?')}']"
            if name == "signalReference":
                references.append(
                    SignalReference(
                        id=string(element, "id", record_path),
                        s=number(element, "s", record_path),
                        t=number(element, "t", record_path),
                        orientation=string(element, "orientation", record_path),
                        validity=parse_validity(element, record_path),
                    )
                )
            elif name == "signal":
                signals.append(
                    Signal(
                        id=string(element, "id", record_path),
                        s=number(element, "s", record_path),
                        t=number(element, "t", record_path),
                        z_offset=number(element, "zOffset", record_path),
                        dynamic=yes_no(element, record_path, required=True),
                        orientation=string(element, "orientation", record_path),
                        type=string(element, "type", record_path),
                        subtype=string(element, "subtype", record_path),
                        name=element.get("name"),
                        country=element.get("country"),
                        country_revision=element.get("countryRevision"),
                        unit=element.get("unit"),
                        text=element.get("text"),
                        temporary=boolean(element, "temporary", record_path),
                        invalidated=boolean(element, "invalidated", record_path),
                        validity=parse_validity(element, record_path),
                        dependencies=tuple(
                            SignalDependency(
                                id=string(child, "id", f"{record_path}/dependency"),
                                type=child.get("type"),
                            )
                            for child in children(element, "dependency")
                        ),
                        references=tuple(
                            SignalLink(
                                element_id=string(
                                    child, "elementId", f"{record_path}/reference"
                                ),
                                element_type=string(
                                    child, "elementType", f"{record_path}/reference"
                                ),
                                type=child.get("type"),
                            )
                            for child in children(element, "reference")
                        ),
                        **{
                            key: optional_number(element, attr, record_path)
                            for key, attr in (
                                ("value", "value"),
                                ("height", "height"),
                                ("width", "width"),
                                ("length", "length"),
                                ("h_offset", "hOffset"),
                                ("pitch", "pitch"),
                                ("roll", "roll"),
                            )
                        },
                    )
                )
    return tuple(signals), tuple(references)


SIGNAL_RULES = {
    "signals": (set(), {"signal", "signalReference"}),
    "signal": (
        {
            "id",
            "s",
            "t",
            "zOffset",
            "dynamic",
            "orientation",
            "type",
            "subtype",
            "name",
            "country",
            "countryRevision",
            "value",
            "unit",
            "text",
            "height",
            "width",
            "length",
            "hOffset",
            "pitch",
            "roll",
            "temporary",
            "invalidated",
        },
        {"validity", "dependency", "reference"},
    ),
    "signalReference": ({"id", "s", "t", "orientation"}, {"validity"}),
    "validity": ({"fromLane", "toLane", "layer"}, set()),
    "dependency": ({"id", "type"}, set()),
    "reference": ({"elementId", "elementType", "type"}, set()),
}


def record_diagnostics(
    element: Element,
    path: str,
    rules: dict[str, tuple[set[str], set[str]]],
    revision: int,
) -> tuple[OpenDriveDiagnostic, ...]:
    """Report every unsupported attribute/child in the supported record tree."""
    diagnostics: list[OpenDriveDiagnostic] = []
    name = local_name(element.tag)
    attributes, allowed = rules[name]
    for attribute in element.attrib:
        if attribute not in attributes:
            diagnostics.append(
                OpenDriveDiagnostic(
                    code="unsupported-attribute",
                    message=f"Attribute '{attribute}' is not currently parsed.",
                    element=path,
                )
            )
        introduced = 9 if attribute in {"temporary", "invalidated", "layer"} else None
        if name == "signal" and attribute == "length":
            introduced = 8
        if name == "object" and attribute == "perpToRoad":
            introduced = 7
        if introduced is not None and revision < introduced:
            diagnostics.append(
                OpenDriveDiagnostic(
                    code="version-mismatch",
                    message=(
                        f"Attribute '{attribute}' was introduced "
                        f"in OpenDRIVE 1.{introduced}."
                    ),
                    element=path,
                )
            )
    if name == "curveLocal" and revision < 9:
        diagnostics.append(
            OpenDriveDiagnostic(
                code="version-mismatch",
                message="Element 'curveLocal' was introduced in OpenDRIVE 1.9.",
                element=path,
            )
        )
    for child in element:
        child_name = local_name(child.tag)
        child_path = f"{path}/{child_name}"
        if child_name not in allowed:
            diagnostics.append(
                OpenDriveDiagnostic(
                    code="unsupported-element",
                    message=f"Element '{child_name}' is not currently parsed.",
                    element=child_path,
                )
            )
        else:
            diagnostics.extend(record_diagnostics(child, child_path, rules, revision))
    return tuple(diagnostics)
