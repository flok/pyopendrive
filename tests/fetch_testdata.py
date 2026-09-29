"""Fetch the external ASAM OpenDRIVE corpus used by integration tests."""

from __future__ import annotations

import hashlib
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

ARCHIVE_URL = (
    "https://publications.pages.asam.net/standards/ASAM_OpenDRIVE/"
    "ASAM_OpenDRIVE_Specification/v1.9.0/specification/_attachments/generated/"
    "ASAM_OpenDRIVE_v1-9-0_examples_and_use-cases.zip"
)
ARCHIVE_SHA256 = "1142865e58efe4b700b11ba420f8ae1f751446b03f25f5071e7fcc1a8697d4c9"
DATA_ROOT = Path(__file__).parent / ".testdata"
ARCHIVE_PATH = DATA_ROOT / "ASAM_OpenDRIVE_v1-9-0_examples_and_use-cases.zip"
CORPUS_PATH = DATA_ROOT / "opendrive-1.9.0"
_MARKER_NAME = ".archive-sha256"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download_archive() -> None:
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        ARCHIVE_URL,
        headers={"User-Agent": "pyopendrive-testdata-fetcher/1"},
    )
    with tempfile.NamedTemporaryFile(dir=DATA_ROOT, delete=False) as temporary:
        temporary_path = Path(temporary.name)
        try:
            with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310
                shutil.copyfileobj(response, temporary)
        except BaseException:
            temporary_path.unlink(missing_ok=True)
            raise

    if _sha256(temporary_path) != ARCHIVE_SHA256:
        temporary_path.unlink()
        raise RuntimeError("Downloaded ASAM archive failed SHA-256 verification")
    temporary_path.replace(ARCHIVE_PATH)


def _archive_is_valid() -> bool:
    return ARCHIVE_PATH.is_file() and _sha256(ARCHIVE_PATH) == ARCHIVE_SHA256


def _safe_xodr_path(name: str) -> Path | None:
    member = PurePosixPath(name)
    if member.is_absolute() or ".." in member.parts:
        raise RuntimeError(f"Unsafe path in ASAM archive: {name!r}")
    if member.suffix.lower() != ".xodr":
        return None
    return Path(*member.parts)


def _extract_corpus() -> None:
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    temporary_path = Path(tempfile.mkdtemp(prefix="opendrive-1.9.0-", dir=DATA_ROOT))
    try:
        extracted = 0
        with zipfile.ZipFile(ARCHIVE_PATH) as archive:
            for info in archive.infolist():
                relative_path = _safe_xodr_path(info.filename)
                if relative_path is None:
                    continue
                destination = temporary_path / relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, destination.open("wb") as target:
                    shutil.copyfileobj(source, target)
                extracted += 1
        if not extracted:
            raise RuntimeError("ASAM archive contains no OpenDRIVE files")
        (temporary_path / _MARKER_NAME).write_text(ARCHIVE_SHA256 + "\n")
        shutil.rmtree(CORPUS_PATH, ignore_errors=True)
        temporary_path.replace(CORPUS_PATH)
    except BaseException:
        shutil.rmtree(temporary_path, ignore_errors=True)
        raise


def fetch_testdata() -> Path:
    """Return a verified, XODR-only local copy of the ASAM 1.9.0 corpus."""
    if not _archive_is_valid():
        ARCHIVE_PATH.unlink(missing_ok=True)
        _download_archive()

    marker = CORPUS_PATH / _MARKER_NAME
    corpus_is_current = (
        marker.is_file()
        and marker.read_text().strip() == ARCHIVE_SHA256
        and any(CORPUS_PATH.rglob("*.xodr"))
    )
    if not corpus_is_current:
        _extract_corpus()
    return CORPUS_PATH


if __name__ == "__main__":
    print(fetch_testdata())
