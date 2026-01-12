import errno
import os
from pathlib import Path
from typing import Union

import aiofiles
import aiofiles.os

async def async_file_exists(path: Union[Path, str]) -> bool:
    """
    Checks asynchronously if a file or path exists.
    """
    try:
        await aiofiles.os.stat(str(path))
        return True
    except FileNotFoundError:
        return False
    except OSError as e:
        if e.errno == errno.ENOENT:
            return False
        raise
    except ValueError:
        return False


async def async_remove_if_exists(path):
    if await async_file_exists(path):
        await aiofiles.os.remove(path)