class DiskSpaceError(OSError):
    """Raised when a write fails because the disk has no space left (errno.ENOSPC)."""
