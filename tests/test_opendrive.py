"""Small examples of testing the public loading API."""

from io import BytesIO, StringIO

import pytest

from pyopendrive import (
    DefaultRegulations,
    License,
    Offset,
    OpenDrive,
    OpenDriveDiagnostic,
    OpenDriveMap,
    OpenDriveParseError,
    OpenDriveVersion,
    RegulationSemantic,
    RoadRegulation,
    SignalRegulation,
)

MINIMAL_MAP = b"""\
<OpenDRIVE>
  <header revMajor="1" revMinor="9" name="Showcase"/>
  <road id="1" length="12.5" junction="-1" name="Example road"/>
</OpenDRIVE>
"""


def test_load_minimal_map() -> None:
    source = StringIO(MINIMAL_MAP.decode())

    road_map = OpenDriveMap.load(source)

    assert road_map.format_version == OpenDriveVersion(major=1, minor=9)
    assert road_map.header.name == "Showcase"
    assert len(road_map.roads) == 1
    assert road_map.roads[0].name == "Example road"
    assert road_map.diagnostics == ()
    assert not source.closed


# Fixtures cover header constructs described in ASAM OpenDRIVE sections 6.4 and 8.5.
@pytest.mark.parametrize("revision", [(1, 4), (1, 5), (1, 6), (1, 7), (1, 8), (1, 9)])
def test_header_metadata_is_separate_from_format_revision(
    revision: tuple[int, int],
) -> None:
    major, minor = revision
    source = StringIO(
        f'<OpenDRIVE><header revMajor="{major}" revMinor="{minor}" '
        'name="Network" north="20" south="-20" east="10" west="-10">'
        "<geoReference><![CDATA[+proj=utm +zone=32]]></geoReference>"
        '<offset x="1.5" y="-2" z="3" hdg="0.25"/></header></OpenDRIVE>'
    )

    road_map = OpenDriveMap.load(source)

    assert road_map.format_version == OpenDriveVersion(major, minor)
    assert road_map.header.north == 20
    assert road_map.header.south == -20
    assert road_map.header.east == 10
    assert road_map.header.west == -10
    assert road_map.header.geo_reference == "+proj=utm +zone=32"
    assert road_map.header.offset == Offset(1.5, -2, 3, 0.25)
    assert road_map.diagnostics == ()


@pytest.mark.parametrize("minor", [8, 9])
def test_header_license_and_default_regulations(minor: int) -> None:
    source = StringIO(
        f'<OpenDRIVE><header revMajor="1" revMinor="{minor}">'
        '<license name="CC0" resource="https://example.test/license" '
        'spdxid="CC0-1.0" text="Public domain"/>'
        '<defaultRegulations><roadRegulations type="rural"><semantics>'
        '<speed type="maximum" value="80" unit="km/h"/>'
        '</semantics></roadRegulations><signalRegulations type="stop" '
        'subType="-1"><semantics><priority type="stop"/></semantics>'
        "</signalRegulations></defaultRegulations></header></OpenDRIVE>"
    )

    header = OpenDriveMap.load(source).header

    assert header.license == License(
        "CC0", "https://example.test/license", "CC0-1.0", "Public domain"
    )
    assert header.default_regulations == DefaultRegulations(
        road=(
            RoadRegulation(
                "rural",
                (
                    RegulationSemantic(
                        "speed",
                        (("type", "maximum"), ("value", "80"), ("unit", "km/h")),
                    ),
                ),
            ),
        ),
        signals=(
            SignalRegulation(
                "stop", "-1", (RegulationSemantic("priority", (("type", "stop"),)),)
            ),
        ),
    )


@pytest.mark.parametrize(
    ("header_children", "attribute", "element"),
    [
        ('<offset x="1" y="2" z="3"/>', "hdg", "/OpenDRIVE/header/offset"),
        ('<offset x="bad" y="2" z="3" hdg="0"/>', "x", "/OpenDRIVE/header/offset"),
        (
            '<license resource="https://example.test"/>',
            "name",
            "/OpenDRIVE/header/license",
        ),
        (
            "<defaultRegulations><roadRegulations/></defaultRegulations>",
            "type",
            "/OpenDRIVE/header/defaultRegulations/roadRegulations",
        ),
    ],
)
def test_invalid_header_metadata_reports_element_and_attribute(
    header_children: str, attribute: str, element: str
) -> None:
    xml = (
        '<OpenDRIVE><header revMajor="1" revMinor="9">'
        f"{header_children}</header></OpenDRIVE>"
    )

    with pytest.raises(OpenDriveParseError, match=attribute) as caught:
        OpenDriveMap.load(StringIO(xml))

    assert caught.value.element == element


def test_load_path_and_binary_stream(tmp_path) -> None:
    path = tmp_path / "map.xodr"
    path.write_bytes(MINIMAL_MAP)

    assert OpenDriveMap.load(path).roads[0].id == "1"

    stream = BytesIO(MINIMAL_MAP)
    assert OpenDriveMap.load(stream).roads[0].id == "1"
    assert not stream.closed


def test_legacy_loader_delegates_to_map() -> None:
    assert OpenDrive.load(BytesIO(MINIMAL_MAP)) == OpenDriveMap.load(
        BytesIO(MINIMAL_MAP)
    )


@pytest.mark.parametrize(
    ("xml", "message", "element"),
    [
        ("<OpenDRIVE>", "Invalid XML", None),
        ("<map/>", "Root element must be", "/map"),
        ("<OpenDRIVE/>", "missing its header", "/OpenDRIVE"),
        (
            '<OpenDRIVE><header revMajor="one" revMinor="9"/></OpenDRIVE>',
            "missing or invalid 'revMajor'",
            "/OpenDRIVE/header",
        ),
        (
            '<OpenDRIVE><header revMajor="1" revMinor="9"/>'
            '<road length="12.5" junction="-1"/></OpenDRIVE>',
            "Road has a missing or invalid attribute",
            "/OpenDRIVE/road[@id='?']",
        ),
    ],
)
def test_parse_errors_have_stable_context(
    xml: str, message: str, element: str | None
) -> None:
    with pytest.raises(OpenDriveParseError, match=message) as caught:
        OpenDriveMap.load(StringIO(xml))

    assert message in caught.value.message
    assert caught.value.element == element


def test_unsupported_content_produces_structured_diagnostics() -> None:
    source = StringIO(
        """\
<OpenDRIVE extension="value">
  <header revMajor="1" revMinor="9" unexpected="5"><geoReference/></header>
  <road id="1" length="12.5" junction="-1"><planView/></road>
  <controller id="7"/>
</OpenDRIVE>
"""
    )

    diagnostics = OpenDriveMap.load(source).diagnostics

    assert diagnostics == (
        OpenDriveDiagnostic(
            "unsupported-attribute",
            "Attribute 'extension' is not currently parsed.",
            "/OpenDRIVE",
        ),
        OpenDriveDiagnostic(
            "unsupported-attribute",
            "Attribute 'unexpected' is not currently parsed.",
            "/OpenDRIVE/header",
        ),
        OpenDriveDiagnostic(
            "unsupported-element",
            "Element 'controller' is not currently parsed.",
            "/OpenDRIVE/controller",
        ),
    )


def test_parses_road_types_and_links() -> None:
    road_map = OpenDriveMap.load(
        StringIO(
            """\
<OpenDRIVE>
  <header revMajor="1" revMinor="9"/>
  <road id="01" name="Main" length="12.5" junction="-1" rule="RHT">
    <link>
      <predecessor elementType="junction" elementId="02"/>
      <successor elementType="road" elementId="3" contactPoint="start"/>
    </link>
    <type s="0" type="town" country="OpenDRIVE">
      <speed max="13.9" unit="m/s"/>
    </type>
    <type s="8" type="rural"><speed max="no limit"/></type>
  </road>
</OpenDRIVE>
"""
        )
    )

    road = road_map.roads[0]
    assert road.id == "01"
    assert road.rule == "RHT"
    assert road.predecessor.element_id == "02"
    assert road.predecessor.contact_point is None
    assert road.successor.element_id == "3"
    assert road.successor.contact_point == "start"
    assert road.types[0].speed.value == 13.9
    assert road.types[0].speed.unit == "m/s"
    assert road.types[1].speed.value == "no limit"


def test_load_attaches_lane_layers_and_reports_unknown_lane_elements() -> None:
    road_map = OpenDriveMap.load(
        StringIO(
            '<OpenDRIVE><header revMajor="1" revMinor="9"/>'
            '<road id="1" length="10" junction="-1"><lanes layer="permanent">'
            '<laneSection s="0"><center><lane id="0"/></center></laneSection>'
            "<unexpected/></lanes></road></OpenDRIVE>"
        )
    )

    assert road_map.roads[0].lane_layers[0].layer == "permanent"
    assert road_map.roads[0].lane_layers[0].sections[0].lanes.center[0].id == 0
    assert road_map.diagnostics == (
        OpenDriveDiagnostic(
            "unsupported-element",
            "Element 'unexpected' is not currently parsed.",
            "/OpenDRIVE/road[@id='1']/lanes/unexpected",
        ),
    )


def test_invalid_road_type_reports_context() -> None:
    with pytest.raises(OpenDriveParseError, match="Road type") as caught:
        OpenDriveMap.load(
            StringIO(
                '<OpenDRIVE><header revMajor="1" revMinor="9"/>'
                '<road id="1" length="1" junction="-1">'
                '<type s="bad" type="town"/></road></OpenDRIVE>'
            )
        )

    assert caught.value.element == "/OpenDRIVE/road[@id='1']/type"
