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

`OpenDriveMap` is the public entry point. XML parsing stays internal; the
returned object exposes the parsed header, format version, and roads.

## Package layout

- `pyopendrive/odr/models/` contains the public domain objects.
- `pyopendrive/odr/parser/` contains the XML-to-model conversion and parse errors.
- `pyopendrive` exposes the public map class and model types directly.

## Development

```powershell
uv sync
uv run ruff check .
uv run ruff format --check .
```
