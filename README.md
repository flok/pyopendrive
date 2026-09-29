# PyOpenDrive

PyOpenDrive is a Python library for reading ASAM OpenDRIVE road network files.

## Current support

The initial parser reads the OpenDRIVE format revision, common header metadata,
and road identifiers, lengths, junction references, and names. It does not yet
parse road geometry, lanes, signals, or other nested elements, and it does not
validate documents against the ASAM XSD schemas.

## Usage

```python
from pyopendrive import OpenDrive

road_network = OpenDrive.load("map.xodr")
print(road_network.format_version)
for road in road_network.roads:
    print(road.id, road.length)
```

`OpenDrive` is the public loading entry point. `OpenDriveMap` and the other
model classes contain parsed data only; XML parsing stays internal.

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
