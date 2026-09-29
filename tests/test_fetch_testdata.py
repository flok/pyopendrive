"""Tests for the local ASAM corpus cache."""

import hashlib
import zipfile
from pathlib import Path

import fetch_testdata
import pytest


def test_valid_cached_corpus_skips_download_and_extraction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive = tmp_path / "examples.zip"
    with zipfile.ZipFile(archive, "w") as package:
        package.writestr("examples/example.xodr", "<OpenDRIVE/>")

    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    corpus = tmp_path / "corpus"
    monkeypatch.setattr(fetch_testdata, "DATA_ROOT", tmp_path)
    monkeypatch.setattr(fetch_testdata, "ARCHIVE_PATH", archive)
    monkeypatch.setattr(fetch_testdata, "CORPUS_PATH", corpus)
    monkeypatch.setattr(fetch_testdata, "ARCHIVE_SHA256", digest)

    assert fetch_testdata.fetch_testdata() == corpus

    def unexpected_call() -> None:
        pytest.fail("valid cached test data should be reused")

    monkeypatch.setattr(fetch_testdata, "_download_archive", unexpected_call)
    monkeypatch.setattr(fetch_testdata, "_extract_corpus", unexpected_call)

    assert fetch_testdata.fetch_testdata() == corpus
