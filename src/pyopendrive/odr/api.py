"""Public loading entry point for OpenDRIVE documents."""

from pathlib import Path
from typing import IO

from pyopendrive.odr.models import OpenDriveMap

type OpenDriveSource = str | Path | IO[bytes] | IO[str]


class OpenDrive:
    """Load OpenDRIVE documents into data-only models."""

    @staticmethod
    def load(source: OpenDriveSource) -> OpenDriveMap:
        """Load an OpenDRIVE XML file from a path or open text/binary stream."""
        from pyopendrive.odr.parser.xml import parse

        return parse(source)
