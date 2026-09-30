# PyOpenDrive architecture

## Purpose and scope

PyOpenDrive reads ASAM OpenDRIVE XML road-network files into typed Python
objects. Its current model follows OpenDRIVE 1.9.0 and planned compatibility
ranges from 1.4.0 through 1.9.0. Writing files, evaluating geometry,
coordinate transforms, routing, runtime schema validation, and dynamic traffic
content are outside the initial release scope.

Feature coverage and version caveats live in [`COMPATIBILITY.md`](COMPATIBILITY.md).
The staged implementation plan lives in [`ROADMAP.md`](ROADMAP.md).

## Package structure

```text
src/pyopendrive/
├── __init__.py
└── odr/
    ├── __init__.py
    ├── api.py
    ├── models/
    │   ├── __init__.py
    │   ├── geometry.py     # Plan-view geometry values
    │   ├── lanes.py        # Lane layers and lane-property values
    │   ├── opendrive.py    # Map, header, and format-revision models
    │   ├── profiles.py     # Elevation and lateral profile values
    │   └── road.py         # Road metadata, profiles, geometry, and lanes
    └── parser/
        ├── __init__.py
        ├── geometry.py     # Plan-view geometry conversion
        ├── lanes.py        # Lane XML-to-model conversion
        ├── profiles.py     # Elevation and lateral profile conversion
        └── xml.py          # XML-to-model conversion
```

Users import supported names from the package root:

```python
from pyopendrive import OpenDriveMap

road_map = OpenDriveMap.load("map.xodr")
```

## Responsibilities and data flow

1. `OpenDriveMap.load(source)` loads paths and caller-owned text or binary
   streams through `odr.parser.xml`; `OpenDrive.load` remains a compatibility
   alias.
2. The XML parser uses `xml.etree.ElementTree` and converts XML to immutable,
   slotted models. Collections exposed by the map and its roads are tuples.
3. `OpenDriveParseError` reports malformed XML or required structure and
   attributes that cannot be parsed, with element context.
4. The package root re-exports supported types so internal module paths can
   change without changing ordinary imports.
5. Recoverable unsupported content produces structured
   `OpenDriveDiagnostic` values on the map.

The parser reads header metadata, road identity and links, road types, plan-view
segments, elevation/lateral profiles, and ordered permanent/temporary lane
layers. Lane layers contain sections, lane groups, lane links, width and border
records, road marks, and supported lane properties. Model classes do not depend
on XML elements. Geometry values preserve source parameters; geometry
calculation and coordinate transforms remain separate. The header contains
major/minor revision only, so patch releases cannot be inferred.

## Design boundaries

- Models describe parsed domain data; parser modules convert XML into models.
- Parsing and recoverable diagnostics belong in `odr/parser/`.
- Version rules belong in the compatibility matrix and version-aware parser.
- Preserve source values; do not silently evaluate or normalize them.
- Keep optional validation separate from the default loading path.

## Project tooling

`pyproject.toml` defines Python 3.12+, Hatchling, `uv`, and Ruff settings.
Integration tests use `uv run python tests/fetch_testdata.py && uv run pytest`;
downloaded ASAM inputs remain outside version control.