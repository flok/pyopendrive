"""Focused tests for railway station records."""

from pathlib import Path

from pyopendrive import (
    OpenDriveMap,
    Platform,
    PlatformSegment,
    RailroadSwitch,
    RailroadTrack,
    Station,
    SwitchPartner,
)


def test_station_platform_segments_are_parsed() -> None:
    source = Path(__file__).parent / "fixtures/network/railroad-station.xodr"

    road_map = OpenDriveMap.load(source)

    assert road_map.stations == (
        Station(
            id="station-1",
            name="Central",
            type="tram",
            platforms=(
                Platform(
                    id="platform-1",
                    name="West",
                    segments=(PlatformSegment("rail", 10, 40, "left"),),
                ),
            ),
        ),
    )
    assert road_map.roads[0].switches == (
        RailroadSwitch(
            id="switch-1",
            name="West turnout",
            position="dynamic",
            main_track=RailroadTrack("rail", 12, "+"),
            side_track=RailroadTrack("siding", 0, "+"),
            partner=SwitchPartner("switch-2", "East turnout"),
        ),
    )
    assert road_map.diagnostics == ()
