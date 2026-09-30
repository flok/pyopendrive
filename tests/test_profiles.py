"""Behavior checks for road elevation and lateral profiles."""

from io import StringIO

import pytest

from pyopendrive import OpenDriveMap, OpenDriveParseError


def _load(profile_xml: str, revision: int = 9):
    return _load_map(profile_xml, revision).roads[0]


def _load_map(profile_xml: str, revision: int = 9) -> OpenDriveMap:
    return OpenDriveMap.load(
        StringIO(
            f'<OpenDRIVE><header revMajor="1" revMinor="{revision}"/>'
            f'<road id="r1" length="100" junction="-1">{profile_xml}</road>'
            "</OpenDRIVE>"
        )
    )


def test_profiles_preserve_records_zeros_and_absence() -> None:
    road = _load(
        """<elevationProfile>
             <elevation s="0" a="0" b="0" c="0" d="0"/>
             <elevation s="50" a="2.5" b="0" c="0" d="0"/>
           </elevationProfile>
           <lateralProfile>
             <superelevation s="0" a="0" b="0" c="0" d="0" level="true"/>
             <shape s="0" t="-4" a="0" b="0" c="0" d="0"/>
             <shape s="0" t="4" a="0" b="0" c="0" d="0"/>
           </lateralProfile>
           <lanes><laneOffset s="0" a="0" b="0" c="0" d="0"/></lanes>"""
    )

    assert road.profiles.elevation[0].a == 0
    assert [record.s for record in road.profiles.elevation] == [0, 50]
    assert len(road.profiles.superelevation) == 1
    assert road.profiles.superelevation[0].level is True
    assert [record.t for record in road.profiles.shape] == [-4, 4]
    assert road.profiles.lane_offset[0].a == 0
    assert road.profiles.crossfall is None
    assert _load("").profiles.elevation is None
    assert _load("<elevationProfile/>").profiles.elevation == ()


def test_crossfall_legacy_and_cross_section_surface() -> None:
    legacy = _load_map(
        '<lateralProfile><crossfall s="0" a="0" b="0" c="0" '
        'd="0" side="both"/></lateralProfile>',
        revision=5,
    )
    assert legacy.roads[0].profiles.crossfall[0].side == "both"
    assert legacy.diagnostics == ()

    later_crossfall = _load_map(
        '<lateralProfile><crossfall s="0" a="0" b="0" c="0" '
        'd="0" side="both"/></lateralProfile>',
        revision=6,
    )
    assert later_crossfall.roads[0].profiles.crossfall is None
    assert later_crossfall.diagnostics[0].code == "unsupported-element"

    modern_crossfall = _load_map(
        '<lateralProfile><crossfall s="0" a="0" b="0" c="0" '
        'd="0" side="both"/></lateralProfile>'
    )
    assert modern_crossfall.roads[0].profiles.crossfall is None
    assert modern_crossfall.diagnostics[0].code == "unsupported-element"

    modern = _load_map(
        """<lateralProfile><crossSectionSurface>
             <tOffset><coefficients s="0" a="0"/></tOffset>
             <surfaceStrips><strip id="1"><constant>
               <coefficients s="0" a="0" b="0" c="0" d="0"/>
             </constant></strip></surfaceStrips>
           </crossSectionSurface></lateralProfile>"""
    )
    road = modern.roads[0]
    surface = road.profiles.cross_section_surface
    assert surface.strips[0].constant[0].a == 0
    assert surface.strips[0].constant[0].b == 0
    assert surface.strips[0].width is None
    assert surface.t_offset[0].a == 0
    assert surface.t_offset[0].b is None
    assert modern.diagnostics == ()


def test_profile_parse_error_has_road_and_element_context() -> None:
    with pytest.raises(OpenDriveParseError) as caught:
        _load('<elevationProfile><elevation s="0" a="0"/></elevationProfile>')

    assert caught.value.element == "/OpenDRIVE/road[@id='r1']/elevation"
    assert "missing or invalid 'b'" in caught.value.message
