# External OpenDRIVE test data

Run the complete local test flow with:

```console
uv run python tests/fetch_testdata.py && uv run pytest
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

This is the first Issue 2 corpus tranche. It exercises the valid 1.9.0 examples
and use cases only; it does not yet cover older revisions or intentionally
invalid documents.

[source]: https://publications.pages.asam.net/standards/ASAM_OpenDRIVE/ASAM_OpenDRIVE_Specification/v1.9.0/specification/_attachments/generated/ASAM_OpenDRIVE_v1-9-0_examples_and_use-cases.zip
