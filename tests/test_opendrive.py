"""Small examples of testing the public loading API."""

from io import BytesIO, StringIO

import pytest

from pyopendrive import (
    OpenDrive,
    OpenDriveDiagnostic,
    OpenDriveMap,
    OpenDriveParseError,
    OpenDriveVersion,
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
  <header revMajor="1" revMinor="9" north="5"><geoReference/></header>
  <road id="1" length="12.5" junction="-1" rule="RHT"><planView/></road>
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
            "Attribute 'north' is not currently parsed.",
            "/OpenDRIVE/header",
        ),
        OpenDriveDiagnostic(
            "unsupported-element",
            "Element 'geoReference' is not currently parsed.",
            "/OpenDRIVE/header/geoReference",
        ),
        OpenDriveDiagnostic(
            "unsupported-attribute",
            "Attribute 'rule' is not currently parsed.",
            "/OpenDRIVE/road[@id='1']",
        ),
        OpenDriveDiagnostic(
            "unsupported-element",
            "Element 'planView' is not currently parsed.",
            "/OpenDRIVE/road[@id='1']/planView",
        ),
        OpenDriveDiagnostic(
            "unsupported-element",
            "Element 'controller' is not currently parsed.",
            "/OpenDRIVE/controller",
        ),
    )
