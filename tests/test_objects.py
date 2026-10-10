"""Independently authored object fixtures for OpenDRIVE 1.9 chapter 13."""

from io import StringIO

import pytest

from pyopendrive import OpenDriveMap, OpenDriveParseError
from pyopendrive.odr.models.geometry import Arc, Line, ParamPoly3
from pyopendrive.odr.models.objects import CornerLocal, CornerRoad, CurveLocal

OBJECT = '<object id="o01" s="5" t="2" zOffset="0"'
MARKING = (
    '<marking color="white" lineLength="1" spaceLength=".1"'
    ' startOffset="0" stopOffset="0"'
)


def load(content: str, revision: int = 9):
    return OpenDriveMap.load(
        StringIO(
            '<OpenDRIVE xmlns="urn:test">'
            f'<header revMajor="1" revMinor="{revision}"/>'
            '<road id="r01" length="20"'
            f' junction="-1"><objects>{content}</objects></road></OpenDRIVE>'
        )
    )


def test_objects_and_references_with_old_and_wrapped_outlines():
    result = load(
        OBJECT
        + ' type="building" dynamic="yes" temporary="true" perpToRoad="1" width="3">'
        '<validity fromLane="1" toLane="2"/>'
        '<outline closed="false"><cornerRoad s="5" t="2" dz="0" height="1"/>'
        '<cornerRoad s="6" t="2" dz="0" height="1"/></outline>'
        '<outlines><outline id="0" outer="true"><cornerLocal id="0"'
        ' u="0" v="0" z="0" height="1"/>'
        '<cornerLocal id="1" u="1" v="1" z="0" height="1"/><markings>'
        + MARKING
        + '><cornerReference id="0"/><cornerReference id="1"/></marking></markings>'
        '</outline></outlines></object><objectReference id="o01"'
        ' s="10" t="0" orientation="none" validLength="2">'
        '<validity fromLane="-2" toLane="-1" layer="temporary"/></objectReference>'
    )
    obj = result.roads[0].objects[0]
    assert obj.id == "o01" and obj.dynamic is True and obj.width == 3
    assert obj.perpendicular_to_road is True
    assert isinstance(obj.outlines[0].corners[0], CornerRoad)
    assert isinstance(obj.outlines[1].corners[0], CornerLocal)
    assert obj.outlines[1].markings[0].corner_references == (0, 1)
    assert result.roads[0].object_references[0].valid_length == 2
    assert result.diagnostics == ()


@pytest.mark.parametrize(
    "primitive,expected",
    [
        ("<line/>", Line),
        ('<arc curvature=".3"/>', Arc),
        (
            '<paramPoly3 aU="0" bU="1" cU="2" dU="3" aV="4" bV="5"'
            ' cV="6" dV="7" pRange="normalized"/>',
            ParamPoly3,
        ),
    ],
)
def test_smooth_outline_source_parameters(primitive, expected):
    result = load(
        OBJECT
        + '><outlines><outline><curveLocal u="0" v="1" z="2" height="3" hdg=".4">'
        + primitive
        + "</curveLocal></outline></outlines></object>"
    )
    curve = result.roads[0].objects[0].outlines[0].corners[0]
    assert isinstance(curve, CurveLocal)
    assert isinstance(curve.primitive, expected)
    assert (curve.u, curve.v, curve.z, curve.height, curve.heading, curve.length) == (
        0,
        1,
        2,
        3,
        0.4,
        None,
    )
    assert result.diagnostics == ()


def test_bounding_box_markings_and_omissions():
    obj = (
        load(
            OBJECT
            + "><markings>"
            + MARKING
            + ' side="left" width=".1"/></markings></object>'
        )
        .roads[0]
        .objects[0]
    )
    assert obj.markings[0].side == "left"
    assert obj.markings[0].width == 0.1 and obj.markings[0].corner_references == ()
    assert obj.dynamic is None and obj.temporary is None and obj.outlines == ()
    assert load("").roads[0].objects == ()


@pytest.mark.parametrize(
    "content,attribute",
    [
        (OBJECT.replace('zOffset="0"', 'zOffset="inf"') + "/>", "zOffset"),
        (
            OBJECT + '><outline><cornerRoad s="0" t="0" dz="0"/></outline></object>',
            "height",
        ),
        (
            OBJECT + '><markings><marking color="white"/></markings></object>',
            "lineLength",
        ),
        (
            OBJECT
            + '><outline><curveLocal u="0" v="0" z="0" height="0"/></outline></object>',
            "Curve",
        ),
    ],
)
def test_malformed_nested_records_have_context(content, attribute):
    with pytest.raises(OpenDriveParseError, match=attribute) as error:
        load(content)
    assert "/road[@id='r01']/objects/object[@id='o01']" in error.value.element


def test_object_unknown_nested_records_and_version_mismatch():
    result = load(
        OBJECT + ' extra="x"'
        ' temporary="true"><repeat/><outlines><outline>'
        '<curveLocal u="0" v="0" z="0" height="0">'
        "<line"
        ' extra="x"><extension/></line></curveLocal>'
        '<extension id="unparsed"/></outline></outlines></object>',
        8,
    )
    codes = [d.code for d in result.diagnostics]
    assert codes.count("version-mismatch") == 2
    assert codes.count("unsupported-attribute") == 2
    assert codes.count("unsupported-element") == 3
