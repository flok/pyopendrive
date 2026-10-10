"""Check the public loading API in an installed distribution environment."""

from importlib.metadata import distribution, version
from io import StringIO
from pathlib import Path

import pyopendrive
from pyopendrive import OpenDriveMap, OpenDriveVersion


def main() -> None:
    package_path = Path(pyopendrive.__file__).resolve()
    installed_package_path = Path(
        distribution("pyopendrive").locate_file("pyopendrive/__init__.py")
    ).resolve()
    assert package_path == installed_package_path, (
        package_path,
        installed_package_path,
    )
    assert version("pyopendrive")
    for name in pyopendrive.__all__:
        assert hasattr(pyopendrive, name), name

    source = StringIO(
        '<OpenDRIVE><header revMajor="1" revMinor="9"/>'
        '<road id="installed" length="12.5" junction="-1"/>'
        "</OpenDRIVE>"
    )
    road_map = OpenDriveMap.load(source)
    assert road_map.format_version == OpenDriveVersion(1, 9)
    assert road_map.roads[0].id == "installed"
    assert road_map.roads[0].length == 12.5
    assert not source.closed
    print(f"Installed pyopendrive {version('pyopendrive')} loads a map.")


if __name__ == "__main__":
    main()
