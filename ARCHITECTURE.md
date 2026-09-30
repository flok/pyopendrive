# PyOpenDrive architecture

## Purpose and scope

PyOpenDrive reads ASAM OpenDRIVE XML road-network files into typed Python
objects. Its current model follows OpenDRIVE 1.9.0 and the planned compatibility
range is 1.4.0 through 1.9.0. OpenDRIVE describes static network data. Writing
files, evaluating geometry, coordinate transforms, routing, runtime schema
validation as a required dependency, and dynamic traffic content are outside
the initial release scope.

The feature-by-feature status and version caveats live in
[`docs/compatibility.md`](docs/compatibility.md). The staged implementation
plan lives in [`ROADMAP.md`](ROADMAP.md).

## Package structure

```text
src/pyopendrive/
├── __init__.py             # Stable public imports
└── odr/
    ├── __init__.py         # OpenDRIVE types and parser error exports
    ├── api.py              # Compatibility loading facade
    ├── models/
    │   ├── __init__.py
    │   └── opendrive.py    # Map, header, road, and format-revision models
    └── parser/
        ├── __init__.py
        └── xml.py          # XML-to-model conversion
```

The `odr` directory is an internal implementation package. Users import
supported names from the `pyopendrive` package root:

```python
from pyopendrive import OpenDriveMap

road_map = OpenDriveMap.load("map.xodr")
```

## Responsibilities and data flow

1. `OpenDriveMap.load(source)` is the public loading method for paths and
   caller-owned text or binary streams. It delegates parsing to
   `odr.parser.xml`; `OpenDrive.load` remains a compatibility alias.
2. The XML parser uses the Python standard library's `xml.etree.ElementTree`
   and converts the document into model values.
3. `OpenDriveMap`, `OpenDriveVersion`, `Header`, and `Road` are immutable,
   slotted dataclasses. Collections exposed by the map are tuples.
4. `OpenDriveParseError` represents malformed XML or required OpenDRIVE
   structure/attributes that cannot be parsed and exposes element context.
5. `pyopendrive.__init__` re-exports the supported public types so internal
   module paths can change without changing normal user imports.
6. Recoverable unsupported elements and attributes produce immutable
   `OpenDriveDiagnostic` values on the map rather than being silently ignored.

The parser currently reads `revMajor`/`revMinor`, common header metadata, and
road IDs, lengths, junction references, and names. It handles XML namespace
prefixes when comparing element names. A file header carries major/minor
revision only; patch releases cannot be inferred from it.

## Design boundaries

- Models contain parsed domain data and should not depend on XML element types.
  The map's loading classmethod imports the parser lazily, preserving that
  dependency boundary while providing the public entry point.
- Parsing and parse-diagnostic collection belong in `odr/parser/`; the map
  exposes only a thin loading entry point and `odr/api.py` retains its legacy
  facade. Domain models contain no XML conversion logic.
- ASAM structural/version rules belong in the compatibility matrix and
  version-aware parser behavior. Keep optional validation separate from the
  default loading path.
- Preserve supported source values as data; do not silently turn parsing into
  geometry evaluation or normalization.
- Extend the model in small slices that follow the specification's element
  relationships and keep version-specific behavior explicit.

## Project tooling

`pyproject.toml` defines Python 3.12+, Hatchling as the build backend, `uv`
project commands, and Ruff lint/format rules. Configuration in that file is
authoritative; this document describes architectural boundaries rather than
duplicating every tool option.

Integration tests use the same fetch-then-test command locally and in CI:
`uv run python tests/fetch_testdata.py && uv run pytest`. The fetch step verifies
and extracts an external ASAM example corpus, reusing a valid local cache;
downloaded inputs remain outside version control. Pytest discovery is configured
in `pyproject.toml`, while provenance and licensing cautions are documented in
`tests/README.md`.
