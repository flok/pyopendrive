"""Authored parser fixtures are evidence of behavior, not schema conformance."""

from io import StringIO
from pathlib import Path

import pytest

from pyopendrive import (
    LanePolynomial,
    Line,
    OpenDriveDiagnostic,
    OpenDriveMap,
    OpenDriveParseError,
    OpenDriveVersion,
    PolynomialProfile,
)

FIXTURES = Path(__file__).parent / "fixtures"
ROAD_PATH = "/OpenDRIVE/road[@id='001']"
SECTION_PATH = f"{ROAD_PATH}/lanes[0]/laneSection[0]"
LANE_PATH = f"{SECTION_PATH}/right/lane[0]"


@pytest.mark.parametrize("minor", range(4, 10))
def test_revision_fixture_preserves_common_road_and_lane_values(minor: int) -> None:
    road_map = OpenDriveMap.load(FIXTURES / "revisions" / f"1.{minor}" / "basic.xodr")

    assert road_map.format_version == OpenDriveVersion(1, minor)
    assert road_map.header.name == f"Authored parser fixture 1.{minor}"
    assert road_map.header.east == 20
    road = road_map.roads[0]
    assert (road.id, road.name, road.length, road.junction) == (
        "001",
        "Straight road",
        20,
        "-1",
    )
    assert (road.types[0].type, road.types[0].speed.value) == ("rural", 40)
    geometry = road.plan_view[0]
    assert isinstance(geometry.primitive, Line)
    assert (geometry.s, geometry.x, geometry.y, geometry.heading, geometry.length) == (
        0,
        0,
        0,
        0,
        20,
    )
    assert road.profiles.elevation == (PolynomialProfile(0, 1, 0.01, 0, 0),)
    assert road.profiles.lane_offset == (PolynomialProfile(0, 0.25, 0, 0, 0),)
    section = road.lane_layers[0].sections[0]
    assert section.lanes.order == ("center", "right")
    assert section.lanes.center[0].id == 0
    lane = section.lanes.right[0]
    assert (lane.id, lane.lane_type, lane.level) == (-1, "driving", False)
    assert lane.widths == (LanePolynomial(0, 3.5, 0, 0, 0),)
    assert (lane.speeds[0].max, lane.speeds[0].unit) == (10, "m/s")
    assert (lane.road_marks[0].mark_type, lane.road_marks[0].width) == ("solid", 0.12)
    assert road_map.diagnostics == ()


@pytest.mark.parametrize(
    ("filename", "message", "element"),
    [
        ("bad-lane-id.xodr", "Invalid integer 'id'", LANE_PATH),
        ("bad-lane-bool.xodr", "Invalid boolean 'level'", LANE_PATH),
        (
            "missing-width-coefficient.xodr",
            "Missing required 'd'",
            f"{LANE_PATH}/width[0]",
        ),
        ("missing-center.xodr", "exactly one center group", SECTION_PATH),
        ("duplicate-center.xodr", "exactly one center group", SECTION_PATH),
        ("missing-rule-value.xodr", "Missing required 'value'", f"{LANE_PATH}/rule[0]"),
        (
            "missing-road-id.xodr",
            "Road has a missing or invalid",
            "/OpenDRIVE/road[@id='?']",
        ),
        ("malformed-xml.xodr", "Invalid XML", None),
    ],
)
def test_invalid_fixture_reports_the_failed_field_and_element(
    filename: str, message: str, element: str | None
) -> None:
    with pytest.raises(OpenDriveParseError, match=message) as caught:
        OpenDriveMap.load(FIXTURES / "invalid" / filename)

    assert caught.value.element == element


@pytest.mark.parametrize("minor", [8, 9])
def test_lane_rule_uses_required_value_attribute(minor: int) -> None:
    road_map = OpenDriveMap.load(
        StringIO(
            f'<OpenDRIVE><header revMajor="1" revMinor="{minor}"/>'
            '<road id="1" length="20" junction="-1"><lanes><laneSection s="0">'
            '<center><lane id="0"/></center><right><lane id="-1">'
            '<rule sOffset="2" value="car pool">ignored element text</rule>'
            '<rule sOffset="4" value=""/></lane></right>'
            "</laneSection></lanes></road></OpenDRIVE>"
        )
    )

    rules = road_map.roads[0].lane_layers[0].sections[0].lanes.right[0].rules
    assert [(rule.s_offset, rule.value) for rule in rules] == [(2, "car pool"), (4, "")]
    assert road_map.diagnostics == ()


def test_lane_extensions_are_reported_in_document_order() -> None:
    road_map = OpenDriveMap.load(
        FIXTURES / "revisions" / "1.9" / "lane-extensions.xodr"
    )

    road = road_map.roads[0]
    assert road.lane_layers[0].sections[0].lanes.right[0].widths[0].a == 3.5
    path = f"{ROAD_PATH}/lanes"
    lane_path = f"{path}/laneSection/right/lane"
    assert road_map.diagnostics == (
        OpenDriveDiagnostic(
            "unsupported-attribute", "Attribute 'vendor' is not currently parsed.", path
        ),
        OpenDriveDiagnostic(
            "unsupported-element",
            "Element 'extension' is not currently parsed.",
            f"{path}/laneOffset/extension",
        ),
        OpenDriveDiagnostic(
            "unsupported-attribute",
            "Attribute 'vendor' is not currently parsed.",
            f"{path}/laneSection/right",
        ),
        OpenDriveDiagnostic(
            "unsupported-attribute",
            "Attribute '{urn:vendor}type' is not currently parsed.",
            lane_path,
        ),
        OpenDriveDiagnostic(
            "unsupported-element",
            "Element 'userData' is not currently parsed.",
            f"{lane_path}/userData",
        ),
        OpenDriveDiagnostic(
            "unsupported-attribute",
            "Attribute 'vendor' is not currently parsed.",
            f"{lane_path}/link/successor",
        ),
        OpenDriveDiagnostic(
            "unsupported-element",
            "Element 'quality' is not currently parsed.",
            f"{lane_path}/width/quality",
        ),
        OpenDriveDiagnostic(
            "unsupported-element",
            "Element 'explicit' is not currently parsed.",
            f"{lane_path}/roadMark/explicit",
        ),
        OpenDriveDiagnostic(
            "unsupported-element",
            "Element 'sway' is not currently parsed.",
            f"{lane_path}/roadMark/sway",
        ),
        OpenDriveDiagnostic(
            "unsupported-attribute",
            "Attribute 'color' is not currently parsed.",
            f"{lane_path}/roadMark/type/line",
        ),
    )
