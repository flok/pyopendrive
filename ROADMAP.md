# PyOpenDrive roadmap

PyOpenDrive reads ASAM OpenDRIVE XML into typed Python objects. The compatibility
target is OpenDRIVE 1.4.0–1.9.0. This roadmap reflects the current
implementation and the project's architecture documented in
[ARCHITECTURE.md](ARCHITECTURE.md).

## Current implementation

- Public entry point: `OpenDriveMap.load(source)`, exported from `pyopendrive`;
  it accepts paths and caller-owned streams. `OpenDrive.load` remains an alias.
- `odr/api.py` is the loading facade. `odr/parser/xml.py` parses XML with the
  standard-library `ElementTree`; `odr/models/` contains data-only, immutable
  models. The parser and models remain separate.
- The parser reads header revision and metadata, road identity, types, and
  links, plan-view geometry, elevation and lateral profiles, and lane layers
  with supported properties. Maps also contain junction topology, groups, and
  static controllers. Roads contain signals, objects, their references, and
  supported outline and marking records. It handles namespace-prefixed XML
  element names and reports malformed XML or missing required structure through
  `OpenDriveParseError`. Unsupported content produces structured diagnostics
  with element context. Geometry evaluation and semantic validation remain
  separate capabilities.
- Tests include authored revision fixtures for 1.4 through 1.9, malformed
  documents, focused parser behavior checks, and the ASAM 1.9.0 examples/use-cases
  corpus. `tests/fetch_testdata.py` downloads the archive, verifies its SHA-256,
  and extracts only `.xodr` files into ignored test data. Authored revision
  fixtures exercise shared parsing behavior. Their historical schema validity
  is unknown, and they do not establish complete older-version compatibility.
- GitHub Actions runs Ruff and tests Python 3.12, 3.13, and 3.14 on pushes and
  pull requests. Each Python version fetches the ASAM corpus, runs pytest, and
  verifies installed wheel and source distributions. Project commands use the
  committed lockfile. The `v<version>` tag workflow verifies the package version,
  repeats these checks, publishes the wheel through PyPI Trusted Publishing,
  and creates a GitHub release with generated notes.
- Remaining network elements, validation, and complete older-version behavior
  are tracked in [COMPATIBILITY.md](COMPATIBILITY.md).
- The project targets Python 3.12+, has no runtime dependencies, and uses `uv`
  and Ruff.

## Milestones

### M0 — Scope and evidence

1. [Define the OpenDRIVE version and feature support matrix](https://github.com/flok/pyopendrive/issues/1) — **complete**; supported revisions and feature groups are summarized in this roadmap.
2. [Build a versioned example and fixture corpus](https://github.com/flok/pyopendrive/issues/2) — **in progress**; the official 1.9.0 corpus, authored 1.4 through 1.9 smoke fixtures, and invalid inputs are exercised. Official historical inputs and normative version-specific checks remain outstanding.

### M1 — Parser foundation

3. [Stabilize the file-loading API and diagnostics](https://github.com/flok/pyopendrive/issues/3) — **complete**; paths and caller-owned streams share `OpenDriveMap.load(...)`, with contextual errors and recoverable diagnostics.
4. [Set up CI and supported-Python verification](https://github.com/flok/pyopendrive/issues/4) — **complete**; workflows include Ruff, Python 3.12 through 3.14, the official example corpus, and installed wheel and source-distribution checks. Version tags publish a wheel and generated release notes after verification.

### M2 — Core road model

5. Parse document and header metadata — **complete** for the documented fields.
6. Parse road metadata, types, and links — **partial**; identity, rules, type/speed records, and predecessor/successor references are implemented.
7. Parse reference-line geometry — **complete**; line, arc, spiral, poly3, and paramPoly3 parameters are preserved.
8. Parse elevation and lateral profiles — **complete** for the documented coefficient and surface records.
9. Parse lanes and lane properties — **partial**; layers, sections, links, widths/borders, road marks, and common properties are implemented. Unsupported nested content is diagnosed.

### M3 — Network features

10. Parse junctions and lane connections — **implemented with validation limits**; connections, lane links, virtual endpoints, crossing road sections, groups, cross paths, reference-line geometry, boundary segments, elevation grids, and CRG metadata are parsed. Optional road/junction reference checks are available. Lane-level topology, geometric checks, CRG decoding, and unverified revision-specific cardinalities remain open.
11. Parse signals and controllers — **partial**; signals, references, lane validity, dependencies, links, and static controller mappings are implemented. Signal semantics and alternate position records remain unsupported.
12. Parse road objects and object references — **partial**; object attributes, references, road/local outline corners, smooth outline curves, and markings are implemented. Repeats, skeletons, materials, parking spaces, borders, tunnels, and bridges remain unsupported.
13. Parse supplementary network elements.
14. Preserve and report user-defined extensions.
15. Resolve included OpenDRIVE files.
16. Read gzip-compressed `.xodrz` files.

### M4 — Compatibility and validation

17. Add compatibility for OpenDRIVE 1.4–1.8, verifying version-specific rules
    against the relevant ASAM specification and schema.
18. Add optional schema and semantic validation; keep it outside the required
    loading path and runtime dependencies.

### M5 — Release

19. Document supported features and practical usage.
20. Prepare the first stable package release.

## Suggested order

Finish the remaining lane and network records in small parser/model slices,
then expand normative older-revision compatibility evidence and optional
validation. Keep fixture assertions and documented limits synchronized with
each slice. Prepare the stable release after the supported public API is settled.

## Scope boundaries

The initial package reads static road-network data. Writing OpenDRIVE files,
geometry evaluation, coordinate transforms, routing, simulation, dynamic
participants, external CRG payload decoding, and mandatory runtime schema
validation are outside the initial release. Requirements derived from ASAM
must stay traceable to their specification revision; uncertain version details
remain unknown until verified against the official specification, XSD, or UML.

## ASAM references

- [OpenDRIVE 1.9.0 specification](https://publications.pages.asam.net/standards/ASAM_OpenDRIVE/ASAM_OpenDRIVE_Specification/v1.9.0/specification/index.html)
- [OpenDRIVE 1.9.0 introduction and deliverables](https://publications.pages.asam.net/standards/ASAM_OpenDRIVE/ASAM_OpenDRIVE_Specification/v1.9.0/specification/00_preface/00_introduction.html)
- [OpenDRIVE releases and downloads](https://www.asam.net/standards/detail/opendrive/)
- The 1.9.0 source baseline includes the normative specification and Signal
  reference, XSD and UML models, examples and implementation examples, and the
  informative Junction guideline. Verify the role of each source before using
  it as a normative requirement.
