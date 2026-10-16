# OpenDRIVE version and feature support

This document defines the initial compatibility target for PyOpenDrive. The
current data model is based on ASAM OpenDRIVE 1.9.0. The parser reads XML into
Python objects; schema validation, semantic checks, and geometry calculations
are separate capabilities.

Authored fixtures cover shared parser behavior under header revisions 1.4
through 1.9. Their historical schema validity is unknown. These fixtures are
not evidence that every feature or version-specific rule is supported.

The project targets Python 3.12 and newer, uses `uv` for project and build
management, and Ruff for linting/formatting. The public loading API is
`pyopendrive.OpenDriveMap.load(source)`; it returns typed models without
rewriting the source document. A successful load is not a claim of complete
XSD or semantic validation; currently unsupported content is identified in
the returned map's structured diagnostics.

## Version scope

| ASAM release | Release date | Header revision | Compatibility evidence |
| --- | --- | --- | --- |
| 1.4.0 | 2015-11-04 | 1.4 | ASAM predecessor release |
| 1.5.0 | 2019-02-17 | 1.5 | ASAM predecessor release |
| 1.6.0 | 2020-03-12 | 1.6 | ASAM release |
| 1.6.1 | 2021-03-04 | 1.6 | Maintenance release; patch is not represented in the XML header |
| 1.7.0 | 2021-08-03 | 1.7 | Backward-compatible with 1.6.1; specification also describes compatibility with 1.4/1.5 documents |
| 1.8.0 | 2023-11-22 | 1.8 | ASAM release |
| 1.8.1 | 2024-11-21 | 1.8 | Backward-compatible with 1.8.0; maintenance fixes and an added chapter |
| 1.9.0 | 2026-05-19 | 1.9 | Backward-compatible with 1.8.1; existing 1.8.1 XML validates against the 1.9.0 schema unchanged |

ASAM releases and dates are listed on the [current release page](https://www.asam.net/standards/detail/opendrive/)
and its [previous releases page](https://www.asam.net/standards/detail/opendrive/older/).
Compatibility statements are documented in [1.7.0](https://www.asam.net/fileadmin/Standards/OpenDRIVE/ASAM_OpenDRIVE_BS_V1-7-0.html),
[1.8.1 section 5](https://publications.pages.asam.net/standards/ASAM_OpenDRIVE/ASAM_OpenDRIVE_Specification/v1.8.1/specification/05_backward_compatibility/05_backward_compatibility.html),
and the [1.9.0 release presentation](https://www.asam.net/standards/detail/opendrive/).

The OpenDRIVE `<header>` identifies the format revision with `revMajor` and
`revMinor`. It cannot distinguish patch releases such as 1.6.0 from 1.6.1, or
1.8.0 from 1.8.1. PyOpenDrive therefore reports the revision encoded in the
document and must not infer a patch release. Patch-specific schema validation,
when enabled, needs an explicit schema choice or another source of provenance.
The parser accepts header revisions 1.4 through 1.9 and rejects other major or
minor values with an `OpenDriveParseError` located at `/OpenDRIVE/header`.

## Feature coverage

Status describes the current implementation and initial roadmap target, not a
claim that every detail has already been implemented.

| Element group | Current parser | Initial target | Notes |
| --- | --- | --- | --- |
| Root, format revision, complete header metadata | Supported | Supported | Parses bounds, georeference source text, coordinate offset, license, and 1.8+ default regulations; transforms remain separate. |
| Road identity and basic attributes | Supported | Supported | Parses ID, length, junction reference, name, and rule; identifiers remain strings. |
| Road links, road types, rules, metadata | Partial | Supported | Parses ordered type/speed records and predecessor/successor references; extended lane-layer state is tracked with the lane model. |
| Plan-view geometry | Supported | Supported | Parses ordered line, arc, spiral, poly3, and paramPoly3 segments while preserving source parameters; curve evaluation remains separate. |
| Elevation, superelevation, shape, cross-section profiles | Supported | Supported | Parses revision-aware coefficient records and cross-section surfaces; evaluating geometry is outside the initial target. |
| Lanes, lane links, road marks, access, speeds, widths | Partial | Supported | Parses layers, sections, groups, links, widths/borders, road marks, and common properties. Lane rules read the required `value` attribute. Unsupported nested children and attributes are diagnosed, including qualified vendor attributes. Explicit road-mark lines, sway, line color, and unknown payload preservation remain unsupported. |
| Junctions, connections, junction groups, controllers | Supported with limits | Supported | Parses topology, cross paths, reference geometry, boundaries, elevation-grid source lists, and CRG metadata. `validate_junctions()` checks selected 1.8.1 type rules, road/junction/controller references, road membership, and lane ID existence. Geometric connectivity and the applicability of 1.8.1 type rules to 1.9.0 remain unverified. |
| Signals and lane validity | Partial | Supported | Parses signals/references, dependencies, signal links, lane validity, and temporary/invalidated source state. Signal semantics and alternate position records remain unsupported and are diagnosed. |
| Road objects and object outlines/markings | Partial | Supported | Parses object/reference attributes, road/local outline corners, smooth line/arc/paramPoly3 curves, and object/outline markings. Repeats, skeletons, materials, parking spaces, borders, tunnels, and bridges remain unsupported and are diagnosed. |
| Rail tracks, switches, tram, and stations | Planned | Supported | Static network elements only. |
| `userData`, `include`, data quality, unknown extensions | Planned | Preserve or report | Preserve unknown extension payload where practical; include expansion is tracked separately. |
| XSD and semantic validation | Not implemented | Optional | Not a mandatory runtime dependency; separate roadmap issue. |
| Geometry evaluation, coordinate transforms, routing | Out of scope | Out of scope | Parsing geometry records does not promise derived positions or routing. |
| Dynamic participants and external CRG payload decoding | Out of scope | Out of scope | OpenDRIVE describes static networks; dynamic content belongs to other standards. |

## Version-specific differences to account for

- **1.4.0 and 1.5.0:** ASAM's 1.7.0 specification warns that elements introduced
  in 1.5 are not compatible with 1.4. Its schema marks relevant elements
  optional for backward compatibility; compatibility with these versions is
  based on the specifications, because ASAM notes historical XSD errors.
- **1.6.0 and 1.6.1:** Both encode header revision 1.6. Do not report which patch
  release authored an input file based on that header.
- **1.7.0:** ASAM documents backward compatibility with 1.6.1 and compatibility
  with documented 1.4/1.5 content.
- **1.8.0 and 1.8.1:** Both encode header revision 1.8. ASAM 1.8.1 is backward
  compatible with 1.8.0 and fixes maintenance issues.
- **1.9.0:** Backward-compatible with 1.8.1. Additions are opt-in attributes or
  optional child elements. New content includes permanent/temporary lane
  layers, roadworks and invalidation states, smooth object outlines, changed
  object markings, harmonized signal semantics, local XSD packaging, and
  global OpenCRG offsets.

Version-specific handling must be verified against the relevant specification
revision and schema before implementation. Informative examples and the
Junction guideline can guide fixtures and explanations, but normative
requirements come from normative specification content. The UML model and XSD
are authoritative structural cross-checks when available.

The junction parser checks common-junction attributes against 1.9.0 section
12.2. Cross paths, reference lines, boundaries, elevation grids, and CRG source
metadata are modeled from the verified 1.8.1 structures. Their complete 1.9.0
changes remain unknown. Signal and object models use the 1.9.0 chapters 14 and
13. `validate_junctions()` checks selected 1.8.1 junction type rules, road,
   junction, and controller references, road membership, and lane ID existence
   without changing load behavior. It does not validate lane positions,
   geometric connectivity, or CRG payloads. Applicability of the type rules to
   1.9.0 remains unverified. See [tests/README.md](tests/README.md) for limits.

The published 1.9.0 specification and XSD disagree on two supported records.
Signal `s`, `t`, and `zOffset` are required in the specification attribute table
but optional in the XSD. Smooth outline `curveLocal` attributes `hdg` and
`length` are optional in the specification but required in the XSD. The parser
follows the specification tables and prose. It requires those signal
coordinates and preserves omitted curve headings and lengths as `None`.
Historical applicability of these differences remains unknown.

ASAM's 1.9.0 introduction states a specific license grant for use and
distribution of the standard text. Schema archives, UML models, examples, and
other deliverables are separately listed artifacts; before copying any of
their contents into this repository or redistributing them, check the license
terms attached to that artifact. Prefer linking to ASAM's official downloads
and keep only independently authored compatibility notes and test fixtures in
the package unless redistribution terms are clear.

## Sources

- [ASAM OpenDRIVE 1.9.0 signal records](https://publications.pages.asam.net/standards/ASAM_OpenDRIVE/ASAM_OpenDRIVE_Specification/v1.9.0/specification/14_signals/14_01_introduction.html)
- [ASAM OpenDRIVE 1.9.0 object outlines](https://publications.pages.asam.net/standards/ASAM_OpenDRIVE/ASAM_OpenDRIVE_Specification/v1.9.0/specification/13_objects/13_02_object_outline.html)
- [ASAM OpenDRIVE 1.9.0 object markings](https://publications.pages.asam.net/standards/ASAM_OpenDRIVE/ASAM_OpenDRIVE_Specification/v1.9.0/specification/13_objects/13_08_object_markings.html)
- [ASAM OpenDRIVE 1.9.0 common junctions](https://publications.pages.asam.net/standards/ASAM_OpenDRIVE/ASAM_OpenDRIVE_Specification/v1.9.0/specification/12_junctions/12_02_common_junctions.html)
- [ASAM OpenDRIVE 1.9.0 specification and deliverables](https://publications.pages.asam.net/standards/ASAM_OpenDRIVE/ASAM_OpenDRIVE_Specification/v1.9.0/specification/index.html)
- [ASAM OpenDRIVE 1.9.0 introduction, conventions, and deliverables](https://publications.pages.asam.net/standards/ASAM_OpenDRIVE/ASAM_OpenDRIVE_Specification/v1.9.0/specification/00_preface/00_introduction.html)
- [ASAM OpenDRIVE 1.8.1 specification](https://publications.pages.asam.net/standards/ASAM_OpenDRIVE/ASAM_OpenDRIVE_Specification/v1.8.1/specification/index.html)
- [ASAM OpenDRIVE 1.8.1 backward compatibility](https://publications.pages.asam.net/standards/ASAM_OpenDRIVE/ASAM_OpenDRIVE_Specification/v1.8.1/specification/05_backward_compatibility/05_backward_compatibility.html)
- [ASAM OpenDRIVE previous releases](https://www.asam.net/standards/detail/opendrive/older/)
