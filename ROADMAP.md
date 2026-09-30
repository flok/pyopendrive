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
- The parser reads header revision, common header metadata, and road IDs,
  lengths, junction references, and names. It handles namespace-prefixed XML
  names and reports malformed XML or missing required structure through
  `OpenDriveParseError`. Unsupported content produces structured diagnostics
  with element context.
- Road geometry, profiles, lanes, junctions, signals, objects, supplementary
  elements, validation, and older-version-specific behavior remain planned;
  the compatibility target and major feature groups are summarized below.
- The project targets Python 3.12+, has no runtime dependencies, and uses `uv`
  and Ruff.

## Milestones

### M0 — Scope and evidence

1. [Define the OpenDRIVE version and feature support matrix](https://github.com/flok/pyopendrive/issues/1) — **complete**; supported revisions and feature groups are summarized in this roadmap.
2. [Build a versioned example and fixture corpus](https://github.com/flok/pyopendrive/issues/2) — planned.

### M1 — Parser foundation

3. [Stabilize the file-loading API and diagnostics](https://github.com/flok/pyopendrive/issues/3) — **complete**; paths and caller-owned streams share `OpenDriveMap.load(...)`, with contextual errors and recoverable diagnostics.
4. [Set up CI and supported-Python verification](https://github.com/flok/pyopendrive/issues/4) — planned.

### M2 — Core road model

5. Parse document and complete header metadata.
6. Parse road metadata, types, and links.
7. Parse reference-line geometry.
8. Parse elevation and lateral profiles.
9. Parse lanes and lane properties.

### M3 — Network features

10. Parse junctions and lane connections.
11. Parse signals and controllers.
12. Parse road objects and object references.
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

Complete the fixture corpus and parser/API contract, then CI. Build the core
model in small parser/model slices, followed by network elements and older
revision compatibility. Documentation can track implementation; prepare the
stable release after the supported surface is settled.

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
