"""Opt-in semantic checks on parsed OpenDRIVE records."""

from pyopendrive.odr.models.opendrive import OpenDriveDiagnostic, OpenDriveMap
from pyopendrive.odr.models.road import Road


def validate_junctions(road_map: OpenDriveMap) -> tuple[OpenDriveDiagnostic, ...]:
    """Check selected 1.8.1 junction rules and references without mutation.

    Full applicability of type-specific rules to OpenDRIVE 1.9.0 remains
    unverified. The checks do not evaluate geometric connectivity.
    """
    roads = {road.id: road for road in road_map.roads}
    junctions = {junction.id for junction in road_map.junctions}
    controllers = {controller.id for controller in road_map.controllers}
    diagnostics: list[OpenDriveDiagnostic] = []

    def issue(code: str, message: str, element: str) -> None:
        diagnostics.append(OpenDriveDiagnostic(code, message, element))

    def road_ref(reference: str, element: str) -> Road | None:
        if reference == "-1":
            return None
        road = roads.get(reference)
        if road is None:
            issue(
                "unresolved-road",
                f"Referenced road {reference!r} does not exist.",
                element,
            )
        return road

    for junction in road_map.junctions:
        path = f"/OpenDRIVE/junction[@id='{junction.id}']"
        kind = junction.type or "default"
        if kind not in {"default", "direct", "virtual", "crossing"}:
            issue(
                "invalid-junction-type",
                f"Unsupported junction type {kind!r}.",
                f"{path}/@type",
            )
            continue

        if kind == "direct" and not junction.connections:
            issue(
                "junction-cardinality",
                "Direct junctions require at least one connection.",
                path,
            )
        if kind == "crossing" and not junction.road_sections:
            issue(
                "junction-cardinality",
                "Crossings require at least one roadSection.",
                path,
            )
        if kind == "crossing" and junction.connections:
            issue(
                "junction-type-content",
                "Crossings cannot define road connections.",
                f"{path}/connection",
            )
        if kind == "virtual":
            for name, value in (
                ("mainRoad", junction.main_road),
                ("orientation", junction.orientation),
                ("sStart", junction.s_start),
                ("sEnd", junction.s_end),
            ):
                if value is None:
                    issue(
                        "missing-junction-field",
                        f"Virtual junctions require {name}.",
                        path,
                    )
            if junction.controllers:
                issue(
                    "junction-type-content",
                    "Virtual junctions cannot define controllers.",
                    f"{path}/controller",
                )
        elif any(
            value is not None
            for value in (
                junction.main_road,
                junction.orientation,
                junction.s_start,
                junction.s_end,
            )
        ):
            issue(
                "junction-type-content",
                "Virtual-junction fields are only valid for virtual junctions.",
                path,
            )
        if kind != "default" and junction.elevation_grid is not None:
            issue(
                "junction-type-content",
                "Elevation grids are only valid for common junctions.",
                f"{path}/elevationGrid",
            )
        if kind not in {"default", "virtual"} and junction.cross_paths:
            issue(
                "junction-type-content",
                "Cross paths are only valid for common or virtual junctions.",
                f"{path}/crossPath",
            )

        for connection in junction.connections:
            item_path = f"{path}/connection[@id='{connection.id}']"
            incoming = (
                road_ref(connection.incoming_road, f"{item_path}/@incomingRoad")
                if connection.incoming_road
                else None
            )
            target_id = (
                connection.linked_road
                if kind == "direct"
                else connection.connecting_road
            )
            target_name = "linkedRoad" if kind == "direct" else "connectingRoad"
            target = (
                road_ref(target_id, f"{item_path}/@{target_name}")
                if target_id
                else None
            )
            if kind == "default" and connection.linked_road is not None:
                issue(
                    "junction-type-content",
                    "linkedRoad is not valid for a common connection.",
                    item_path,
                )
            if kind == "direct" and connection.connecting_road is not None:
                issue(
                    "junction-type-content",
                    "connectingRoad is not valid for a direct connection.",
                    item_path,
                )
            if kind != "virtual" and connection.type == "virtual":
                issue(
                    "junction-type-content",
                    "Virtual connections are only valid in virtual junctions.",
                    item_path,
                )
            if kind in {"default", "crossing"} and connection.type is not None:
                issue(
                    "junction-type-content",
                    "Connection type attributes are only for virtual junctions.",
                    f"{item_path}/@type",
                )
            if kind == "virtual" and connection.type not in {
                None,
                "default",
                "virtual",
            }:
                issue(
                    "invalid-connection-type",
                    f"Unsupported virtual connection type {connection.type!r}.",
                    f"{item_path}/@type",
                )
            if (
                kind == "virtual"
                and connection.type != "virtual"
                and not connection.connecting_road
            ):
                issue(
                    "missing-connection-field",
                    "Default virtual-junction connections require connectingRoad.",
                    item_path,
                )
            if (
                kind == "virtual"
                and connection.type == "virtual"
                and connection.connecting_road
            ):
                issue(
                    "junction-type-content",
                    "Virtual connections cannot define connectingRoad.",
                    f"{item_path}/@connectingRoad",
                )
            if kind in {"default", "direct"}:
                for name, value in (
                    ("incomingRoad", connection.incoming_road),
                    (target_name, target_id),
                    ("contactPoint", connection.contact_point),
                ):
                    if value is None:
                        issue(
                            "missing-connection-field",
                            f"{kind} connections require {name}.",
                            item_path,
                        )
            if incoming is not None and target is not None:
                _check_lanes(
                    connection.lane_links, incoming, target, diagnostics, item_path
                )
            if (
                kind in {"default", "virtual"}
                and connection.connecting_road in roads
                and roads[connection.connecting_road].junction != junction.id
            ):
                issue(
                    "wrong-junction-membership",
                    "Connecting road does not name this junction.",
                    f"{item_path}/@connectingRoad",
                )
            if kind == "virtual" and connection.type == "virtual":
                if connection.predecessor is None or connection.successor is None:
                    issue(
                        "missing-connection-link",
                        "Virtual connections require predecessor and successor.",
                        item_path,
                    )
                else:
                    predecessor = connection.predecessor
                    successor = connection.successor
                    if predecessor.element_type == "road":
                        road_ref(
                            predecessor.element_id,
                            f"{item_path}/predecessor/@elementId",
                        )
                    if successor.element_type == "road":
                        road_ref(
                            successor.element_id, f"{item_path}/successor/@elementId"
                        )
                if (
                    connection.predecessor is not None
                    and connection.successor is not None
                    and connection.predecessor.element_id in roads
                    and connection.successor.element_id in roads
                ):
                    _check_lanes(
                        connection.lane_links,
                        roads[connection.predecessor.element_id],
                        roads[connection.successor.element_id],
                        diagnostics,
                        item_path,
                    )

        for section in junction.road_sections:
            road_ref(section.road_id, f"{path}/roadSection[@id='{section.id}']/@roadId")
        for item in junction.cross_paths:
            item_path = f"{path}/crossPath[@id='{item.id}']"
            crossing = road_ref(item.crossing_road, f"{item_path}/@crossingRoad")
            at_start = road_ref(item.road_at_start, f"{item_path}/@roadAtStart")
            at_end = road_ref(item.road_at_end, f"{item_path}/@roadAtEnd")
            if crossing and at_start:
                _check_cross_lane(
                    item.start_lane_link,
                    at_start,
                    crossing,
                    diagnostics,
                    f"{item_path}/startLaneLink",
                )
            if crossing and at_end:
                _check_cross_lane(
                    item.end_lane_link,
                    at_end,
                    crossing,
                    diagnostics,
                    f"{item_path}/endLaneLink",
                )
            if crossing is not None and crossing.junction != junction.id:
                issue(
                    "wrong-junction-membership",
                    "Crossing road does not name this junction.",
                    f"{item_path}/@crossingRoad",
                )
        for name, values in (
            ("connection", [item.id for item in junction.connections]),
            ("crossPath", [item.id for item in junction.cross_paths]),
            ("roadSection", [item.id for item in junction.road_sections]),
        ):
            if len(values) != len(set(values)):
                issue(
                    "duplicate-junction-id",
                    f"Duplicate {name} IDs occur within the junction.",
                    path,
                )
        if junction.main_road:
            road_ref(junction.main_road, f"{path}/@mainRoad")
        for priority in junction.priorities:
            road_ref(priority.high, f"{path}/priority/@high")
            road_ref(priority.low, f"{path}/priority/@low")
        for controller in junction.controllers:
            if controller.id not in controllers:
                issue(
                    "unresolved-controller",
                    f"Referenced controller {controller.id!r} does not exist.",
                    f"{path}/controller/@id",
                )
        if junction.boundary:
            for index, segment in enumerate(junction.boundary.segments):
                road_ref(segment.road_id, f"{path}/boundary/segment[{index}]/@roadId")

    for group in road_map.junction_groups:
        if not group.junction_references:
            issue(
                "junction-cardinality",
                "Junction groups require at least one junctionReference.",
                f"/OpenDRIVE/junctionGroup[@id='{group.id}']",
            )
        for reference in group.junction_references:
            if reference.junction not in junctions:
                issue(
                    "unresolved-junction",
                    f"Referenced junction {reference.junction!r} does not exist.",
                    f"/OpenDRIVE/junctionGroup[@id='{group.id}']/junctionReference/@junction",
                )
    return tuple(diagnostics)


def _lane_ids(road: Road) -> set[int]:
    return {
        lane.id
        for layer in road.lane_layers
        for section in layer.sections
        for group in (section.lanes.left, section.lanes.center, section.lanes.right)
        if group is not None
        for lane in group
    }


def _check_lanes(links, source: Road, target: Road, diagnostics, path: str) -> None:
    source_lanes, target_lanes = _lane_ids(source), _lane_ids(target)
    for link in links:
        for lane_id, known, attribute in (
            (link.from_lane, source_lanes, "from"),
            (link.to_lane, target_lanes, "to"),
        ):
            if lane_id not in known:
                diagnostics.append(
                    OpenDriveDiagnostic(
                        "unresolved-lane",
                        f"Referenced {attribute} lane {lane_id} does not exist "
                        "on road.",
                        f"{path}/@{attribute}",
                    )
                )


def _check_cross_lane(
    link, linked_road: Road, crossing_road: Road, diagnostics, path: str
) -> None:
    _check_lanes((link,), linked_road, crossing_road, diagnostics, path)
