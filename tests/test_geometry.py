"""Behavior checks for parsed reference-line geometry."""

from io import StringIO

import pytest

from pyopendrive import (
    Arc,
    GeometrySegment,
    Line,
    OpenDriveMap,
    OpenDriveParseError,
    ParamPoly3,
    Poly3,
    Spiral,
)


def test_plan_view_preserves_order_and_primitive_parameters() -> None:
    source = StringIO(
        """\
<OpenDRIVE>
  <header revMajor="1" revMinor="9"/>
  <road id="R1" length="55" junction="-1">
    <planView>
      <geometry s="0" x="0" y="1" hdg="0.5" length="10">
        <line/>
      </geometry>
      <geometry s="10" x="1" y="2" hdg="0.6" length="11">
        <arc curvature="0.02"/>
      </geometry>
      <geometry s="21" x="2" y="3" hdg="0.7" length="12">
        <spiral curvStart="0.01" curvEnd="0.03"/>
      </geometry>
      <geometry s="33" x="3" y="4" hdg="0.8" length="13">
        <poly3 a="1" b="2" c="3" d="4"/>
      </geometry>
      <geometry s="46" x="4" y="5" hdg="0.9" length="9">
        <paramPoly3 aU="1" bU="2" cU="3" dU="4"
                    aV="5" bV="6" cV="7" dV="8" pRange="arcLength"/>
      </geometry>
    </planView>
  </road>
</OpenDRIVE>
"""
    )

    segments = OpenDriveMap.load(source).roads[0].plan_view

    assert [segment.s for segment in segments] == [0, 10, 21, 33, 46]
    assert all(isinstance(segment, GeometrySegment) for segment in segments)
    assert [segment.primitive for segment in segments] == [
        Line(),
        Arc(0.02),
        Spiral(0.01, 0.03),
        Poly3(1, 2, 3, 4),
        ParamPoly3(1, 2, 3, 4, 5, 6, 7, 8, "arcLength"),
    ]
    assert (segments[0].x, segments[0].y, segments[0].heading, segments[0].length) == (
        0,
        1,
        0.5,
        10,
    )


def test_geometry_parse_error_has_road_and_segment_context() -> None:
    source = StringIO(
        '<OpenDRIVE><header revMajor="1" revMinor="9"/>'
        '<road id="R1" length="1" junction="-1"><planView>'
        '<geometry s="0" x="0" y="0" hdg="0" length="1">'
        "<arc/></geometry></planView></road></OpenDRIVE>"
    )

    with pytest.raises(OpenDriveParseError, match="curvature") as caught:
        OpenDriveMap.load(source)

    assert caught.value.element == "/OpenDRIVE/road[@id='R1']/planView/geometry[1]"
