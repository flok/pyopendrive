# OpenDRIVE test data

## Authored fixtures

Run the parser checks without a download:

```console
uv run --locked pytest tests/test_compatibility.py tests/test_opendrive.py tests/test_geometry.py tests/test_profiles.py tests/test_lanes.py
```

`fixtures/revisions/1.4/` through `fixtures/revisions/1.9/` contain independently
authored XML documents. Each `basic.xodr` exercises the same small set of road,
straight geometry, elevation, lane offset, width, road-mark, and speed records.
`test_compatibility.py` checks the reported revision, identifiers, coefficients,
lane values, and absence of diagnostics for those inputs.

These are parser smoke fixtures. They establish that the covered constructs
load under each header revision. They do not establish full compatibility with
that revision, historical XSD validity, semantic validity, or patch-release
support. Historical validity of the independently authored documents remains
unknown until checked against the relevant official specification or schema.
No ASAM examples or schema text are copied into these fixtures.

`fixtures/invalid/` contains malformed XML and inputs with invalid or missing
required parser fields. Tests assert the failed field and the error's element
path. This corpus covers parser errors, not every invalid document an XSD or
semantic validator would reject.

`fixtures/revisions/1.9/lane-extensions.xodr` deliberately combines unsupported
lane content with parsed widths. Tests check each diagnostic and its order,
including unknown group attributes, nested children, a namespaced attribute,
`userData`, explicit road-mark lines, sway offsets, and line color. The fixture
is designed to exercise diagnostics and does not claim schema validity.
Unsupported subtrees produce one diagnostic at their root. The parser discards
their payloads.

`fixtures/network/road-crg.xodr` is an independently authored CRG-reference
fixture. Its record shape follows ASAM OpenDRIVE 1.8.1 section 10.6 and the
1.9.0 global-mode coordinate offsets; no external CRG payload is included.

Lane-rule checks use the required `value` attribute specified in
[ASAM OpenDRIVE 1.8.1 section 11.9][lane-rules]. Road-mark gaps are checked
against [ASAM OpenDRIVE 1.8.1 section 11.8][road-marks]. These citations confirm
the structure for that revision. The tests do not infer when each feature was
first introduced.

## External ASAM examples

Run the complete local test flow with:

```console
uv run --locked python tests/fetch_testdata.py && uv run --locked pytest
```

The first command downloads ASAM's **ASAM OpenDRIVE 1.9.0 Examples and use
cases** deliverable from its [official publication location][source], verifies
the archive against SHA-256
`1142865e58efe4b700b11ba420f8ae1f751446b03f25f5071e7fcc1a8697d4c9`, and
extracts only `.xodr` files into `tests/.testdata/opendrive-1.9.0/`. The archive
and extracted files are ignored by Git. A valid local archive and extracted
corpus are reused, so subsequent runs skip their download and extraction. The
second command runs the pytest suite only after fetching succeeds.

The exact license and redistribution terms for this separate examples archive
have **not** been verified. Downloading it for these tests must not be
interpreted as permission to redistribute it. Do not commit the downloaded
files or publish them as CI artifacts. Consult ASAM's terms before using the
corpus outside this test flow.

Tests use pytest, which is installed by the project's default development
dependency group and configured in `pyproject.toml`. `test_opendrive.py`
provides a small, self-contained example that does not depend on the downloaded
corpus.

The external corpus exercises ASAM's 1.9.0 examples and use cases.
The committed authored fixtures provide the limited revision and invalid-input
coverage described above. Older official examples, schema validation, and
complete coverage of revision differences remain future work.

[source]: https://publications.pages.asam.net/standards/ASAM_OpenDRIVE/ASAM_OpenDRIVE_Specification/v1.9.0/specification/_attachments/generated/ASAM_OpenDRIVE_v1-9-0_examples_and_use-cases.zip

[lane-rules]: https://publications.pages.asam.net/standards/ASAM_OpenDRIVE/ASAM_OpenDRIVE_Specification/v1.8.1/specification/11_lanes/11_09_specific_lane_rules.html
[road-marks]: https://publications.pages.asam.net/standards/ASAM_OpenDRIVE/ASAM_OpenDRIVE_Specification/v1.8.1/specification/11_lanes/11_08_road_markings.html
[road-crg]: https://simulation.pages.asam.net/opendrive-group/opendrive-antora-gen/ASAM_OpenDRIVE_Specification/v1.9.0/specification/10_roads/10_06_road_surface.html
