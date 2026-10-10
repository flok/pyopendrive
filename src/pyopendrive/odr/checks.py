"""Opt-in semantic checks on parsed OpenDRIVE records."""

from pyopendrive.odr.models.opendrive import OpenDriveDiagnostic, OpenDriveMap


def validate_junctions(road_map: OpenDriveMap) -> tuple[OpenDriveDiagnostic, ...]:
    """Report unresolved junction-related IDs without changing parsed records."""
    roads = {road.id for road in road_map.roads}
    junctions = {junction.id for junction in road_map.junctions}
    diagnostics: list[OpenDriveDiagnostic] = []

    def missing(reference: str, known: set[str], kind: str, element: str) -> None:
        if reference not in known:
            diagnostics.append(
                OpenDriveDiagnostic(
                    code=f"unresolved-{kind}",
                    message=f"Referenced {kind} {reference!r} does not exist.",
                    element=element,
                )
            )

    for junction in road_map.junctions:
        path = f"/OpenDRIVE/junction[@id='{junction.id}']"
        for connection in junction.connections:
            connection_path = f"{path}/connection[@id='{connection.id}']"
            for attribute, reference in (
                ("incomingRoad", connection.incoming_road),
                ("connectingRoad", connection.connecting_road),
                ("linkedRoad", connection.linked_road),
            ):
                if reference is not None:
                    missing(reference, roads, "road", f"{connection_path}/@{attribute}")
        for section in junction.road_sections:
            missing(
                section.road_id,
                roads,
                "road",
                f"{path}/roadSection[@id='{section.id}']/@roadId",
            )
        for item in junction.cross_paths:
            cross_path = f"{path}/crossPath[@id='{item.id}']"
            for attribute, reference in (
                ("crossingRoad", item.crossing_road),
                ("roadAtStart", item.road_at_start),
                ("roadAtEnd", item.road_at_end),
            ):
                missing(reference, roads, "road", f"{cross_path}/@{attribute}")
        if junction.main_road is not None:
            missing(junction.main_road, roads, "road", f"{path}/@mainRoad")
        if junction.boundary is not None:
            for index, segment in enumerate(junction.boundary.segments):
                missing(
                    segment.road_id,
                    roads,
                    "road",
                    f"{path}/boundary/segment[{index}]/@roadId",
                )

    for group in road_map.junction_groups:
        for reference in group.junction_references:
            missing(
                reference.junction,
                junctions,
                "junction",
                f"/OpenDRIVE/junctionGroup[@id='{group.id}']/junctionReference/@junction",
            )
    return tuple(diagnostics)
