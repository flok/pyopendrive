"""Behavior checks for lane layer parsing."""

from xml.etree import ElementTree

import pytest

from pyopendrive import Lane, LanePolynomial
from pyopendrive.odr.parser.lanes import LaneParseError, parse_lane_layers


def test_parse_lane_layers_and_properties_in_document_order() -> None:
    road = ElementTree.fromstring(
        """<road id="r1">
          <lanes layer="permanent">
            <laneSection s="0">
              <right><lane id="-1" type="driving" level="false">
                <link><predecessor id="-2" layer="temporary"/>
                      <successor id="-1" layer="permanent"/></link>
                <width sOffset="0" a="3.5" b="0" c="0" d="0"/>
                <material sOffset="0" friction="0" roughness="0"/>
                <speed sOffset="0" max="0" unit="m/s"/>
                <access sOffset="0" restriction="pedestrian" rule="deny"/>
                <height sOffset="0" inner="0" outer="0"/>
                <rule sOffset="0">no stopping</rule>
                <roadMark sOffset="0" type="solid" color="white">
                  <type name="solid" width="0.12">
                    <line sOffset="0" length="3" space="0" width="0.12"/>
                  </type>
                </roadMark>
              </lane></right>
              <center><lane id="0" type="none"/></center>
              <left><lane id="1" type="driving" roadWorks="true"/></left>
            </laneSection>
            <laneSection s="10" singleSide="false">
              <center><lane id="0"/></center>
              <left><lane id="1"><border sOffset="0" a="4" b="0" c="0" d="0"/>
                <border sOffset="5" a="5" b="0" c="0" d="0"/></lane></left>
            </laneSection>
          </lanes>
          <lanes layer="temporary"><laneSection s="2" length="4">
            <center><lane id="0"/></center>
            <right><lane id="-1"><link>
              <successor id="-2" layer="permanent"/>
            </link></lane></right>
          </laneSection></lanes>
        </road>"""
    )

    permanent, temporary = parse_lane_layers(road)

    assert (permanent.layer, temporary.layer) == ("permanent", "temporary")
    assert [section.s for section in permanent.sections] == [0, 10]
    first = permanent.sections[0]
    assert first.lanes.order == ("right", "center", "left")
    lane = first.lanes.right[0]
    assert lane.id == -1 and lane.level is False
    assert lane.widths == (LanePolynomial(0, 3.5, 0, 0, 0),)
    assert lane.links.predecessors[0].layer == "temporary"
    assert lane.materials[0].friction == 0
    assert lane.speeds[0].max == 0
    assert lane.heights[0].inner == 0 and lane.heights[0].outer == 0
    assert lane.road_marks[0].type_definition.lines[0].space == 0
    assert first.lanes.left[0].road_works is True
    assert permanent.sections[1].lanes.left[0].borders[1].a == 5
    assert permanent.sections[1].single_side is False
    assert temporary.sections[0].length == 4
    assert temporary.sections[0].lanes.left is None
    assert temporary.sections[0].lanes.right[0].links.successors[0].layer == "permanent"


@pytest.mark.parametrize(
    ("xml", "message", "element"),
    [
        (
            '<road id="7"><lanes><laneSection><center><lane id="0"/>'
            "</center></laneSection></lanes></road>",
            "Missing required 's'",
            "/OpenDRIVE/road[@id='7']/lanes[0]/laneSection[0]",
        ),
        (
            '<road id="7"><lanes><laneSection s="0"><center>'
            '<lane id="x"/></center></laneSection></lanes></road>',
            "Invalid integer 'id'",
            "/OpenDRIVE/road[@id='7']/lanes[0]/laneSection[0]/center/lane[0]",
        ),
    ],
)
def test_invalid_lane_values_have_context(xml: str, message: str, element: str) -> None:
    with pytest.raises(LaneParseError, match=message) as caught:
        parse_lane_layers(ElementTree.fromstring(xml))

    assert caught.value.element == element


def test_absent_and_explicit_zero_lane_properties_are_distinct() -> None:
    road = ElementTree.fromstring(
        '<road><lanes><laneSection s="0"><center><lane id="0"/>'
        '</center><right><lane id="-1"><speed sOffset="0"/></lane>'
        '<lane id="-2"><speed sOffset="0" max="0"/></lane></right>'
        "</laneSection></lanes></road>"
    )

    lanes = parse_lane_layers(road)[0].sections[0].lanes.right

    assert lanes[0].speeds[0].max is None
    assert lanes[1].speeds[0].max == 0
    assert isinstance(lanes[0], Lane)
