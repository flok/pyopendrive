# Repository instructions

## Project rules

- Keep the public Python API exported from `pyopendrive`; the primary entry
  point is `OpenDriveMap.load(source)`.
- Keep OpenDRIVE data models separate from XML parsing. Models describe parsed
  data; parser modules convert input documents into those models.
- Treat `docs/compatibility.md` as the source of truth for supported standard
  revisions, feature coverage, and compatibility limits.
- Target Python 3.12 or newer. Use `uv` for project and build commands and Ruff
  for linting and formatting; read `pyproject.toml` for configured commands.
- Keep ASAM-derived requirements traceable to the relevant specification
  revision. Mark unverified version details as unknown until checked against
  the official specification, XSD, or UML model.

## Documentation synchronization

For every general codebase change, review both this file and
`ARCHITECTURE.md` in the same change. Update `ARCHITECTURE.md` when package
layout, data flow, public contracts, or design boundaries change. Update this
file when repository conventions or development workflows change. Do not add
timestamp-only edits when a document's guidance remains accurate.

## Before finishing a change

- Run the relevant configured Ruff checks for changed Python code.
- Run or update the behavior checks that cover changed functionality when the
  repository provides them.
- Check that any documented examples and public imports match the current API.
