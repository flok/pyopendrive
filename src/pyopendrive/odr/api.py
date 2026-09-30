"""Public loading entry point for OpenDRIVE documents."""

from pyopendrive.odr.models import OpenDriveMap, OpenDriveSource


class OpenDrive:
    """Load OpenDRIVE documents into data-only models."""

    @staticmethod
    def load(source: OpenDriveSource) -> OpenDriveMap:
        """Load a map; retained as an alias for :meth:`OpenDriveMap.load`."""
        return OpenDriveMap.load(source)
