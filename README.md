# PyOpenDrive

PyOpenDrive is a Python library for reading ASAM OpenDRIVE road network files.

## Current support

The parser reads the OpenDRIVE format revision, header metadata, road attributes
and links, road types, plan-view geometry, elevation and lateral profiles,
lane layers with supported lane properties, and selected junction, controller,
signal, object, railway station/platform/switch, and road-surface CRG records. The
models preserve source geometry parameters.
The loader does not evaluate curves or validate documents
against the ASAM XSD schemas.

See [COMPATIBILITY.md](COMPATIBILITY.md) for precise feature coverage and
version limits, and [ROADMAP.md](ROADMAP.md) for remaining work.

## Usage

```python
from pyopendrive import OpenDriveMap

road_map = OpenDriveMap.load("map.xodr")
print(road_map.format_version)
for road in road_map.roads:
    print(road.id, road.length)
    for signal in road.signals:
        print(signal.id, signal.type, signal.subtype)
for junction in road_map.junctions:
    print(junction.id, len(junction.connections))
```

`OpenDriveMap.load` accepts filesystem paths and caller-owned text or binary
streams. Caller-owned streams remain open. `OpenDrive` remains available as a
compatibility alias. Successful parsing reads supported fields but does not
imply complete XSD or semantic validation. Recoverable unsupported content is
reported through structured values in `road_map.diagnostics`.

## Package layout

- `pyopendrive/odr/models/` contains the public domain objects.
- `pyopendrive/odr/parser/` contains the XML-to-model conversion and parse errors.
- `pyopendrive` exposes the loading facade and model types directly.

## Development

```powershell
uv sync
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked python tests/fetch_testdata.py
uv run --locked pytest
```

CI runs these checks on Python 3.12, 3.13, and 3.14. It also builds and installs
both the wheel and source distribution, then checks their public loading API.
