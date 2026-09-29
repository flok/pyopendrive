"""Small examples of testing the public loading API."""

from io import StringIO

from pyopendrive import OpenDrive, OpenDriveVersion


def test_load_minimal_map() -> None:
    source = StringIO(
        """\
<OpenDRIVE>
  <header revMajor="1" revMinor="9" name="Showcase"/>
  <road id="1" length="12.5" junction="-1" name="Example road"/>
</OpenDRIVE>
"""
    )

    road_map = OpenDrive.load(source)

    assert road_map.format_version == OpenDriveVersion(major=1, minor=9)
    assert road_map.header.name == "Showcase"
    assert len(road_map.roads) == 1
    assert road_map.roads[0].name == "Example road"
