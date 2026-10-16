"""Focused tests for railway station records."""

from pathlib import Path

from pyopendrive import OpenDriveMap, Platform, PlatformSegment, Station


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
    assert road_map.diagnostics == ()
