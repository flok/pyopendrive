# PyOpenDrive

PyOpenDrive is a Python library for reading ASAM OpenDRIVE road network files.

## Current support

The parser reads the OpenDRIVE format revision, header metadata, road attributes
and links, road types, plan-view geometry, elevation and lateral profiles,
lane layers with supported lane properties, and selected junction, controller,
signal, and object records. The models preserve source geometry parameters.
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
    for segment in road.plan_view:
        print(segment.s, segment.primitive)
    for layer in road.lane_layers:
        for section in layer.sections:
            for side in ("left", "center", "right"):
                for lane in getattr(section.lanes, side) or ():
                    print(side, lane.id, lane.lane_type)
    for signal in road.signals:
        print(signal.id, signal.type, signal.subtype)
    for road_object in road.objects:
        print(road_object.id, road_object.type, road_object.s, road_object.t)
for junction in road_map.junctions:
    print(junction.id, len(junction.connections))
```

The model preserves geometry parameters; `segment.primitive` identifies the
source geometry but does not calculate coordinates. Signal and object lists may
be empty when a road contains none. Unsupported but recoverable content is
available as structured diagnostics:

```python
for diagnostic in road_map.diagnostics:
    print(diagnostic.code, diagnostic.element, diagnostic.message)
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
