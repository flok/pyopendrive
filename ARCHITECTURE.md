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
    │   ├── junctions.py    # Junction topology and controller values
    │   ├── lanes.py        # Lane layers and lane-property values
    │   ├── objects.py      # Road objects, outlines, and markings
    │   ├── opendrive.py    # Map, header, and format-revision models
    │   ├── profiles.py     # Elevation and lateral profile values
    │   ├── road.py         # Road metadata and nested source records
    │   └── signals.py      # Signals, references, and shared lane validity
    └── parser/
        ├── __init__.py
        ├── geometry.py     # Plan-view geometry conversion
        ├── junctions.py    # Junction and controller conversion
        ├── lanes.py        # Lane XML-to-model conversion
        ├── objects.py      # Road object conversion
        ├── profiles.py     # Elevation and lateral profile conversion
        ├── signals.py      # Signal conversion and source-value helpers
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
on XML elements. Maps expose `junctions`, `junction_groups`, and `controllers`.
Roads expose `signals`, `signal_references`, `objects`, and `object_references`.
These ordered tuple collections contain source records. References remain IDs;
the parser does not resolve connectivity or signal ownership. Unsupported
network children and attributes produce diagnostics.
Geometry values preserve source parameters; geometry
calculation and coordinate transforms remain separate. The header contains
major/minor revision only, so patch releases cannot be inferred.

## Design boundaries

- Models describe parsed domain data; parser modules convert XML into models.
- Parsing and recoverable diagnostics belong in `odr/parser/`.
- Version rules belong in the compatibility matrix and version-aware parser.
- Preserve source values; do not silently evaluate or normalize them.
- Keep optional validation separate from the default loading path.
- Loading checks selected required attributes and numeric values. It does not
  enforce every type-dependent requirement, cardinality, or cross-reference.
  Junction, signal, and object parsing remains partial as documented in the
  compatibility matrix.

## Project tooling

`pyproject.toml` defines Python 3.12+, Hatchling, `uv`, and Ruff settings.
Integration tests use `uv run --locked python tests/fetch_testdata.py` followed
by `uv run --locked pytest`; downloaded ASAM inputs remain outside version
control. CI checks Python 3.12, 3.13, and 3.14, runs Ruff, and builds and installs
the wheel and source distribution. `tests/check_distribution.py` verifies the
public exports and loading API in an isolated installed-package environment.
