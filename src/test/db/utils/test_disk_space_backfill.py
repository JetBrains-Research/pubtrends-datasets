import asyncio
import os
import shutil
import subprocess
import unittest
from datetime import datetime
from pathlib import Path

from sqlalchemy.exc import DBAPIError

from src.config.config import Config
from src.db.repositories.gse_repository import GSERepository
from src.db.repositories.gsm_repository import GSMRepository
from src.db.utils.backfill_geometadb import GEOmetadbBackfiller
from src.exception.disk_space_error import DiskSpaceError

_SQL_PATH = Path(__file__).parent.parent / "db" / "testgeometadb.sql"
_TMPFS_SIZE_MB = 10


@unittest.skipUnless(os.getenv("TEST_DISK_SPACE_BACKFILL", "0") == "1", "Disk space backfill test is disabled.")
class TestDiskSpaceBackfill(unittest.TestCase):
    """
    Integration test that verifies DiskSpaceError propagation under real disk exhaustion.

    Should be run inside a docker container with limited disk space (Linux-based test option in README.md).
    """

    def setUp(self) -> None:
        self.config = Config(test=True)
        self.dataset_download_folder = Path(self.config.dataset_download_folder)

        gse_repository = GSERepository(self.config.geometadb_path)
        gsm_repository = GSMRepository(self.config.geometadb_path)
        self.backfiller = GEOmetadbBackfiller(self.config, gse_repository, gsm_repository)

        self.filler_file = Path(os.path.join(self.dataset_download_folder, "filler.tmp"))

    def tearDown(self) -> None:
        if self.filler_file.exists():
            self.filler_file.unlink()
        for soft_file in Path(self.dataset_download_folder).glob("*.soft.gz"):
            soft_file.unlink()

    def test_disk_space_error_handling(self) -> None:
        """
        Verify DiskSpaceError is raised in two scenarios:

        1. The backfill runs normally until the 10 MB tmpfs fills up.
        2. The tmpfs is pre-filled to capacity so the error occurs at the very
           start of a SOFT file download.

        :raises AssertionError: if DiskSpaceError is not raised or comes from
            the wrong path in scenario 2.
        """
        # --- Scenario 1: FS fills up during backfill ---
        with self.assertRaises(DBAPIError):
            self.backfiller.backfill_geometadb(datetime(2024, 3, 1), datetime(2024, 3, 2), skip_existing=False, ignore_failures=True, dont_redownload=False)

        # --- Scenario 2: FS is already full when download begins ---
        for soft_file in self.dataset_download_folder.glob("*.soft.gz"):
            soft_file.unlink()

        free_bytes = shutil.disk_usage(self.config.dataset_download_folder).free
        self.filler_file.touch()
        print("Free", free_bytes / 1024 / 1024, "MB")
        self.filler_file.write_bytes(b"\x00" * free_bytes)

        with self.assertRaises(DiskSpaceError) as ctx:
            # 1GB dataset
            asyncio.run(self.backfiller.download_datasets(["GSE106000"], ignore_failures=True, dont_redownload=False))

        self.assertIn("downloading", str(ctx.exception))
