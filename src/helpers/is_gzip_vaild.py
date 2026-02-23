import aiogzip
import gzip
import zlib


async def is_gzip_valid(path):
    """
    Checks if a gzip file is valid.
    :param path: Path to the gzip file.
    :return: True if the file is valid, False otherwise.
    """
    try:
        async with aiogzip.AsyncGzipFile(path, "rb") as f:
            try:
                await f.read(1)
                return True
            except (gzip.BadGzipFile, EOFError, zlib.error):
                # Header is corrupt, file is truncated, or zlib data is invalid
                return False
    except (FileNotFoundError, PermissionError, OSError):
        # File cannot be opened or accessed
        return False
