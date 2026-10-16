"""Independently authored topology fixtures; no ASAM artifacts are redistributed."""

from dataclasses import FrozenInstanceError
from io import StringIO

import pytest

from pyopendrive import OpenDriveMap, OpenDriveParseError, validate_junctions


def load(content: str, namespace: str = "") -> OpenDriveMap:
    return OpenDriveMap.load(
        StringIO(
            f'<OpenDRIVE {namespace}><header revMajor="1" revMinor="9"/>'
            f"{content}</OpenDRIVE>"
        )
    )


@pytest.mark.parametrize("namespace", ["", 'xmlns="urn:opendrive"'])
def test_junction_network_values_and_order(namespace: str) -> None:
    road_map = load(
        """
        <junction id="junction-a" name="Intersection">
          <connection id="c2" incomingRoad="001"
                      connectingRoad="002" contactPoint="end">
            <laneLink from="-2" to="1"/>
            <laneLink from="-1" to="2"/>
          </connection>
          <connection id="c1" incomingRoad="003"
                      connectingRoad="004" contactPoint="start"/>
          <priority high="001" low="003"/>
          <controller id="lights" type="application-specific" sequence="0"/>
        </junction>
        <junction id="direct" type="direct">
          <connection id="d" incomingRoad="001" linkedRoad="005" contactPoint="start">
            <laneLink from="-1" to="-3" overlapZone="12.5"/>
          </connection>
        </junction>
        <junctionGroup id="g" type="roundabout" name="Group">
          <junctionReference junction="direct"/>
          <junctionReference junction="junction-a"/>
        </junctionGroup>
        <controller id="lights" name="Traffic lights" sequence="2">
          <control signalId="signal-2" type="custom"/>
          <control signalId="signal-1"/>
        </controller>
        """,
        namespace,
    )
    junction, direct = road_map.junctions
    assert junction.id == "junction-a"
    assert junction.type is None
    assert junction.name == "Intersection"
    assert [connection.id for connection in junction.connections] == ["c2", "c1"]
    connection = junction.connections[0]
    assert (connection.incoming_road, connection.connecting_road) == ("001", "002")
    assert connection.contact_point == "end"
    assert [(link.from_lane, link.to_lane) for link in connection.lane_links] == [
        (-2, 1),
        (-1, 2),
    ]
    assert connection.lane_links[0].overlap_zone is None
    assert (junction.priorities[0].high, junction.priorities[0].low) == ("001", "003")
    assert junction.controllers[0].sequence == 0
    assert junction.controllers[0].type == "application-specific"
    assert direct.connections[0].linked_road == "005"
    assert direct.connections[0].connecting_road is None
    assert direct.connections[0].lane_links[0].overlap_zone == 12.5
    group = road_map.junction_groups[0]
    assert (group.id, group.type, group.name) == ("g", "roundabout", "Group")
    assert [ref.junction for ref in group.junction_references] == [
        "direct",
        "junction-a",
    ]
    controller = road_map.controllers[0]
    assert (controller.id, controller.name, controller.sequence) == (
        "lights",
        "Traffic lights",
        2,
    )
    assert [control.signal_id for control in controller.controls] == [
        "signal-2",
        "signal-1",
    ]
    assert controller.controls[0].type == "custom"
    assert controller.controls[1].type is None
    assert road_map.diagnostics == ()
    with pytest.raises(FrozenInstanceError):
        junction.id = "changed"


def test_virtual_connections_and_crossing_sections() -> None:
    road_map = load(
        """
        <junction id="v" type="virtual" mainRoad="r"
                  orientation="+" sStart="10" sEnd="20">
          <connection id="regular" connectingRoad="branch"/>
          <connection id="virtual" type="virtual">
            <predecessor elementType="road" elementId="r" elementS="10" elementDir="+"/>
            <successor elementType="road" elementId="s" contactPoint="end"/>
            <laneLink from="-1" to="1"/>
          </connection>
        </junction>
        <junction id="x" type="crossing">
          <roadSection id="s1" roadId="r" sStart="0.5" sEnd="20.25"/>
          <roadSection id="s2" roadId="rail" sStart="100" sEnd="101"/>
        </junction>
        """
    )
    virtual, crossing = road_map.junctions
    assert (virtual.main_road, virtual.orientation, virtual.s_start, virtual.s_end) == (
        "r",
        "+",
        10,
        20,
    )
    connection = virtual.connections[1]
    assert connection.type == "virtual"
    assert connection.predecessor.element_s == 10
    assert connection.predecessor.element_dir == "+"
    assert connection.successor.contact_point == "end"
    assert connection.successor.element_s is None
    assert [(s.id, s.road_id, s.s_start, s.s_end) for s in crossing.road_sections] == [
        ("s1", "r", 0.5, 20.25),
        ("s2", "rail", 100, 101),
    ]
    assert road_map.diagnostics == ()


@pytest.mark.parametrize(
    ("content", "attribute", "element"),
    [
        ("<junction/>", "id", "/OpenDRIVE/junction[@id='?']"),
        ('<junction id="j"><connection/></junction>', "id", "/connection[@id='?']"),
        (
            '<junction id="j"><connection id="c">'
            '<laneLink from="-1"/></connection></junction>',
            "to",
            "/laneLink",
        ),
        (
            '<junction id="j"><connection id="c">'
            '<laneLink from="x" to="1"/></connection></junction>',
            "from",
            "/laneLink",
        ),
        ('<junctionGroup id="g"/>', "type", "/OpenDRIVE/junctionGroup[@id='g']"),
        (
            '<junctionGroup id="g" type="roundabout">'
            "<junctionReference/></junctionGroup>",
            "junction",
            "/junctionReference",
        ),
        ('<controller id="c"><control/></controller>', "signalId", "/control"),
        ('<controller id="c" sequence="bad"/>', "sequence", "/controller[@id='c']"),
        (
            '<junction id="j" type="crossing">'
            '<roadSection id="s" roadId="r" sStart="nan" sEnd="1"/></junction>',
            "sStart",
            "/roadSection",
        ),
    ],
)
def test_missing_or_invalid_attributes_have_context(
    content: str, attribute: str, element: str
) -> None:
    with pytest.raises(OpenDriveParseError) as caught:
        load(content)
    assert attribute in caught.value.message
    assert caught.value.element.endswith(element)


def test_supported_junction_geometry_and_unknown_content_diagnostics() -> None:
    road_map = load(
        """<junction id="j" future="value">
          <connection id="c" extra="value">
            <laneLink from="-1" to="-1"><userData/></laneLink>
          </connection>
          <planView>
            <geometry s="0" x="0" y="0" hdg="0" length="10"><line/></geometry>
          </planView>
          <crossPath id="cp" crossingRoad="r3" roadAtStart="r1" roadAtEnd="r2">
            <startLaneLink s="0" from="-1" to="-1"/>
            <endLaneLink s="10" from="1" to="1"/>
          </crossPath>
          <controller id="c" name="unsupported"><control signalId="s"/></controller>
        </junction>
        <controller id="c" type="unsupported"><userData/></controller>"""
    )
    observations = [(d.code, d.element) for d in road_map.diagnostics]
    assert ("unsupported-attribute", "/OpenDRIVE/junction[@id='j']") in observations
    assert any(user_data.code is None for user_data in road_map.user_data)
    assert not any(
        path.endswith("/planView") or path.endswith("/crossPath")
        for _, path in observations
    )
    assert (
        "unsupported-element",
        "/OpenDRIVE/junction[@id='j']/controller[@id='c']/control",
    ) in observations
    assert ("unsupported-attribute", "/OpenDRIVE/controller[@id='c']") in observations


def test_map_without_topology_records_has_empty_tuples() -> None:
    road_map = load("")
    assert road_map.junctions == ()
    assert road_map.junction_groups == ()
    assert road_map.controllers == ()


def test_junction_reference_validation_is_opt_in_and_keeps_source_ids() -> None:
    road_map = load("""<junction id="j"><connection id="c" incomingRoad="missing"/>
      <crossPath id="cp" crossingRoad="missing" roadAtStart="r1" roadAtEnd="r2">
        <startLaneLink s="0" from="-1" to="-1"/><endLaneLink s="1" from="1" to="1"/>
      </crossPath></junction>""")
    assert road_map.diagnostics == ()
    assert road_map.junctions[0].cross_paths[0].crossing_road == "missing"
    assert [item.code for item in validate_junctions(road_map)].count(
        "unresolved-road"
    ) == 4


def test_junction_boundary_elevation_grid_and_crg_metadata() -> None:
    road_map = load("""<junction id="j">
      <boundary>
        <segment type="lane" roadId="r" boundaryLane="-1" sStart="begin" sEnd="20"/>
        <segment type="joint" roadId="r2" contactPoint="end" transitionLength="2.5"/>
      </boundary>
      <elevationGrid sStart="0" gridSpacing="0.5">
        <elevation center="1 2" left="0.5 1.5" right="1.5 2.5"/>
      </elevationGrid>
      <surface>
        <CRG file="surface.crg" mode="attached" orientation="+"
             sStart="0" sEnd="20" zScale="1.2"/>
      </surface>
    </junction>""")
    junction = road_map.junctions[0]
    assert junction.boundary is not None
    assert junction.boundary.segments[0].s_start == "begin"
    assert junction.boundary.segments[1].transition_length == 2.5
    assert junction.elevation_grid is not None
    assert junction.elevation_grid.elevations[0].center == (1.0, 2.0)
    assert junction.crgs[0].file == "surface.crg"
    assert junction.crgs[0].z_scale == 1.2


def test_junction_validator_checks_lane_ids_and_type_requirements() -> None:
    road_map = load("""
      <road id="in" length="10" junction="-1"><lanes><laneSection s="0">
        <left><lane id="1"/></left><center><lane id="0"/></center>
      </laneSection></lanes></road>
      <road id="connect" length="10" junction="j"><lanes><laneSection s="0">
        <left><lane id="2"/></left><center><lane id="0"/></center>
      </laneSection></lanes></road>
      <junction id="j"><connection id="c" incomingRoad="in"
        connectingRoad="connect" contactPoint="start">
        <laneLink from="7" to="2"/>
      </connection></junction>
      <junction id="virtual" type="virtual"/>
    """)
    observations = [(item.code, item.element) for item in validate_junctions(road_map)]
    assert (
        "unresolved-lane",
        "/OpenDRIVE/junction[@id='j']/connection[@id='c']/@from",
    ) in observations
    assert sum(code == "missing-junction-field" for code, _ in observations) == 4


def test_junction_validator_reports_known_type_cardinalities() -> None:
    road_map = load('<junction id="cross" type="crossing"/>')
    diagnostics = validate_junctions(road_map)
    assert any(
        item.code == "junction-cardinality" and "roadSection" in item.message
        for item in diagnostics
    )
