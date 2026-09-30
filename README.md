# PyOpenDrive

PyOpenDrive is a Python library for reading ASAM OpenDRIVE road network files.

## Current support

The initial parser reads the OpenDRIVE format revision, common header metadata,
and road identifiers, lengths, junction references, and names. It does not yet
parse road geometry, lanes, signals, or other nested elements, and it does not
validate documents against the ASAM XSD schemas.

## Usage

```python
from pyopendrive import OpenDriveMap

road_network = OpenDriveMap.load("map.xodr")
print(road_network.format_version)
for road in road_network.roads:
    print(road.id, road.length)
```

`OpenDriveMap.load` accepts filesystem paths and caller-owned text or binary
streams. Caller-owned streams remain open. `OpenDrive` remains available as a
compatibility alias. Successful parsing reads supported fields but does not
imply complete XSD or semantic validation. Recoverable unsupported content is
reported through structured values in `road_network.diagnostics`.

## Package layout

- `pyopendrive/odr/models/` contains the public domain objects.
- `pyopendrive/odr/parser/` contains the XML-to-model conversion and parse errors.
- `pyopendrive` exposes the loading facade and model types directly.

## Development

```powershell
uv sync
uv run ruff check .
uv run ruff format --check .
```
